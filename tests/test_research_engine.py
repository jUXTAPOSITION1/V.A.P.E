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

    def test_refinement_hint_is_included_in_the_prompt(self):
        # Multi-round iteration (layered_research) feeds a thin first
        # round's own follow_up_strategy back in here as refinement_hint —
        # the LLM must actually see it, not just accept it silently.
        captured = {}

        def fake_ask(system, user, **kwargs):
            captured["user"] = user
            return (json.dumps({"queries": [{"q": "q1", "priority": 5}]}), "oci_grok")

        with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=fake_ask):
            re_engine.generate_queries("Foo", "general", refinement_hint="try official announcements next")
        assert "try official announcements next" in captured["user"]

    def test_no_refinement_hint_omits_the_extra_prompt_section(self):
        captured = {}

        def fake_ask(system, user, **kwargs):
            captured["user"] = user
            return (json.dumps({"queries": [{"q": "q1", "priority": 5}]}), "oci_grok")

        with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=fake_ask):
            re_engine.generate_queries("Foo", "general")
        assert "prior research round" not in captured["user"]


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


def test_credibility_tier_recognizes_expanded_domain_sets():
    # Real, verifiable additions to each tier -- not exhaustive, just
    # pinning that the expansion actually landed in the right buckets.
    assert re_engine._credibility_tier("https://halborn.com/foo") == "security_research"
    assert re_engine._credibility_tier("https://blockworks.co/foo") == "news"
    assert re_engine._credibility_tier("https://basescan.org/address/0x1") == "primary_platform"
    assert re_engine._credibility_tier("https://defillama.com/protocol/foo") == "primary_platform"


def test_credibility_tier_promotes_unclassified_domain_with_topic_and_incident_language():
    # Real gap this closes: a project's own custom domain can never be
    # fully enumerated in a fixed list -- when the page's own title/snippet
    # names the researched topic AND uses incident-disclosure language, it
    # should be promoted out of "unclassified" rather than stuck there.
    tier = re_engine._credibility_tier(
        "https://setprotocol.example/blog/incident",
        topic="Set Protocol",
        text="Set Protocol Official Incident Report: what happened",
    )
    assert tier == "primary_platform"


def test_credibility_tier_does_not_promote_without_both_signals():
    # Topic present but no incident-disclosure keyword -> still unclassified.
    assert re_engine._credibility_tier(
        "https://setprotocol.example/blog/update",
        topic="Set Protocol", text="Set Protocol ships a new feature",
    ) == "unclassified"
    # Incident-disclosure keyword present but topic never mentioned -> still
    # unclassified, since it could be an unrelated protocol's post-mortem.
    assert re_engine._credibility_tier(
        "https://randomblog.example.com",
        topic="Set Protocol", text="Official post-mortem of a totally different incident",
    ) == "unclassified"


def test_credibility_tier_secondary_signal_is_optional():
    # No topic/text given at all -> behaves exactly as before this change.
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

    def test_promotes_unclassified_hit_using_topic_plus_title_and_snippet(self):
        def fake_search(query, max_results=5):
            return {"provider": "tavily", "results": [
                {"url": "https://setprotocol.example/post", "title": "Set Protocol Official Incident Report",
                 "snippet": "what happened and next steps"},
            ]}
        with mock.patch("agents.intel_common.web_search_snippets", side_effect=fake_search):
            result = re_engine.broad_discovery("Set Protocol", "threat_analysis", query_call=self._fake_query_call)
        assert result["findings"][0]["credibility"] == "primary_platform"

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

    def test_excludes_urls_already_in_an_externally_supplied_seen_urls_set(self):
        # layered_research() shares one seen_urls set across rounds so a
        # second round's findings are genuinely new, not a repeat.
        with mock.patch("agents.intel_common.web_search_snippets",
                         return_value={"provider": "tavily", "results": [
                             {"url": "https://rekt.news/a", "title": "t", "snippet": "s"}]}):
            result = re_engine.broad_discovery("Foo", "general", query_call=self._fake_query_call,
                                                seen_urls={"https://rekt.news/a"})
        assert result["findings"] == []
        assert result["prioritized_urls"] == []

    def test_mutates_the_given_seen_urls_set_with_newly_found_urls(self):
        seen = set()
        with mock.patch("agents.intel_common.web_search_snippets",
                         return_value={"provider": "tavily", "results": [
                             {"url": "https://rekt.news/a", "title": "t", "snippet": "s"}]}):
            re_engine.broad_discovery("Foo", "general", query_call=self._fake_query_call, seen_urls=seen)
        assert "https://rekt.news/a" in seen

    def test_passes_refinement_hint_to_a_query_call_that_accepts_it(self):
        captured = {}

        def query_call(topic, task_type, known_facts, max_queries, refinement_hint=None):
            captured["hint"] = refinement_hint
            return {"queries": [{"q": "q1", "priority": 5}], "follow_up_strategy": ""}

        with mock.patch("agents.intel_common.web_search_snippets", return_value={"provider": None, "results": []}):
            re_engine.broad_discovery("Foo", "general", query_call=query_call, refinement_hint="widen scope")
        assert captured["hint"] == "widen scope"

    def test_omits_refinement_hint_for_a_fixed_arity_query_call(self):
        # A caller-supplied query_call from before refinement_hint existed
        # (like this class's own _fake_query_call) must not blow up with a
        # TypeError just because layered_research() now offers a hint.
        with mock.patch("agents.intel_common.web_search_snippets", return_value={"provider": None, "results": []}):
            result = re_engine.broad_discovery("Foo", "general", query_call=self._fake_query_call,
                                                refinement_hint="widen scope")
        assert result["findings"] == []  # no exception raised


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

    def test_promotes_unclassified_domain_using_topic_and_page_content(self):
        # Real gap this closes: a project's own custom domain (not in any
        # fixed tier list) with a page that actually names the topic and
        # uses incident-disclosure language should be promoted out of
        # "unclassified" -- deep_extract has no separate title/snippet the
        # way a search hit does, so it reads the page's own leading content.
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = {
            "url": "https://setprotocol.example/post", "domain": "setprotocol.example",
            "provider": "firecrawl", "content": "Set Protocol Official Incident Report...", "entities": [],
        }
        extract = re_engine.deep_extract("https://setprotocol.example/post", sourcer=fake_sourcer,
                                          topic="Set Protocol")
        assert extract["credibility"] == "primary_platform"

    def test_no_topic_given_leaves_unclassified_domain_unclassified(self):
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.return_value = {
            "url": "https://setprotocol.example/post", "domain": "setprotocol.example",
            "provider": "firecrawl", "content": "Set Protocol Official Incident Report...", "entities": [],
        }
        extract = re_engine.deep_extract("https://setprotocol.example/post", sourcer=fake_sourcer)
        assert extract["credibility"] == "unclassified"


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


# ── layered_research multi-round iteration ──────────────────────────────
class TestLayeredResearchMultiRound:
    def _discovery(self, url, follow_up_strategy=""):
        return {
            "topic": "Foo", "task_type": "general",
            "findings": [{"url": url, "credibility": "unclassified", "title": "t", "snippet": "s"}],
            "prioritized_urls": [url],
            "log": {"queries": [{"q": "q1", "rationale": "", "provider": "tavily", "hit_count": 1}],
                    "follow_up_strategy": follow_up_strategy, "unique_sources_found": 1},
        }

    def test_thin_first_round_triggers_a_second_round_with_the_refinement_hint(self):
        round1 = self._discovery("https://a.com/1", follow_up_strategy="try official announcements")
        round2 = self._discovery("https://b.com/2")
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.side_effect = lambda url: {
            "url": url, "domain": "x", "provider": "firecrawl", "content": "c", "entities": []}
        with mock.patch("agents.research_engine.broad_discovery", side_effect=[round1, round2]) as m_bd:
            result = re_engine.layered_research("Foo", sourcer=fake_sourcer)
        assert m_bd.call_count == 2
        _, kwargs = m_bd.call_args_list[1]
        assert kwargs["refinement_hint"] == "try official announcements"
        assert len(result["deep_extracts"]) == 2
        assert result["log"]["rounds_run"] == 2
        assert result["log"]["deep_extracted_count"] == 2
        fake_sourcer.save_seen.assert_called_once()

    def test_stops_after_one_round_once_the_target_is_already_met(self):
        discovery = {
            "topic": "Foo", "task_type": "general",
            "findings": [{"url": f"https://a.com/{i}", "credibility": "unclassified",
                          "title": "t", "snippet": "s"} for i in range(3)],
            "prioritized_urls": [f"https://a.com/{i}" for i in range(3)],
            "log": {"queries": [], "follow_up_strategy": "some hint", "unique_sources_found": 3},
        }
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.side_effect = lambda url: {
            "url": url, "domain": "x", "provider": "firecrawl", "content": "c", "entities": []}
        with mock.patch("agents.research_engine.broad_discovery", return_value=discovery) as m_bd:
            result = re_engine.layered_research("Foo", sourcer=fake_sourcer)
        m_bd.assert_called_once()  # 3 extracts already hits MIN_DEEP_EXTRACTS_TARGET, no 2nd round
        assert len(result["deep_extracts"]) == 3

    def test_stops_early_when_a_round_finds_nothing_new_even_with_rounds_left(self):
        # Same discovery returned every round (e.g. a genuinely thin topic
        # where refined queries still land on the same sources) must not
        # burn through every remaining round doing repeat work.
        discovery = self._discovery("https://a.com/1", follow_up_strategy="widen scope")
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.side_effect = lambda url: {
            "url": url, "domain": "x", "provider": "firecrawl", "content": "c", "entities": []}
        with mock.patch("agents.research_engine.broad_discovery", return_value=discovery) as m_bd:
            result = re_engine.layered_research("Foo", sourcer=fake_sourcer, max_rounds=4)
        assert m_bd.call_count == 2  # round 2 found nothing new -> stop, don't try rounds 3/4
        assert len(result["deep_extracts"]) == 1

    def test_never_exceeds_max_rounds(self):
        # Every round finds exactly one NEW url (so the "zero new findings"
        # early-stop never fires) but never reaches MIN_DEEP_EXTRACTS_TARGET
        # -- max_rounds itself must still be the thing that stops it.
        counter = iter(range(1, 100))
        fake_sourcer = mock.Mock()
        fake_sourcer.fetch_page.side_effect = lambda url: {
            "url": url, "domain": "x", "provider": "firecrawl", "content": "c", "entities": []}
        with mock.patch("agents.research_engine.broad_discovery",
                         side_effect=lambda *a, **kw: self._discovery(f"https://a.com/{next(counter)}",
                                                                       follow_up_strategy="keep trying")) as m_bd:
            result = re_engine.layered_research("Foo", sourcer=fake_sourcer, max_rounds=2)
        assert m_bd.call_count == 2
        assert len(result["deep_extracts"]) == 2


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


def test_evidence_block_ranks_findings_and_extracts_by_credibility_not_insertion_order():
    # Real gap this closes: a second discovery round's low-tier hit landing
    # after a first round's security-research source used to render in
    # insertion order -- the highest-value source should always come first,
    # regardless of which round found it.
    result = {
        "topic": "Foo", "task_type": "threat_analysis", "known_facts": {},
        "findings": [{"url": "https://x.com/social", "credibility": "social_unverified",
                      "title": "social hit", "snippet": "s"},
                     {"url": "https://rekt.news/a", "credibility": "security_research",
                      "title": "sec hit", "snippet": "s"}],
        "deep_extracts": [{"url": "https://x.com/social", "credibility": "social_unverified", "content": "weak"},
                           {"url": "https://rekt.news/a", "credibility": "security_research", "content": "strong"}],
    }
    block = re_engine._evidence_block(result)
    assert block.index("sec hit") < block.index("social hit")
    assert block.index("SOURCE: https://rekt.news/a") < block.index("SOURCE: https://x.com/social")


def test_evidence_block_does_not_mutate_the_callers_lists():
    findings = [{"url": "https://x.com/social", "credibility": "social_unverified", "title": "s", "snippet": "s"},
                {"url": "https://rekt.news/a", "credibility": "security_research", "title": "s", "snippet": "s"}]
    result = {"topic": "Foo", "task_type": "general", "known_facts": {}, "findings": findings, "deep_extracts": []}
    re_engine._evidence_block(result)
    assert findings[0]["url"] == "https://x.com/social"  # original order untouched


def test_evidence_block_gives_higher_credibility_sources_a_larger_character_budget():
    long_text = "x" * 5000
    result = {
        "topic": "Foo", "task_type": "general", "known_facts": {}, "findings": [],
        "deep_extracts": [{"url": "https://rekt.news/a", "credibility": "security_research", "content": long_text},
                           {"url": "https://x.com/social", "credibility": "social_unverified", "content": long_text}],
    }
    block = re_engine._evidence_block(result)
    sec_excerpt_len = len(block.split("SOURCE: https://rekt.news/a")[1].split("SOURCE:")[0])
    social_excerpt_len = len(block.split("SOURCE: https://x.com/social")[1])
    assert sec_excerpt_len > social_excerpt_len


def test_evidence_block_surfaces_entities_ahead_of_the_excerpt():
    result = {
        "topic": "Foo", "task_type": "threat_analysis", "known_facts": {}, "findings": [],
        "deep_extracts": [{"url": "https://rekt.news/a", "credibility": "security_research",
                            "content": "long prose " * 500,
                            "entities": ["0x" + "aa" * 20, "CVE-2026-1234"]}],
    }
    block = re_engine._evidence_block(result)
    assert "Entities found on this page: 0x" + "aa" * 20 + ", CVE-2026-1234" in block
    assert block.index("Entities found on this page") < block.index("long prose")


def test_evidence_block_omits_entities_line_when_none_present():
    result = {"topic": "Foo", "task_type": "general", "known_facts": {}, "findings": [],
              "deep_extracts": [{"url": "https://rekt.news/a", "credibility": "security_research",
                                  "content": "no entities here"}]}
    block = re_engine._evidence_block(result)
    assert "Entities found on this page" not in block


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
        assert "GAPS_JSON trailer parse failed" in capsys.readouterr().out

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

    # ── thin-evidence prompt path ─────────────────────────────────────────
    def _rich_result(self):
        return {"topic": "Foo", "task_type": "threat_analysis", "known_facts": {},
                "findings": [{"url": f"https://rekt.news/{i}", "credibility": "security_research",
                              "title": f"t{i}", "snippet": "s"} for i in range(3)],
                "deep_extracts": [{"url": "https://rekt.news/0", "credibility": "security_research",
                                    "content": "real extracted content"}],
                "log": {}}

    def test_thin_evidence_uses_the_short_honest_answer_prompt(self):
        # _base_result() has no findings/deep_extracts -> thin by definition.
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result())
        system, _user = m.call_args[0]
        assert "Do NOT try to fill out a full structured report" in system
        assert "Connect evidence across sources" not in system

    def test_rich_evidence_uses_the_full_structured_prompt(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._rich_result())
        system, _user = m.call_args[0]
        assert "Connect evidence across sources" in system
        assert "Do NOT try to fill out a full structured report" not in system

    # ── required-section headings baked into the core (non-thin) prompt ───
    def test_rich_evidence_requests_the_task_types_required_headings(self):
        # Real gap this closes: required_sections used to be checked only
        # post-hoc by review_output() -- the model itself was never told
        # what headings a threat_analysis report needs unless a specific
        # caller (agents/hack_agent.py) hand-wrote its own instruction.
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._rich_result())  # task_type="threat_analysis"
        system, _user = m.call_args[0]
        assert "## Known Facts" in system
        assert "## Timeline" in system
        assert "## Root Cause" in system
        assert "## Impact" in system
        assert "## Response & Mitigation" in system

    def test_required_headings_omit_the_mechanically_rendered_sections(self):
        # Gaps & Confidence and Research Methodology and Sources are always
        # rendered separately by render_gaps_section()/render_methodology_
        # log() after synthesize() returns -- asking the model to also
        # write those headings would duplicate them in the final report.
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._rich_result())
        system, _user = m.call_args[0]
        assert "## Gaps & Confidence" not in system
        assert "## Research Methodology and Sources" not in system

    def test_required_headings_are_task_type_specific(self):
        result = dict(self._rich_result())
        result["task_type"] = "general"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)
        system, _user = m.call_args[0]
        assert "## Findings" in system
        assert "## Known Facts" not in system  # threat_analysis-only heading

    def test_news_report_injects_no_rigid_heading_mandate(self):
        # Real, live bug (2026-08-01): news_report's required_sections used
        # to hardcode "What Happened"/"Key Statements"/"Context & Impact",
        # and this instruction was injected BEFORE agents/news_reporter.py's
        # own extra_instructions in the same prompt -- every live article
        # kept the same three-heading template regardless of how carefully
        # news_reporter.py's own "adapt your structure" instruction was
        # worded, because the rigid mandate always won. Confirmed via the
        # actual published article at intel/news/news-2026-08-01-
        # centralization-crisis-deepens-as-japanese-mining-giant-sbi-c.md.
        result = dict(self._rich_result())
        result["task_type"] = "news_report"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result, extra_instructions="Adapt your structure to the story.")
        system, _user = m.call_args[0]
        assert "exact Markdown headings" not in system
        assert "What Happened" not in system
        assert "Key Statements" not in system
        assert "Context & Impact" not in system
        assert "Adapt your structure to the story." in system

    def test_thin_evidence_does_not_request_required_headings(self):
        # The thin-evidence path (item #2) explicitly tells the model to
        # skip headings it has nothing to fill -- baking in a hard heading
        # requirement there would defeat that fix.
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result())  # thin by definition
        system, _user = m.call_args[0]
        assert "## Known Facts" not in system

    # ── canonical reported/headline loss figure sentence ───────────────────
    def test_known_loss_figure_is_called_out_as_canonical_reported_number(self):
        result = self._base_result()
        result["known_facts"] = {"loss_usd_m": 12.5}
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)
        system, _user = m.call_args[0]
        assert "loss_usd_m=12.5" in system
        assert "reported/headline loss figure" in system

    def test_loss_figure_sentence_omitted_when_no_loss_fact_present(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result())  # known_facts={}
        system, _user = m.call_args[0]
        assert "reported/headline loss figure" not in system

    def test_loss_figure_sentence_checks_alternate_known_facts_key_names(self):
        result = self._base_result()
        result["known_facts"] = {"amount_usd_m": 3.2}
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)
        system, _user = m.call_args[0]
        assert "amount_usd_m=3.2" in system

    def test_loss_figure_sentence_also_present_in_thin_evidence_path(self):
        # shared_rules (including this sentence) applies to both prompt
        # paths -- the distinction between reported and confirmed figures
        # matters just as much when evidence is thin.
        result = self._base_result()
        result["known_facts"] = {"loss_usd_m": 12.5}
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)  # thin by definition (no findings/deep_extracts)
        system, _user = m.call_args[0]
        assert "Do NOT try to fill out a full structured report" in system
        assert "reported/headline loss figure" in system

    def test_zero_loss_value_is_not_treated_as_a_real_figure(self):
        result = self._base_result()
        result["known_facts"] = {"loss_usd_m": 0}
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)
        system, _user = m.call_args[0]
        assert "reported/headline loss figure" not in system

    def test_thin_evidence_still_appends_header_and_trailer_instructions(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result(), trailers=self._GAPS_AND_VERDICT_TRAILERS)
        system, _user = m.call_args[0]
        assert "Do NOT try to fill out a full structured report" in system
        assert "VERDICT ALIGNMENT" in system

    def test_short_raw_user_block_is_treated_as_thin(self):
        result = {"topic": "Foo", "task_type": "general", "raw_user_block": "Nothing found.", "log": {}}
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)
        system, _user = m.call_args[0]
        assert "Do NOT try to fill out a full structured report" in system

    def test_long_raw_user_block_is_not_treated_as_thin(self):
        result = {"topic": "Foo", "task_type": "general", "raw_user_block": "x" * 500, "log": {}}
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(result)
        system, _user = m.call_args[0]
        assert "Do NOT try to fill out a full structured report" not in system

    _GAPS_AND_VERDICT_TRAILERS = [
        {"type": "json", "name": "gaps", "label": "GAPS_JSON"},
        {"type": "enum", "name": "verdict", "label": "VERDICT ALIGNMENT", "options": ("AGREE", "DISAGREE")},
    ]

    def test_verdict_omitted_by_default(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")):
            result = re_engine.synthesize(self._base_result())
        assert result["verdict"] is None

    def test_verdict_parsed_from_absolute_last_line(self):
        text = "Real analysis.\nGAPS_JSON: []\nVERDICT ALIGNMENT: DISAGREE"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), trailers=self._GAPS_AND_VERDICT_TRAILERS)
        assert result["verdict"] == "DISAGREE"
        assert "VERDICT ALIGNMENT" not in result["narrative"]
        assert "GAPS_JSON" not in result["narrative"]

    def test_verdict_case_insensitive_but_normalized_to_declared_casing(self):
        text = "Real analysis.\nverdict alignment: agree"
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), trailers=self._GAPS_AND_VERDICT_TRAILERS)
        assert result["verdict"] == "AGREE"

    def test_verdict_not_matched_when_not_the_final_line(self):
        # Real anti-injection fix this preserves (investigate.py PR #277):
        # an occurrence of the marker text anywhere BUT the final line must
        # never be treated as the real verdict — untrusted evidence quoted
        # or injected earlier in the response could otherwise contain it.
        text = "VERDICT ALIGNMENT: DISAGREE\nBut actually here is more analysis after that."
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), trailers=self._GAPS_AND_VERDICT_TRAILERS)
        assert result["verdict"] is None
        assert "VERDICT ALIGNMENT: DISAGREE" in result["narrative"]

    def test_verdict_and_gaps_json_parsed_independently(self):
        text = ('Real analysis.\nGAPS_JSON: [{"description": "gap one", "confidence": 0.5}]\n'
                'VERDICT ALIGNMENT: AGREE')
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), trailers=self._GAPS_AND_VERDICT_TRAILERS)
        assert result["verdict"] == "AGREE"
        assert len(result["gaps"]) == 1
        assert result["gaps"][0]["description"] == "gap one"
        assert result["narrative"] == "Real analysis."

    def test_verdict_only_trailer_produces_no_gaps(self):
        # trailers=[...] replaces the implicit default entirely — a caller
        # that only declares a verdict trailer gets no gaps parsing at all,
        # rather than a silently-always-on GAPS_JSON the caller never asked for.
        text = "Real analysis.\nVERDICT ALIGNMENT: AGREE"
        verdict_only = [{"type": "enum", "name": "verdict", "label": "VERDICT ALIGNMENT",
                          "options": ("AGREE", "DISAGREE")}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), trailers=verdict_only)
        assert result["verdict"] == "AGREE"
        assert result["gaps"] == []

    def test_empty_trailers_list_requests_and_parses_nothing(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("Just narrative.", "oci_grok")) as m:
            result = re_engine.synthesize(self._base_result(), trailers=[])
        assert result["gaps"] == []
        assert result["verdict"] is None
        assert result["narrative"] == "Just narrative."
        system, _user = m.call_args[0]
        assert "GAPS_JSON" not in system

    def test_trailer_options_included_in_system_prompt(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result(), trailers=self._GAPS_AND_VERDICT_TRAILERS)
        system, _user = m.call_args[0]
        assert "VERDICT ALIGNMENT" in system
        assert "AGREE|DISAGREE" in system

    def test_distinctly_named_trailers_do_not_collide(self):
        """Real gap this pins (CodeRabbit, PR #375): _parse_trailers used to
        route every "json" trailer into "gaps" and every "enum" trailer into
        "verdict" regardless of its own declared name — a second json
        trailer would merge into the same list as the first, and a
        non-verdict enum would silently overwrite the real verdict. Each
        trailer's own name must be its own slot in result["trailers"],
        independent of type and of any other trailer's name."""
        text = ("Real analysis.\n"
                'CITATIONS_JSON: [{"description": "cite one", "confidence": 0.9}]\n'
                "SEVERITY: HIGH")
        trailers = [
            {"type": "json", "name": "citations", "label": "CITATIONS_JSON"},
            {"type": "enum", "name": "severity", "label": "SEVERITY", "options": ("LOW", "HIGH")},
        ]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), trailers=trailers)
        assert result["trailers"]["citations"][0]["description"] == "cite one"
        assert result["trailers"]["severity"] == "HIGH"
        # Neither collides into the legacy gaps/verdict convenience aliases,
        # which stay at their defaults since no trailer here is named that.
        assert result["gaps"] == []
        assert result["verdict"] is None

    def test_custom_max_tokens_passed_through(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            re_engine.synthesize(self._base_result(), max_tokens=750)
        _, kwargs = m.call_args
        assert kwargs["max_tokens"] == 750

    # ── header fields (generic HEADLINE:/DEK:/---/body-style contract) ────
    def test_header_fields_parsed_and_stripped_from_narrative(self):
        text = "HEADLINE: Base Hits Record TVL\nDEK: A milestone day.\n---\n## Body\nReal content."
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), header_fields=headers, trailers=[])
        assert result["header"]["headline"] == "Base Hits Record TVL"
        assert result["header"]["dek"] == "A milestone day."
        assert result["narrative"] == "## Body\nReal content."

    def test_header_fields_missing_delimiter_degrades_to_none_not_lost_narrative(self):
        text = "Just plain prose, no header markers at all."
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), header_fields=headers, trailers=[])
        assert result["header"] == {"headline": None, "dek": None}
        assert result["narrative"] == text

    def test_header_delimiter_ignores_markdown_rule_with_no_real_header(self):
        """Real bug this pins (CodeRabbit, PR #375): a bare markdown
        thematic break ('---') the model wrote as part of its own narrative
        must not be mistaken for the header delimiter just because it's the
        first '---' line in the text — only a delimiter preceded by at
        least one actual configured label counts. Otherwise every opening
        paragraph before an unrelated '---' silently vanishes with no
        header fields to show for it either."""
        text = "Opening paragraph the model wrote.\n\n---\n\nMore narrative after a markdown rule."
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), header_fields=headers, trailers=[])
        assert result["header"] == {"headline": None, "dek": None}
        assert result["narrative"] == text

    def test_header_fields_omitted_by_default(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")):
            result = re_engine.synthesize(self._base_result())
        assert result["header"] == {}

    def test_header_and_trailers_both_parsed_together(self):
        text = ("HEADLINE: Big Story\nDEK: Stakes are high.\n---\n"
                'Body text.\nGAPS_JSON: [{"description": "gap", "confidence": 0.4}]')
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), header_fields=headers)
        assert result["header"]["headline"] == "Big Story"
        assert result["narrative"] == "Body text."
        assert len(result["gaps"]) == 1

    def test_custom_header_delimiter(self):
        text = "HEADLINE: Title\n===\nBody here."
        headers = [{"name": "headline", "label": "HEADLINE"}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(text, "oci_grok")):
            result = re_engine.synthesize(self._base_result(), header_fields=headers,
                                           header_delimiter="===", trailers=[])
        assert result["header"]["headline"] == "Title"
        assert result["narrative"] == "Body here."

    def test_raw_user_block_bypasses_structured_evidence_rendering(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            result = dict(self._base_result())
            result["raw_user_block"] = "A fully custom grounding block."
            re_engine.synthesize(result)
        _system, user = m.call_args[0]
        assert user == "A fully custom grounding block."

    def test_prompt_construction_failure_degrades_honestly(self):
        # A malformed findings entry missing a required key used to raise
        # straight out of _evidence_block() with no try/except around it —
        # "never raises" must hold even for a caller's own malformed result.
        result = dict(self._base_result())
        result["findings"] = [{"title": "no url key"}]
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            out = re_engine.synthesize(result)
        assert "unavailable" in out["narrative"]
        m.assert_not_called()

    # ── debug observability: exact prompts used, for offline inspection ───
    def test_debug_carries_the_exact_system_and_user_prompts_used(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")) as m:
            result = re_engine.synthesize(self._rich_result())
        system, user = m.call_args[0]
        assert result["debug"]["system_prompt"] == system
        assert result["debug"]["user_prompt"] == user[:re_engine._DEBUG_USER_PROMPT_CHARS]

    def test_debug_thin_flag_matches_the_evidence_thinness(self):
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")):
            thin_result = re_engine.synthesize(self._base_result())
            rich_result = re_engine.synthesize(self._rich_result())
        assert thin_result["debug"]["thin"] is True
        assert rich_result["debug"]["thin"] is False

    def test_debug_user_prompt_is_truncated_for_a_large_evidence_block(self):
        result = self._rich_result()
        result["deep_extracts"][0]["content"] = "x" * 10000
        with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "oci_grok")):
            out = re_engine.synthesize(result)
        assert len(out["debug"]["user_prompt"]) == re_engine._DEBUG_USER_PROMPT_CHARS

    def test_debug_is_none_when_llm_module_not_importable(self):
        with mock.patch.dict("sys.modules", {"agents.llm": None}):
            result = re_engine.synthesize(self._base_result())
        assert result["debug"] == {"system_prompt": None, "user_prompt": None, "thin": None}

    def test_debug_is_populated_even_when_the_llm_call_fails(self):
        # The prompt was still fully built before the LLM call raised --
        # exactly the case an offline debugger needs to inspect.
        with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=RuntimeError("boom")):
            result = re_engine.synthesize(self._rich_result())
        assert result["debug"]["system_prompt"] is not None
        assert result["debug"]["thin"] is False


# ── _parse_header / _parse_trailers direct unit tests ────────────────────
# Focused, hermetic tests calling these two functions directly (no
# synthesize()/LLM mocking involved) so the parsing contract itself --
# independent of any particular caller's use of it -- has its own coverage.
class TestParseHeaderDirect:
    def test_delimiter_only_counts_when_a_label_actually_matched(self):
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        text = "Opening paragraph.\n\n---\n\nMore narrative after a markdown rule."
        header, body = re_engine._parse_header(text, headers, "---")
        assert header == {"headline": None, "dek": None}
        assert body == text

    def test_real_header_is_parsed_and_stripped(self):
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        text = "HEADLINE: Big News\nDEK: Something happened.\n---\nBody text here."
        header, body = re_engine._parse_header(text, headers, "---")
        assert header == {"headline": "Big News", "dek": "Something happened."}
        assert body == "Body text here."

    def test_labels_are_matched_order_independent(self):
        headers = [{"name": "headline", "label": "HEADLINE"}, {"name": "dek", "label": "DEK"}]
        text = "DEK: Something happened.\nHEADLINE: Big News\n---\nBody text here."
        header, body = re_engine._parse_header(text, headers, "---")
        assert header == {"headline": "Big News", "dek": "Something happened."}

    def test_no_header_fields_requested_returns_full_text_untouched(self):
        header, body = re_engine._parse_header("Plain narrative.", [], "---")
        assert header == {}
        assert body == "Plain narrative."

    def test_first_candidate_delimiter_without_a_label_is_skipped_for_a_later_real_one(self):
        # Two '---' occurrences: the first is a bare markdown rule inside
        # the narrative itself, the second is the real header/body
        # delimiter -- every occurrence must be tried, not just the first.
        headers = [{"name": "headline", "label": "HEADLINE"}]
        text = "Some prose.\n\n---\n\nHEADLINE: Real Title\n---\nBody after real header."
        header, body = re_engine._parse_header(text, headers, "---")
        assert header == {"headline": "Real Title"}
        assert body == "Body after real header."


class TestParseTrailersDirect:
    def test_processes_in_reverse_declared_order_so_earlier_trailers_still_parse(self):
        # Real anti-injection property this pins: the JSON trailer's own
        # regex requires it to end at the string's end ($) -- if trailers
        # were parsed in forward-declared order, the JSON trailer would
        # look for its own match at the string's end while the enum
        # trailer's line is still physically after it, and would silently
        # fail to find it. Reverse-order parsing strips the last-declared
        # trailer first so every earlier trailer still sees itself as the
        # new "end" of the text.
        trailers = [{"type": "json", "name": "citations", "label": "CITATIONS_JSON"},
                    {"type": "enum", "name": "severity", "label": "SEVERITY", "options": ("LOW", "HIGH")}]
        text = ('Real narrative.\nCITATIONS_JSON: [{"description": "c1", "confidence": 0.5}]\n'
                'SEVERITY: HIGH')
        named, body = re_engine._parse_trailers(text, trailers)
        assert named["citations"][0]["description"] == "c1"
        assert named["severity"] == "HIGH"
        assert body == "Real narrative."

    def test_enum_trailer_only_matches_the_current_last_non_empty_line(self):
        # Anti-injection: untrusted evidence quoted earlier in the response
        # could contain the marker text -- only the physically-last line
        # is ever trusted as the real trailer value.
        trailers = [{"type": "enum", "name": "verdict", "label": "VERDICT", "options": ("AGREE", "DISAGREE")}]
        text = "VERDICT: DISAGREE\nMore text injected after it."
        named, body = re_engine._parse_trailers(text, trailers)
        assert named["verdict"] is None
        assert body == text  # narrative left fully intact, nothing stripped

    def test_malformed_json_trailer_leaves_default_and_logs_not_raises(self, capsys):
        trailers = [{"type": "json", "name": "gaps", "label": "GAPS_JSON"}]
        text = "Real analysis.\nGAPS_JSON: [{not: valid, json}]"
        named, body = re_engine._parse_trailers(text, trailers)
        assert named["gaps"] == []
        assert "Real analysis." in body
        assert "GAPS_JSON trailer parse failed" in capsys.readouterr().out

    def test_no_trailers_requested_returns_empty_dict_and_full_text(self):
        named, body = re_engine._parse_trailers("Plain text.", [])
        assert named == {}
        assert body == "Plain text."


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
