"""Tests for agents/news_reporter.py — candidate picking, the reporter/editor
two-pass pipeline, and honest degradation when the editorial pass can't run.
Hermetic: every LLM/web-search/network call is mocked, no real network or
git-tracked file writes (write_news_report is redirected into tmp_path).
"""
import json
from datetime import datetime, timezone
from unittest import mock

from agents import news_common as nc
from agents import news_reporter


def test_publish_stamp_formats_iso_utc_and_et_in_summer():
    now_utc = datetime(2026, 8, 1, 14, 30, 0, tzinfo=timezone.utc)
    date_iso, published_et = news_reporter._publish_stamp(now_utc)
    assert date_iso == "2026-08-01T14:30:00Z"
    assert published_et == "August 1, 2026 · 10:30 AM EDT"


def test_publish_stamp_formats_et_in_winter_standard_time():
    """EST vs EDT is resolved from the real date via zoneinfo, not
    hardcoded -- this crosses the DST boundary into standard time."""
    now_utc = datetime(2026, 1, 15, 20, 5, 0, tzinfo=timezone.utc)
    date_iso, published_et = news_reporter._publish_stamp(now_utc)
    assert date_iso == "2026-01-15T20:05:00Z"
    assert published_et == "January 15, 2026 · 3:05 PM EST"


def test_publish_stamp_crosses_a_calendar_date_going_from_utc_to_et():
    """UTC late night rolls back to the previous ET calendar date -- the
    ET stamp must reflect the reader's own date, not a bare UTC-minus-hours
    that silently keeps the wrong day."""
    now_utc = datetime(2026, 8, 1, 3, 4, 0, tzinfo=timezone.utc)
    date_iso, published_et = news_reporter._publish_stamp(now_utc)
    assert date_iso == "2026-08-01T03:04:00Z"
    assert published_et == "July 31, 2026 · 11:04 PM EDT"


def test_is_derivative_headline_true_when_blank():
    assert news_reporter._is_derivative_headline(None, "Some Source Headline") is True
    assert news_reporter._is_derivative_headline("   ", "Some Source Headline") is True


def test_is_derivative_headline_true_for_exact_match_case_and_whitespace_insensitive():
    assert news_reporter._is_derivative_headline(
        "  Bitcoin Rallies Past $100K  ", "bitcoin rallies past $100k") is True


def test_is_derivative_headline_true_for_near_duplicate():
    assert news_reporter._is_derivative_headline(
        "Bitcoin Rallies Past $100000", "Bitcoin Rallies Past $100K") is True


def test_is_derivative_headline_false_for_genuinely_distinct_headline():
    assert news_reporter._is_derivative_headline(
        "Bitcoin Tops $100K", "Bitcoin Rallies Past $100K") is False
    assert news_reporter._is_derivative_headline(
        "Rally Deepens", "Crypto markets rally") is False


def test_pick_candidates_skips_already_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    with open(nc.FEED_PATH, "w") as f:
        json.dump({"headlines": [
            {"title": "A", "url": "https://a.example/1", "topic": "base"},
            {"title": "B", "url": "https://b.example/2", "topic": "macro"},
        ]}, f)
    state = {"reported_urls": ["https://a.example/1"], "seen": {}}
    picked = news_reporter._pick_candidates(state, 1)
    assert len(picked) == 1
    assert picked[0]["url"] == "https://b.example/2"


def test_pick_candidates_prefers_topic_diversity(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    with open(nc.FEED_PATH, "w") as f:
        json.dump({"headlines": [
            {"title": "A", "url": "https://a.example/1", "topic": "base"},
            {"title": "B", "url": "https://b.example/2", "topic": "base"},
            {"title": "C", "url": "https://c.example/3", "topic": "macro"},
        ]}, f)
    picked = news_reporter._pick_candidates({"reported_urls": [], "seen": {}}, 2)
    topics = {p["topic"] for p in picked}
    assert topics == {"base", "macro"}


def test_pick_candidates_returns_empty_when_all_reported(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    with open(nc.FEED_PATH, "w") as f:
        json.dump({"headlines": [{"title": "A", "url": "https://a.example/1", "topic": "base"}]}, f)
    state = {"reported_urls": ["https://a.example/1"], "seen": {}}
    assert news_reporter._pick_candidates(state, 3) == []


def _synth(headline, dek, body):
    """Builds the dict shape agents.research_engine.synthesize() returns,
    for mocking write_story()'s drafting call."""
    return {"narrative": body, "header": {"headline": headline, "dek": dek},
            "gaps": [], "verdict": None, "provider": "oci_grok"}


def test_editorial_pass_uses_edited_text_when_available():
    with mock.patch("agents.intel_common.grok_analysis", return_value="Cleaned up, fact-checked body."):
        body, fact_checked = news_reporter._editorial_pass("grounding text", "raw draft")
    assert body == "Cleaned up, fact-checked body."
    assert fact_checked is True


def test_editorial_pass_keeps_draft_when_editor_unavailable():
    with mock.patch("agents.intel_common.grok_analysis",
                     return_value="_Analyst narrative unavailable this cycle (no LLM provider reachable)._"):
        body, fact_checked = news_reporter._editorial_pass("grounding text", "raw draft")
    assert body == "raw draft"
    assert fact_checked is False


# ── _looks_truncated() -- real, live bug (2026-08-01): a Vertex-tuned
#    Gemini candidate with a non-STOP finishReason (see agents/llm.py's
#    _call_vertex_tuned() fix) returned a real but partial fragment that
#    got published cut off mid-sentence inside an unclosed markdown link.
#    This gate is the news_reporter-side defense-in-depth on top of that
#    upstream fix -- catches ANY future truncation regardless of cause. ──

def test_looks_truncated_true_for_unclosed_markdown_link():
    body = ("Next week the network is expected to review the release, "
             "according to a [CoinDesk report](https://www.coindesk.com/tech/2026/08/01/xrp")
    assert news_reporter._looks_truncated(body) is True


def test_looks_truncated_true_for_body_ending_mid_word_no_punctuation():
    assert news_reporter._looks_truncated("The upgrade will reintroduce two features previously withdrawn due to") is True


def test_looks_truncated_false_for_a_genuinely_complete_body():
    body = ("## What Happened\n\nThe XRP Ledger is preparing for a network upgrade next week. "
             "Read the [full report](https://example.com/report) for details.")
    assert news_reporter._looks_truncated(body) is False


def test_looks_truncated_false_for_body_ending_in_closing_markdown():
    assert news_reporter._looks_truncated("Watch for the next disclosure from the *validator set*") is False
    assert news_reporter._looks_truncated("Watch for the next disclosure from the validator set.") is False


def test_looks_truncated_true_for_empty_body():
    assert news_reporter._looks_truncated("") is True
    assert news_reporter._looks_truncated(None) is True


def test_looks_truncated_true_for_url_with_its_own_balanced_parens():
    """A real URL can legitimately contain a balanced parenthesized segment
    (e.g. a Wikipedia-style '/Foo_(bar)' path) -- the naive check this
    replaced mistook that inner ')' for the outer markdown link's own
    closing paren and returned False here, when the link is genuinely
    still unclosed (CodeRabbit, PR #394)."""
    assert news_reporter._looks_truncated("[source](https://example.test/Foo_(bar)") is True


def test_looks_truncated_false_for_a_link_whose_url_has_balanced_parens_and_actually_closes():
    body = "See the [source](https://example.test/Foo_(bar)) for details."
    assert news_reporter._looks_truncated(body) is False


def test_write_story_returns_none_when_editorial_output_looks_truncated(tmp_path, monkeypatch):
    """End-to-end: a body that survives the derivative-headline/blank-dek
    gates but comes back from the editorial pass cut off mid-sentence must
    still never be published -- same real bug this closes as the unit
    tests above, exercised through the actual write_story() path."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "XRP Ledger upgrade brings back features once pulled over critical bugs",
                 "url": "https://example.com/story", "source": "CoinDesk",
                 "published": "2026-08-01T00:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary."}
    truncated_body = ("Next week the validator network is expected to review the release, according "
                       "to a [CoinDesk report](https://www.coindesk.com/tech/2026/08/01/xrp")

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("Second Time's the Charm?", "A dek.", "Full untruncated draft.")), \
         mock.patch("agents.intel_common.grok_analysis", return_value=truncated_body), \
         mock.patch("agents.intel_common.log_sweep_memory") as memlog:
        result = news_reporter.write_story(candidate)

    assert result is None
    memlog.assert_not_called()  # never reaches the "wrote a real report" bookkeeping


def test_write_story_marks_fact_checked_and_includes_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "DeFi protocol patches bug", "url": "https://example.com/story",
                 "source": "The Block", "published": "2026-07-27T09:00:00Z", "topic": "defi-security"}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily",
                                   "results": [{"title": "Corroborating piece", "url": "https://example.com/corr",
                                                "snippet": "confirms the patch"}]}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch.object(news_reporter, "_generate_ai_image", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("The Patch That Saved Millions", "A close call.", "## Details\nBody text.")), \
         mock.patch("agents.intel_common.grok_analysis", return_value="## Details\nEdited body text."), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        path = news_reporter.write_story(candidate)

    text = open(path).read()
    assert "The Patch That Saved Millions" in text
    assert "Fact-checked:** Yes" in text
    assert "Edited body text." in text
    assert "Corroborating piece" in text
    assert "**Agency:** VAPE Wire" in text
    assert "**Image:** assets/logo-v-256.png" in text
    assert "brand mark" in text
    assert "**Date:**" in text  # machine-parseable UTC ISO timestamp
    assert "**Published:**" in text  # human-facing US Eastern-time stamp


def test_write_story_falls_back_to_brand_mark_when_no_ai_image(tmp_path, monkeypatch):
    """VAPE never republishes a source outlet's own photo (legal/copyright
    exposure, explicit direction 2026-07-28) -- when AI generation is
    unavailable this cycle, the only fallback is VAPE's own brand mark, even
    if the candidate carries a real photo URL from its discovery lane."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Crypto markets rally", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-27T09:00:00Z", "topic": "crypto-markets",
                 "image": "https://example.com/real-photo.jpg"}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily",
                                   "results": [{"title": "Corroborating piece", "url": "https://example.com/corr",
                                                "snippet": "confirms the rally"}]}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch.object(news_reporter, "_generate_ai_image", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("Rally Deepens", "Momentum builds.", "Body text.")), \
         mock.patch("agents.intel_common.grok_analysis", return_value="Body text."), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None), \
         mock.patch.object(nc, "brand_image") as brand:
        path = news_reporter.write_story(candidate)

    text = open(path).read()
    assert "**Image:** assets/logo-v-256.png" in text
    assert "brand mark" in text
    brand.assert_not_called()  # no source-photo tier exists to call it from


def test_write_story_uses_ai_generated_image_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Crypto markets rally", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-27T09:00:00Z", "topic": "crypto-markets"}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily",
                                   "results": [{"title": "Corroborating piece", "url": "https://example.com/corr",
                                                "snippet": "confirms the rally"}]}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch.object(news_reporter, "_generate_ai_image",
                            return_value="assets/news-images/rally-deepens.jpg") as gen_ai, \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("Rally Deepens", "Momentum builds.", "Body text.")), \
         mock.patch("agents.intel_common.grok_analysis", return_value="Body text."), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        path = news_reporter.write_story(candidate)

    text = open(path).read()
    assert "**Image:** assets/news-images/rally-deepens.jpg" in text
    assert "AI-generated — VAPE Wire branded" in text
    gen_ai.assert_called_once()


def test_image_prompt_returns_none_when_llm_unavailable():
    with mock.patch("agents.intel_common.grok_analysis",
                     return_value="_Analyst narrative unavailable this cycle (no LLM provider reachable)._"):
        assert news_reporter._image_prompt("Headline", "Dek", "Body text", "Crypto Markets") is None


def test_image_prompt_returns_stripped_text():
    with mock.patch("agents.intel_common.grok_analysis", return_value="  A close-up of gold coins.  "):
        assert news_reporter._image_prompt("Headline", "Dek", "Body text", "Crypto Markets") == "A close-up of gold coins."


def test_image_styles_are_all_nonempty_strings():
    assert len(news_reporter.IMAGE_STYLES) == 30
    assert len(set(news_reporter.IMAGE_STYLES)) == len(news_reporter.IMAGE_STYLES)
    for style in news_reporter.IMAGE_STYLES:
        assert isinstance(style, str) and style.strip()


def test_image_prompt_picks_a_style_and_bakes_it_into_the_instructions():
    """The whole point of the rotation is that the model can't fall back to
    a hardcoded photorealistic default -- confirm the chosen style's own
    text actually reaches grok_analysis()'s instructions, not just that a
    style was picked and silently ignored."""
    with mock.patch("agents.news_reporter.random.choice", return_value=news_reporter.IMAGE_STYLES[3]) as choice, \
         mock.patch("agents.intel_common.grok_analysis", return_value="a prompt") as grok:
        news_reporter._image_prompt("Headline", "Dek", "Body text", "Crypto Markets")
    choice.assert_called_once_with(news_reporter.IMAGE_STYLES)
    instructions = grok.call_args.kwargs["instructions"]
    assert news_reporter.IMAGE_STYLES[3] in instructions


def test_image_prompt_style_rotation_produces_more_than_one_style_across_many_calls():
    """A real regression this guards against: a rotation list that never
    actually gets exercised (e.g. a copy-paste bug that always indexes [0])
    would look correct at a glance but always emit the same style anyway."""
    seen_styles = set()
    chosen_styles = [news_reporter.IMAGE_STYLES[0], news_reporter.IMAGE_STYLES[1]]
    with mock.patch(
        "agents.news_reporter.random.choice",
        side_effect=chosen_styles * 30,
    ), mock.patch("agents.intel_common.grok_analysis") as grok:
        def _capture(*_args, **kwargs):
            seen_styles.add(next(s for s in news_reporter.IMAGE_STYLES if s in kwargs["instructions"]))
            return "a prompt"
        grok.side_effect = _capture
        for _ in range(60):
            news_reporter._image_prompt("Headline", "Dek", "Body text", "Crypto Markets")
    assert seen_styles == set(chosen_styles)


def test_generate_ai_image_returns_none_when_no_prompt():
    with mock.patch.object(news_reporter, "_image_prompt", return_value=None):
        assert news_reporter._generate_ai_image("H", "D", "B", "Topic", "slug") is None


def test_generate_ai_image_returns_none_when_both_models_fail():
    with mock.patch.object(news_reporter, "_image_prompt", return_value="a prompt"), \
         mock.patch("agents.llm.ask_xai_image", return_value=None), \
         mock.patch("agents.llm.ask_gemini_image", return_value=None):
        assert news_reporter._generate_ai_image("H", "D", "B", "Topic", "slug") is None


def test_generate_ai_image_tries_xai_first_and_brands_the_url():
    """xAI Grok Image is tried first (promoted to primary 2026-08-01, since
    Gemini/Vertex are both confirmed dead ends right now) -- a success there
    must short-circuit before ever calling Gemini."""
    with mock.patch.object(news_reporter, "_image_prompt", return_value="a prompt"), \
         mock.patch("agents.llm.ask_xai_image", return_value="https://xai.example/generated.png") as xai, \
         mock.patch("agents.llm.ask_gemini_image") as gemini, \
         mock.patch.object(nc, "brand_image", return_value="assets/news-images/slug.jpg") as brand:
        result = news_reporter._generate_ai_image("H", "D", "B", "Topic", "slug")
    assert result == "assets/news-images/slug.jpg"
    xai.assert_called_once_with("a prompt")
    gemini.assert_not_called()
    brand.assert_called_once_with("https://xai.example/generated.png", "slug")


def test_generate_ai_image_falls_back_to_gemini_when_xai_fails():
    with mock.patch.object(news_reporter, "_image_prompt", return_value="a prompt"), \
         mock.patch("agents.llm.ask_xai_image", return_value=None), \
         mock.patch("agents.llm.ask_gemini_image", return_value=b"fake-png-bytes"), \
         mock.patch.object(nc, "brand_image", return_value="assets/news-images/slug.jpg") as brand:
        result = news_reporter._generate_ai_image("H", "D", "B", "Topic", "slug")
    assert result == "assets/news-images/slug.jpg"
    brand.assert_called_once_with(b"fake-png-bytes", "slug")


def test_generate_ai_image_falls_back_to_gemini_when_xai_url_fails_to_brand():
    """xAI returns a real image URL, but brand_image() itself fails (a
    transient fetch/composite error) -- must fall through to Gemini rather
    than giving up on a real xAI image just because branding choked on it."""
    with mock.patch.object(news_reporter, "_image_prompt", return_value="a prompt"), \
         mock.patch("agents.llm.ask_xai_image", return_value="https://xai.example/generated.png"), \
         mock.patch("agents.llm.ask_gemini_image", return_value=b"fake-png-bytes") as gemini, \
         mock.patch.object(nc, "brand_image", side_effect=[None, "assets/news-images/slug.jpg"]) as brand:
        result = news_reporter._generate_ai_image("H", "D", "B", "Topic", "slug")
    assert result == "assets/news-images/slug.jpg"
    gemini.assert_called_once_with("a prompt")
    assert brand.call_args_list == [
        mock.call("https://xai.example/generated.png", "slug"),
        mock.call(b"fake-png-bytes", "slug"),
    ]


def test_write_story_includes_native_rss_snippet_in_grounding(tmp_path, monkeypatch):
    """A candidate discovered via the native-RSS lane carries the outlet's
    own feed summary as candidate["snippet"] -- confirms it reaches the
    grounding text passed to the drafting call, not just the corroboration
    search results."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Bitcoin Rallies Past $100K", "url": "https://www.coindesk.com/story",
                 "source": "CoinDesk", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "Bitcoin surged past $100,000 as spot ETF inflows accelerated this week."}
    captured = {}

    def fake_synthesize(result, **kw):
        captured["grounding"] = result["raw_user_block"]
        return _synth("Bitcoin Tops $100K", "A milestone.", "Body text.")

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": False, "provider": None, "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch.object(news_reporter, "_generate_ai_image", return_value=None), \
         mock.patch("agents.research_engine.synthesize", side_effect=fake_synthesize), \
         mock.patch("agents.intel_common.grok_analysis", return_value="Body text."), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        news_reporter.write_story(candidate)

    assert "Source outlet's own summary:" in captured["grounding"]
    assert "Bitcoin surged past $100,000" in captured["grounding"]


def test_write_story_returns_none_when_nothing_sourceable(tmp_path, monkeypatch):
    """The 'only report on what we can source' gate (explicit direction,
    2026-07-28): a bare headline with no scraped body, no outlet snippet,
    and no corroborating search hit must never reach the drafting LLM call
    -- it has nothing real to report on."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Some thin headline", "url": "https://example.com/thin",
                 "source": "Nowhere", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets"}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch("agents.research_engine.synthesize") as synth:
        result = news_reporter.write_story(candidate)

    assert result is None
    synth.assert_not_called()  # no LLM spend on a candidate with nothing real to report


def test_write_story_skips_candidate_when_synthesis_unavailable(tmp_path, monkeypatch):
    """An unavailable-LLM sentinel must never be published as a story
    (CodeRabbit, PR #375) -- write_story() checks the narrative for the
    "_Synthesis unavailable" prefix before ever reaching the editorial pass
    or writing a report."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Some headline", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary."}
    unavailable = {"narrative": "_Synthesis unavailable this cycle (LLM call failed)._",
                   "header": {"headline": None, "dek": None},
                   "gaps": [], "verdict": None, "provider": None}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch("agents.research_engine.synthesize", return_value=unavailable), \
         mock.patch("agents.intel_common.grok_analysis") as editor:
        result = news_reporter.write_story(candidate)

    assert result is None
    editor.assert_not_called()  # no copy-desk spend on a story that was never drafted


def test_write_story_returns_none_when_headline_is_blank(tmp_path, monkeypatch):
    """The HEADLINE drafting instruction is prompt-only -- write_story()
    must not fall back to candidate["title"] (the source's own headline)
    when the model returns a blank headline, since that would silently
    publish the exact copy the originality requirement exists to prevent
    (CodeRabbit, PR #390)."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Some real headline", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary."}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth(None, "A dek.", "Body text.")), \
         mock.patch("agents.intel_common.grok_analysis") as editor:
        result = news_reporter.write_story(candidate)

    assert result is None
    editor.assert_not_called()  # no copy-desk spend on a headline that failed the guard


def test_write_story_returns_none_when_headline_copies_source_title(tmp_path, monkeypatch):
    """Same guard, the other failure mode: the model returns the source
    outlet's own headline verbatim instead of writing an original one."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Bitcoin Rallies Past $100K", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary."}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("Bitcoin Rallies Past $100K", "A dek.", "Body text.")), \
         mock.patch("agents.intel_common.grok_analysis") as editor:
        result = news_reporter.write_story(candidate)

    assert result is None
    editor.assert_not_called()


def test_write_story_returns_none_when_dek_is_blank(tmp_path, monkeypatch):
    """The DEK instruction asks for a genuine sub-headline -- a blank DEK
    (empty string or None) must fail the same deterministic gate as a
    blank/derivative headline, not pass through silently (CodeRabbit,
    PR #390)."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Some real headline", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary."}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("A Genuinely Original Headline", "  ", "Body text.")), \
         mock.patch("agents.intel_common.grok_analysis") as editor:
        result = news_reporter.write_story(candidate)

    assert result is None
    editor.assert_not_called()


def test_write_story_proceeds_when_only_snippet_is_real(tmp_path, monkeypatch):
    """A native-RSS candidate.get('snippet') alone is enough real substance
    to clear the gate, even with no scrape and no corroboration."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Some thin headline", "url": "https://example.com/thin",
                 "source": "CoinDesk", "published": "2026-07-28T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary of what happened."}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily", "results": []}), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch.object(news_reporter, "_generate_ai_image", return_value=None), \
         mock.patch("agents.research_engine.synthesize",
                     return_value=_synth("Title", "Dek.", "Body.")), \
         mock.patch("agents.intel_common.grok_analysis", return_value="Body."), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        result = news_reporter.write_story(candidate)

    assert result is not None


def test_run_retries_next_candidate_when_one_has_no_substance(tmp_path, monkeypatch):
    """run()'s bounded retry loop: a thin, unsourceable headline is marked
    reported and skipped without stopping the cycle -- the next candidate
    still gets a real shot at NEWS_REPORTER_PICKS."""
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    monkeypatch.setattr(nc, "STATE_PATH", str(tmp_path / "news-state.json"))
    monkeypatch.setenv("NEWS_REPORTER_PICKS", "1")
    with open(nc.FEED_PATH, "w") as f:
        json.dump({"headlines": [
            {"title": "Thin headline", "url": "https://a.example/1", "topic": "base"},
            {"title": "Real headline", "url": "https://b.example/2", "topic": "macro"},
        ]}, f)

    calls = {"n": 0}

    def fake_write_story(candidate):
        calls["n"] += 1
        return None if candidate["url"] == "https://a.example/1" else f"{tmp_path}/written.md"

    with mock.patch.object(news_reporter, "write_story", side_effect=fake_write_story):
        written = news_reporter.run()

    assert written == [f"{tmp_path}/written.md"]
    assert calls["n"] == 2
    state = nc.load_state()
    assert nc.is_reported(state, "https://a.example/1")
    assert nc.is_reported(state, "https://b.example/2")


def test_run_stops_after_bounded_attempts_on_an_all_thin_feed(tmp_path, monkeypatch):
    """A feed where every headline is unsourceable must not retry forever --
    bounded at max(n*3, 3) attempts."""
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    monkeypatch.setattr(nc, "STATE_PATH", str(tmp_path / "news-state.json"))
    monkeypatch.setenv("NEWS_REPORTER_PICKS", "1")
    with open(nc.FEED_PATH, "w") as f:
        json.dump({"headlines": [
            {"title": f"Thin {i}", "url": f"https://a.example/{i}", "topic": "base"} for i in range(5)
        ]}, f)

    with mock.patch.object(news_reporter, "write_story", return_value=None) as ws:
        written = news_reporter.run()

    assert written == []
    assert ws.call_count == 3


# ── multi-source depth on every story (explicit direction, 2026-08-01, after
#    a real user report on a thin single-source rewrite of a major story --
#    and a same-day correction that this is how every VAPE Wire article gets
#    written, not a special tier for security/large-dollar stories) ────────

def test_gather_corroboration_runs_three_queries_and_dedupes_for_security_topic():
    calls = []

    def fake_search(query, max_results=5):
        calls.append(query)
        # The same URL comes back from every query -- must be deduped once,
        # not duplicated per query, while each query's unique hit survives.
        return {"available": True, "provider": "tavily",
                "results": [{"title": "Shared hit", "url": "https://shared.example/1", "snippet": "s"},
                            {"title": f"Unique {len(calls)}", "url": f"https://unique.example/{len(calls)}",
                             "snippet": "s"}]}

    candidate = {"title": "Coldcard firmware flaw drains $70M", "topic": "defi-security"}
    with mock.patch("agents.intel_common.web_search_snippets", side_effect=fake_search):
        out = news_reporter._gather_corroboration(candidate)
    # Original headline + "explained analysis" + the security-beat root-cause query.
    assert calls == [
        "Coldcard firmware flaw drains $70M",
        "Coldcard firmware flaw drains $70M explained analysis",
        "Coldcard firmware flaw drains $70M technical root cause",
    ]
    shared_hits = [r for r in out["results"] if r["url"] == "https://shared.example/1"]
    assert len(shared_hits) == 1
    assert len(out["results"]) == 4  # 1 shared + 3 query-unique hits


def test_gather_corroboration_uses_fact_check_query_for_non_security_topic():
    """Every story gets the same three-query depth -- the third query is
    just topic-aware: a fact-check angle for anything outside the security
    beat, since a market-commentary story fact-checking another outlet's
    unsupported claim needs real cross-referencing aimed at the claim
    itself, not a technical mechanism."""
    calls = []

    def fake_search(query, max_results=5):
        calls.append(query)
        return {"available": True, "provider": "tavily", "results": []}

    candidate = {"title": "Bitcoin Foundation says XRP lags the market", "topic": "crypto-markets"}
    with mock.patch("agents.intel_common.web_search_snippets", side_effect=fake_search):
        news_reporter._gather_corroboration(candidate)
    assert calls == [
        "Bitcoin Foundation says XRP lags the market",
        "Bitcoin Foundation says XRP lags the market explained analysis",
        "Bitcoin Foundation says XRP lags the market fact check",
    ]


def test_scrape_multiple_sources_collects_real_bodies_and_skips_failures():
    bodies = {"https://a.example/1": "Body A", "https://c.example/3": "Body C"}

    with mock.patch.object(nc, "scrape_article_text", side_effect=lambda url, max_len=3000: bodies.get(url)):
        scraped = news_reporter._scrape_multiple_sources(
            "https://a.example/1", [{"url": "https://b.example/2"}, {"url": "https://c.example/3"}], max_sources=3)
    assert [u for u, _ in scraped] == ["https://a.example/1", "https://c.example/3"]  # b skipped, no body


def test_scrape_multiple_sources_respects_max_sources_cap():
    with mock.patch.object(nc, "scrape_article_text", side_effect=lambda url, max_len=3000: f"Body for {url}"):
        scraped = news_reporter._scrape_multiple_sources(
            "https://primary.example", [{"url": f"https://x.example/{i}"} for i in range(5)], max_sources=2)
    assert len(scraped) == 2


def test_write_story_builds_multi_source_grounding_with_larger_budget_for_security_story(tmp_path, monkeypatch):
    """A security-beat story (the real user-reported gap: a thin
    single-source rewrite of a major story) gets the full multi-source
    treatment: multiple search queries, multiple scraped source bodies
    presented as separate labeled blocks, a larger drafting/editorial token
    budget, and a Fact-checked field that says so."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Coldcard firmware flaw drains $70 million from cold wallets",
                 "url": "https://example.com/primary", "source": "The Block",
                 "published": "2026-07-31T00:00:00Z", "topic": "defi-security"}

    search_calls = []

    def fake_search(query, max_results=5):
        search_calls.append((query, max_results))
        return {"available": True, "provider": "tavily",
                "results": [{"title": "Galaxy Research mapping", "url": "https://example.com/galaxy",
                             "snippet": "1,082.65 BTC from 1,196 addresses"},
                            {"title": "Block engineering post", "url": "https://example.com/block",
                             "snippet": "RNG fallback root cause"}]}

    def fake_scrape(url, max_len=3000):
        return {
            "https://example.com/primary": "Primary source body text about the theft.",
            "https://example.com/galaxy": "Galaxy Research's full on-chain mapping body text.",
            "https://example.com/block": "Block's engineering root-cause analysis body text.",
        }.get(url)

    captured = {}

    def fake_synthesize(result, **kw):
        captured["grounding"] = result["raw_user_block"]
        captured["max_tokens"] = kw.get("max_tokens")
        return _synth("The Entropy Mirage", "A five-year-old flaw let attackers reconstruct keys offline.",
                      "## What Happened\nBody text.")

    editor_calls = []

    def fake_editor(role, grounding, instructions=None, max_tokens=2400, temperature=0.55, search=False):
        editor_calls.append({"instructions": instructions, "max_tokens": max_tokens})
        return "## What Happened\nEdited body text."

    with mock.patch("agents.intel_common.web_search_snippets", side_effect=fake_search), \
         mock.patch.object(nc, "scrape_article_text", side_effect=fake_scrape), \
         mock.patch.object(news_reporter, "_generate_ai_image", return_value=None), \
         mock.patch("agents.research_engine.synthesize", side_effect=fake_synthesize), \
         mock.patch("agents.intel_common.grok_analysis", side_effect=fake_editor), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        path = news_reporter.write_story(candidate)

    assert path is not None
    text = open(path).read()
    assert "The Entropy Mirage" in text
    assert "Fact-checked:** Yes — multi-source review completed" in text

    # Multiple search queries actually ran.
    assert len(search_calls) == 3

    # Multiple real source bodies were scraped and presented as separate,
    # labeled blocks the model can cross-check and attribute figures against.
    grounding = captured["grounding"]
    assert "Scraped article bodies from 3 independent sources" in grounding
    assert "Primary source body text about the theft." in grounding
    assert "Galaxy Research's full on-chain mapping body text." in grounding
    assert "Block's engineering root-cause analysis body text." in grounding

    # Larger drafting/editorial token budgets for a genuinely deeper piece.
    assert captured["max_tokens"] == 3600
    assert editor_calls[0]["max_tokens"] == 3200
    assert "numeric precision" in editor_calls[0]["instructions"]


def test_write_story_gives_the_same_multi_source_depth_to_a_routine_market_story(tmp_path, monkeypatch):
    """The explicit correction this codebase now enforces: multi-source
    depth is not a special tier for security/large-dollar stories, it's how
    every VAPE Wire article gets written -- confirmed here with an ordinary
    crypto-markets story that would have been the old single-query,
    lower-budget path."""
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "Crypto markets rally", "url": "https://example.com/story",
                 "source": "CoinDesk", "published": "2026-07-27T09:00:00Z", "topic": "crypto-markets",
                 "snippet": "A real outlet-provided summary of the rally."}

    search_calls = []

    def fake_search(query, max_results=5):
        search_calls.append((query, max_results))
        return {"available": True, "provider": "tavily", "results": []}

    captured = {}

    def fake_synthesize(result, **kw):
        captured["max_tokens"] = kw.get("max_tokens")
        return _synth("Rally Deepens", "Momentum builds.", "Body text.")

    editor_calls = []

    def fake_editor(role, grounding, instructions=None, max_tokens=2400, temperature=0.55, search=False):
        editor_calls.append(max_tokens)
        return "Body text."

    with mock.patch("agents.intel_common.web_search_snippets", side_effect=fake_search), \
         mock.patch.object(nc, "scrape_article_text", return_value=None), \
         mock.patch.object(news_reporter, "_generate_ai_image", return_value=None), \
         mock.patch("agents.research_engine.synthesize", side_effect=fake_synthesize), \
         mock.patch("agents.intel_common.grok_analysis", side_effect=fake_editor), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        path = news_reporter.write_story(candidate)

    assert path is not None
    text = open(path).read()
    assert "Fact-checked:** Yes — multi-source review completed" in text
    assert len(search_calls) == 3
    assert search_calls[-1][0] == "Crypto markets rally fact check"
    assert captured["max_tokens"] == 3600
    assert editor_calls[0] == 3200
