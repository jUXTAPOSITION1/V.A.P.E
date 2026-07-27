"""Tests for agents/news_reporter.py — candidate picking, the reporter/editor
two-pass pipeline, and honest degradation when the editorial pass can't run.
Hermetic: every LLM/web-search/network call is mocked, no real network or
git-tracked file writes (write_news_report is redirected into tmp_path).
"""
import json
from unittest import mock

from agents import news_common as nc
from agents import news_reporter


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


def test_parse_llm_output_extracts_headline_dek_body():
    raw = "HEADLINE: Base Hits Record TVL\nDEK: A milestone day for the L2.\n---\n## Body\nReal content here."
    headline, dek, body = news_reporter._parse_llm_output(raw, "fallback")
    assert headline == "Base Hits Record TVL"
    assert dek == "A milestone day for the L2."
    assert body == "## Body\nReal content here."


def test_parse_llm_output_falls_back_on_malformed_response():
    headline, dek, body = news_reporter._parse_llm_output("just plain prose, no markers", "Original Title")
    assert headline == "Original Title"
    assert dek == ""
    assert body == "just plain prose, no markers"


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


def test_write_story_marks_fact_checked_and_includes_sources(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "NEWS_DIR", str(tmp_path))
    candidate = {"title": "DeFi protocol patches bug", "url": "https://example.com/story",
                 "source": "The Block", "published": "2026-07-27T09:00:00Z", "topic": "defi-security"}

    with mock.patch("agents.intel_common.web_search_snippets",
                     return_value={"available": True, "provider": "tavily",
                                   "results": [{"title": "Corroborating piece", "url": "https://example.com/corr",
                                                "snippet": "confirms the patch"}]}), \
         mock.patch.object(nc, "extract_og_image", return_value=None), \
         mock.patch("agents.intel_common.grok_analysis",
                     side_effect=["HEADLINE: The Patch That Saved Millions\nDEK: A close call.\n---\n## Details\nBody text.",
                                  "## Details\nEdited body text."]), \
         mock.patch("agents.intel_common.log_sweep_memory", return_value=None):
        path = news_reporter.write_story(candidate)

    text = open(path).read()
    assert "The Patch That Saved Millions" in text
    assert "Fact-checked:** Yes" in text
    assert "Edited body text." in text
    assert "Corroborating piece" in text
    assert "**Agency:** VAPE Wire" in text
