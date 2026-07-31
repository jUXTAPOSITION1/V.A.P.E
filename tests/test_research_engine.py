"""Tests for agents/research_engine.py — the layered research pipeline
(classify -> broad_discovery -> deep_extract -> synthesize -> render).
Hermetic: agents.llm.ask_oci_grok_safe, agents.intel_common.web_search_snippets,
and agents.web_sourcer.WebSourcer are all mocked/faked; no real network call,
no real LLM call, no real Memory writes.
"""
import json
from unittest import mock

from agents import research_engine as re_engine


# ── classify_task ────────────────────────────────────────────────────────
def test_classify_task_normalizes_known_types():
    assert re_engine.classify_task("Threat-Analysis") == "threat_analysis"
    assert re_engine.classify_task("news report") == "news_report"
    assert re_engine.classify_task("INVESTIGATION") == "investigation"


def test_classify_task_falls_back_to_general_for_unknown():
    assert re_engine.classify_task("something-weird") == "general"
    assert re_engine.classify_task(None) == "general"
    assert re_engine.classify_task("") == "general"


# ── _default_queries (deterministic fallback) ───────────────────────────
def test_default_queries_never_empty_and_task_aware():
    result = re_engine._default_queries("Bitmor", "threat_analysis")
    assert result["queries"]
    assert len(result["queries"]) <= re_engine.MAX_QUERIES_DEFAULT
    assert all("Bitmor" in q["q"] for q in result["queries"])
    assert result["follow_up_strategy"]


def test_default_queries_includes_known_date():
    result = re_engine._default_queries("Bitmor", "threat_analysis", known_facts={"date": "2026-05-25"})
    assert any("2026-05-25" in q["q"] for q in result["queries"])


def test_default_queries_respects_max_queries():
    result = re_engine._default_queries("Bitmor", "threat_analysis", max_queries=2)
    assert len(result["queries"]) == 2


# ── generate_queries ─────────────────────────────────────────────────────
class TestGenerateQueries:
    def test_falls_back_when_llm_module_not_importable(self):
        with mock.patch.dict("sys.modules", {"agents.llm": None}):
            result = re_engine.generate_queries("Foo", "general")
        assert result["queries"]

    def test_falls_back_when_llm_unavailable(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("[llm unavailable: no keys]", None)):
            result = re_engine.generate_queries("Foo", "general")
        assert result["queries"]
        assert "fallback" in result["queries"][0]["rationale"]

    def test_falls_back_on_malformed_json(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("not json at all", "oci_grok")):
            result = re_engine.generate_queries("Foo", "general")
        assert result["queries"]

    def test_falls_back_on_llm_exception(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=RuntimeError("boom")):
            result = re_engine.generate_queries("Foo", "general")
        assert result["queries"]

    def test_parses_valid_json_and_sorts_by_priority(self):
        payload = json.dumps({
            "queries": [
                {"q": "foo low prio", "rationale": "r1", "priority": 2},
                {"q": "foo high prio", "rationale": "r2", "priority": 9},
            ],
            "follow_up_strategy": "widen search",
        })
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(payload, "oci_grok")):
            result = re_engine.generate_queries("Foo", "general")
        assert [q["q"] for q in result["queries"]] == ["foo high prio", "foo low prio"]
        assert result["follow_up_strategy"] == "widen search"

    def test_clamps_priority_and_drops_empty_queries(self):
        payload = json.dumps({"queries": [
            {"q": "", "priority": 5},
            {"q": "real one", "priority": 99},
            {"q": "also real", "priority": -5},
        ]})
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(payload, "oci_grok")):
            result = re_engine.generate_queries("Foo", "general")
        priorities = {q["q"]: q["priority"] for q in result["queries"]}
        assert "" not in priorities
        assert priorities["real one"] == 10
        assert priorities["also real"] == 1

    def test_falls_back_when_queries_key_missing_or_empty(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(json.dumps({"queries": []}), "oci_grok")):
            result = re_engine.generate_queries("Foo", "general")
        assert result["queries"]  # deterministic fallback kicked in
        assert "fallback" in result["queries"][0]["rationale"]

    def test_respects_max_queries(self):
        payload = json.dumps({"queries": [{"q": f"q{i}", "priority": 5} for i in range(20)]})
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(payload, "oci_grok")):
            result = re_engine.generate_queries("Foo", "general", max_queries=3)
        assert len(result["queries"]) == 3

    def test_respects_max_queries_on_fallback_path(self):
        # Real bug CodeRabbit flagged on PR #372: the fallback path used to
        # always return up to MAX_QUERIES_DEFAULT regardless of what the
        # caller asked for, so a caller requesting max_queries=2 could get
        # 8 back whenever the LLM was unavailable/unparseable.
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("not json", "oci_grok")):
            result = re_engine.generate_queries("Foo", "threat_analysis", max_queries=2)
        assert len(result["queries"]) == 2


# ── credibility tiering ──────────────────────────────────────────────────
def test_domain_extraction_strips_www():
    assert re_engine._domain("https://www.coindesk.com/foo") == "coindesk.com"
    assert re_engine._domain("not a url") == ""
    assert re_engine._domain(None) == ""


def test_credibility_tier_classification():
    assert re_engine._credibility_tier("https://rekt.news/foo") == "security_research"
    assert re_engine._credibility_tier("https://www.coindesk.com/foo") == "news"
    assert re_engine._credibility_tier("https://github.com/foo/bar") == "primary_platform"
    assert re_engine._credibility_tier("https://x.com/foo") == "social_unverified"
    assert re_engine._credibility_tier("https://randomblog.example.com") == "unclassified"


# ── broad_discovery ──────────────────────────────────────────────────────
class TestBroadDiscovery:
    def _fake_query_call(self, topic, task_type, known_facts, max_queries):
        return {"queries": [{"q": "query one", "rationale": "r1", "priority": 5},
                             {"q": "query two", "rationale": "r2", "priority": 5}],
                "follow_up_strategy": "widen if thin"}

    def test_dedupes_urls_across_queries_and_ranks_by_credibility(self):
        def fake_search(query, max_results=5):
            return {"provider": "tavily", "results": [
                {"url": "https://x.com/social", "title": "social", "snippet": "s"},
                {"url": "https://rekt.news/report", "title": "sec", "snippet": "s"},
                {"url": "https://x.com/social", "title": "dup", "snippet": "s"},  # duplicate across queries
            ]}
        with mock.patch("agents.intel_common.web_search_snippets", side_effect=fake_search):
            result = re_engine.broad_discovery("Foo", "threat_analysis", query_call=self._fake_query_call)
        urls = [f["url"] for f in result["findings"]]
        assert urls.count("https://x.com/social") == 1  # deduped
        assert result["prioritized_urls"][0] == "https://rekt.news/report"  # higher credibility ranked first
        assert result["log"]["queries"][0]["q"] == "query one"
        assert result["log"]["follow_up_strategy"] == "widen if thin"
        assert result["task_type"] == "threat_analysis"

    def test_no_hits_returns_empty_findings_not_error(self):
        with mock.patch("agents.intel_common.web_search_snippets",
                         return_value={"provider": None, "results": []}):
            result = re_engine.broad_discovery("Foo", "general", query_call=self._fake_query_call)
        assert result["findings"] == []
        assert result["prioritized_urls"] == []

    def test_search_provider_failure_does_not_abort_the_round(self):
        # broad_discovery's own docstring promises it never raises — one
        # query's search call raising shouldn't stop the remaining queries
        # from running, even though web_search_snippets is documented not
        # to raise on its own (defense in depth, not reachable today).
        calls = {"n": 0}

        def flaky_search(query, max_results=5):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("provider down")
            return {"provider": "tavily", "results": [{"url": "https://rekt.news/r", "title": "t", "snippet": "s"}]}

        with mock.patch("agents.intel_common.web_search_snippets", side_effect=flaky_search):
            result = re_engine.broad_discovery("Foo", "general", query_call=self._fake_query_call)
        assert result["prioritized_urls"] == ["https://rekt.news/r"]
        assert calls["n"] == 2


# ── deep_extract ─────────────────────────────────────────────────────────
class TestDeepExtract:
    def test_returns_none_when_sourcer_finds_nothing(self):
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = None
        assert re_engine.deep_extract("https://example.com", sourcer=fake_sourcer) is None

    def test_returns_none_on_fetch_error(self):
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = {"url": "https://example.com", "error": "timeout"}
        assert re_engine.deep_extract("https://example.com", sourcer=fake_sourcer) is None

    def test_returns_normalized_extract_on_success(self):
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = {
            "url": "https://rekt.news/report", "domain": "rekt.news",
            "provider": "firecrawl", "content": "real page content", "entities": ["Foo"],
        }
        extract = re_engine.deep_extract("https://rekt.news/report", sourcer=fake_sourcer)
        assert extract["credibility"] == "security_research"
        assert extract["content"] == "real page content"
        assert extract["entities"] == ["Foo"]

    def test_creates_its_own_sourcer_when_none_given(self):
        with mock.patch("agents.web_sourcer.WebSourcer") as MockSourcer:
            instance = MockSourcer.return_value
            instance.fetch_page.return_value = None
            re_engine.deep_extract("https://example.com")
        MockSourcer.assert_called_once()


# ── layered_research (orchestration) ────────────────────────────────────
class TestLayeredResearch:
    def test_orchestrates_discovery_and_deep_extraction(self):
        discovery = {
            "topic": "Foo", "task_type": "threat_analysis",
            "findings": [{"url": "https://rekt.news/a", "credibility": "security_research",
                          "title": "a", "snippet": "s"}],
            "prioritized_urls": ["https://rekt.news/a"],
            "log": {"queries": [], "follow_up_strategy": "", "unique_sources_found": 1},
        }
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = {
            "url": "https://rekt.news/a", "domain": "rekt.news",
            "provider": "firecrawl", "content": "content here", "entities": [],
        }
        with mock.patch("agents.research_engine.broad_discovery", return_value=discovery):
            result = re_engine.layered_research("Foo", task_type="threat_analysis", sourcer=fake_sourcer)
        assert result["task_type"] == "threat_analysis"
        assert len(result["deep_extracts"]) == 1
        assert result["log"]["deep_extracted_count"] == 1
        fake_sourcer.save_seen.assert_called_once()

    def test_never_raises_when_no_urls_found(self):
        discovery = {"topic": "Foo", "task_type": "general", "findings": [], "prioritized_urls": [],
                      "log": {"queries": [], "follow_up_strategy": "", "unique_sources_found": 0}}
        fake_sourcer = mock.Mock()
        with mock.patch("agents.research_engine.broad_discovery", return_value=discovery):
            result = re_engine.layered_research("Foo", sourcer=fake_sourcer)
        assert result["deep_extracts"] == []
        fake_sourcer.save_seen.assert_called_once()

    def test_respects_max_deep_urls_cap(self):
        discovery = {
            "topic": "Foo", "task_type": "general",
            "findings": [], "prioritized_urls": [f"https://example.com/{i}" for i in range(10)],
            "log": {"queries": [], "follow_up_strategy": "", "unique_sources_found": 10},
        }
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = {"url": "x", "domain": "example.com",
                                                 "provider": None, "content": "c", "entities": []}
        with mock.patch("agents.research_engine.broad_discovery", return_value=discovery):
            re_engine.layered_research("Foo", max_deep_urls=2, sourcer=fake_sourcer)
        assert fake_sourcer.fetch_page.call_count == 2


# ── _evidence_block ──────────────────────────────────────────────────────
def test_evidence_block_includes_facts_findings_and_deep_extracts():
    result = {
        "topic": "Foo", "task_type": "threat_analysis",
        "known_facts": {"loss_usd_m": 5, "date": "2026-01-01"},
        "findings": [{"url": "https://rekt.news/a", "credibility": "security_research",
                      "title": "A report", "snippet": "some snippet"}],
        "deep_extracts": [{"url": "https://rekt.news/a", "credibility": "security_research",
                            "content": "full page text"}],
    }
    block = re_engine._evidence_block(result)
    assert "Foo" in block
    assert "loss_usd_m=5" in block
    assert "A report" in block
    assert "full page text" in block


# ── synthesize ────────────────────────────────────────────────────────────
class TestSynthesize:
    def _base_result(self):
        return {"topic": "Foo", "task_type": "threat_analysis", "known_facts": {}, "findings": [],
                "deep_extracts": [], "log": {}}

    def test_unavailable_when_llm_module_not_importable(self):
        with mock.patch.dict("sys.modules", {"agents.llm": None}):
            result = re_engine.synthesize(self._base_result())
        assert "unavailable" in result["narrative"]
        assert result["gaps"] == []
        assert result["provider"] is None

    def test_unavailable_when_llm_call_raises(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=RuntimeError("boom")):
            result = re_engine.synthesize(self._base_result())
        assert "unavailable" in result["narrative"]

    def test_unavailable_when_no_provider_reachable(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("[llm unavailable: no keys]", None)):
            result = re_engine.synthesize(self._base_result())
        assert "unavailable" in result["narrative"]
        assert result["provider"] is None

    def test_parses_gaps_json_trailer_and_strips_it_from_narrative(self):
        text = ('Real narrative text here.\n'
                'GAPS_JSON: [{"description": "attacker unidentified", "confidence": 0.3, '
                '"next_action": "monitor chain"}]')
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result())
        assert result["narrative"] == "Real narrative text here."
        assert result["gaps"] == [{"description": "attacker unidentified", "confidence": 0.3,
                                    "next_action": "monitor chain"}]
        assert result["provider"] == "oci_grok"

    def test_malformed_gaps_json_leaves_narrative_untouched_and_gaps_empty(self):
        text = "Real narrative text.\nGAPS_JSON: [not valid json"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result())
        assert result["gaps"] == []
        assert "Real narrative text." in result["narrative"]

    def test_malformed_gaps_json_is_logged_not_silently_dropped(self, capsys):
        # Bracket-closed (so the regex matches and json.loads is actually
        # attempted) but not valid JSON — exercises the real parse-failure
        # branch, unlike an unterminated trailer that never matches at all.
        text = "Real narrative text.\nGAPS_JSON: [{not: valid, json}]"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            re_engine.synthesize(self._base_result())
        assert "GAPS_JSON parse failed" in capsys.readouterr().out

    def test_no_gaps_trailer_returns_empty_gaps_list(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("Just narrative, no trailer.", "groq")):
            result = re_engine.synthesize(self._base_result())
        assert result["gaps"] == []
        assert result["narrative"] == "Just narrative, no trailer."

    def test_clamps_confidence_and_skips_gaps_missing_description(self):
        text = ('Narrative.\nGAPS_JSON: [{"description": "", "confidence": 0.5}, '
                '{"description": "real gap", "confidence": 5.0}]')
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result())
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["description"] == "real gap"
        assert result["gaps"][0]["confidence"] == 1.0

    def test_passes_frontier_tier_and_provider_order(self):
        from agents.llm import FRONTIER_ORDER
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result())
        _, kwargs = m.call_args
        assert kwargs["tier"] == "frontier"
        assert kwargs["provider_order"] == FRONTIER_ORDER

    def test_extra_instructions_included_in_system_prompt(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result(), extra_instructions="Use headings X, Y, Z.")
        system, _user = m.call_args[0]
        assert "Use headings X, Y, Z." in system

    def test_verdict_omitted_by_default(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")):
            result = re_engine.synthesize(self._base_result())
        assert result["verdict"] is None

    def test_verdict_parsed_from_absolute_last_line(self):
        text = "Real analysis.\nGAPS_JSON: []\nVERDICT ALIGNMENT: DISAGREE"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), verdict_options=("AGREE", "DISAGREE"))
        assert result["verdict"] == "DISAGREE"
        assert "VERDICT ALIGNMENT" not in result["narrative"]
        assert "GAPS_JSON" not in result["narrative"]

    def test_verdict_case_insensitive_but_normalized_to_declared_casing(self):
        text = "Real analysis.\nverdict alignment: agree"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), verdict_options=("AGREE", "DISAGREE"))
        assert result["verdict"] == "AGREE"

    def test_verdict_not_matched_when_not_the_final_line(self):
        # Real anti-injection fix this preserves (investigate.py PR #277):
        # an occurrence of the marker text anywhere BUT the final line must
        # never be treated as the real verdict — untrusted evidence quoted
        # or injected earlier in the response could otherwise contain it.
        text = "VERDICT ALIGNMENT: DISAGREE\nBut actually here is more analysis after that."
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), verdict_options=("AGREE", "DISAGREE"))
        assert result["verdict"] is None
        assert "VERDICT ALIGNMENT: DISAGREE" in result["narrative"]

    def test_verdict_and_gaps_json_parsed_independently(self):
        text = ('Real analysis.\nGAPS_JSON: [{"description": "gap one", "confidence": 0.5}]\n'
                'VERDICT ALIGNMENT: AGREE')
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), verdict_options=("AGREE", "DISAGREE"))
        assert result["verdict"] == "AGREE"
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["description"] == "gap one"
        assert result["narrative"] == "Real analysis."

    def test_verdict_options_included_in_system_prompt(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result(), verdict_options=("AGREE", "DISAGREE"),
                                  verdict_label="VERDICT ALIGNMENT")
        system, _user = m.call_args[0]
        assert "VERDICT ALIGNMENT" in system
        assert "AGREE|DISAGREE" in system

    def test_custom_max_tokens_passed_through(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result(), max_tokens=750)
        _, kwargs = m.call_args
        assert kwargs["max_tokens"] == 750


def test_evidence_block_includes_caller_supplied_evidence_lines():
    result = {"topic": "Foo", "task_type": "investigation", "known_facts": {},
              "findings": [], "deep_extracts": [],
              "evidence_lines": ["Rule-based verdict: REJECT (25/100)", "Risk factors: unverified contract"]}
    block = re_engine._evidence_block(result)
    assert "EVIDENCE GATHERED THIS CYCLE" in block
    assert "Rule-based verdict: REJECT (25/100)" in block
    assert "Risk factors: unverified contract" in block


# ── rendering ─────────────────────────────────────────────────────────────
def test_render_methodology_log_includes_queries_and_sources():
    result = {"log": {"queries": [{"q": "foo bar", "rationale": "r", "hit_count": 3, "provider": "tavily"}],
                       "follow_up_strategy": "widen next time",
                       "deep_extracted_urls": ["https://rekt.news/a"],
                       "unique_sources_found": 5}}
    rendered = re_engine.render_methodology_log(result)
    assert "## Research Methodology and Sources" in rendered
    assert "foo bar" in rendered
    assert "widen next time" in rendered
    assert "rekt.news/a" in rendered
    assert "security_research" in rendered
    assert "5" in rendered


def test_render_methodology_log_handles_empty_log():
    rendered = re_engine.render_methodology_log({})
    assert "## Research Methodology and Sources" in rendered
    assert "0" in rendered


def test_render_methodology_log_escapes_backticks_in_query_and_rationale():
    # An LLM-authored rationale/query string containing a backtick used to
    # be spliced straight into a `...` Markdown code span, breaking it.
    result = {"log": {"queries": [{"q": "foo `bar` baz", "rationale": "uses `eval()` internally",
                                    "hit_count": 1, "provider": "tavily"}]}}
    rendered = re_engine.render_methodology_log(result)
    assert "`bar`" not in rendered
    assert "`eval()`" not in rendered
    assert "foo 'bar' baz" in rendered
    assert "uses 'eval()' internally" in rendered


def test_render_methodology_log_uses_autolink_for_urls_not_bracket_link():
    # A ')' in a real search-result URL would close a [text](url)-style
    # Markdown link early — angle-bracket autolinks avoid that entirely.
    result = {"log": {"deep_extracted_urls": ["https://en.wikipedia.org/wiki/Foo_(bar)"]}}
    rendered = re_engine.render_methodology_log(result)
    assert "<https://en.wikipedia.org/wiki/Foo_(bar)>" in rendered
    assert "](https://en.wikipedia.org/wiki/Foo_(bar))" not in rendered


def test_render_gaps_section_with_gaps():
    gaps = [{"description": "unclear attacker identity", "confidence": 0.42, "next_action": "trace wallet"}]
    rendered = re_engine.render_gaps_section(gaps)
    assert "## Gaps & Confidence" in rendered
    assert "unclear attacker identity" in rendered
    assert "42%" in rendered
    assert "trace wallet" in rendered


def test_render_gaps_section_empty_states_explicitly():
    rendered = re_engine.render_gaps_section([])
    assert "## Gaps & Confidence" in rendered
    assert "No material gaps flagged" in rendered


# ── review_output ─────────────────────────────────────────────────────────
class TestReviewOutput:
    def test_ok_when_all_required_sections_and_gaps_present(self):
        text = ("## Known Facts\n...\n## Timeline\n...\n## Root Cause\n...\n## Impact\n...\n"
                "## Response & Mitigation\n...\n## Gaps & Confidence\n...\n"
                "## Research Methodology and Sources\n...")
        review = re_engine.review_output(text, task_type="threat_analysis")
        assert review == {"ok": True, "issues": []}

    def test_flags_missing_sections(self):
        text = "## Known Facts\nsome text with gaps and confidence mentioned"
        review = re_engine.review_output(text, task_type="threat_analysis")
        assert not review["ok"]
        assert any("Timeline" in issue for issue in review["issues"])
        assert any("Root Cause" in issue for issue in review["issues"])

    def test_flags_missing_gaps_confidence_mention(self):
        text = ("## Known Facts\n...\n## Timeline\n...\n## Root Cause\n...\n## Impact\n...\n"
                "## Response & Mitigation\n...\n## Gaps & Confidence\n...\n"
                "## Research Methodology and Sources\n...").replace("Gaps & Confidence", "Nothing Here")
        review = re_engine.review_output(text, task_type="threat_analysis")
        assert not review["ok"]
        assert any("gaps/confidence" in issue for issue in review["issues"])

    def test_general_task_type_has_lighter_requirements(self):
        text = ("## Findings\nsome findings.\n## Gaps & Confidence\n...\n"
                "## Research Methodology and Sources\n...")
        review = re_engine.review_output(text, task_type="general")
        assert review == {"ok": True, "issues": []}

    def test_section_mention_in_prose_without_a_heading_still_flagged_missing(self):
        # Real gap CodeRabbit flagged: matching anywhere in the body (not
        # just headings) let prose that merely mentions "the impact was..."
        # satisfy the check even with no real "## Impact" section.
        text = ("## Known Facts\nThe impact was severe and the timeline moved fast, "
                "with a clear root cause and a fast response and mitigation.\n"
                "## Gaps & Confidence\n...\n## Research Methodology and Sources\n...")
        review = re_engine.review_output(text, task_type="threat_analysis")
        assert not review["ok"]
        assert any("Timeline" in issue for issue in review["issues"])
        assert any("Impact" in issue for issue in review["issues"])
        assert any("Root Cause" in issue for issue in review["issues"])

    def test_never_raises_on_none_input(self):
        review = re_engine.review_output(None, task_type="general")
        assert review["ok"] is False


# ── log_review_finding ─────────────────────────────────────────────────────
class TestLogReviewFinding:
    def test_noop_when_no_issues(self):
        with mock.patch("skillforge.memory.retriever.append_to_memory") as m:
            re_engine.log_review_finding("Foo", "threat_analysis", [])
        m.assert_not_called()

    def test_logs_to_memory_with_lesson_category_and_tags(self):
        with mock.patch("skillforge.memory.retriever.append_to_memory") as m:
            re_engine.log_review_finding("Foo", "threat_analysis", ["missing expected section: Timeline"])
        m.assert_called_once()
        _, kwargs = m.call_args
        assert kwargs["category"] == "lesson"
        assert "research-engine" in kwargs["tags"]
        assert kwargs["metadata"]["topic"] == "Foo"

    def test_never_raises_when_memory_module_unavailable(self):
        with mock.patch.dict("sys.modules", {"skillforge.memory.retriever": None}):
            re_engine.log_review_finding("Foo", "general", ["some issue"])  # must not raise

    def test_never_raises_when_append_to_memory_errors(self):
        with mock.patch("skillforge.memory.retriever.append_to_memory", side_effect=RuntimeError("boom")):
            re_engine.log_review_finding("Foo", "general", ["some issue"])  # must not raise
