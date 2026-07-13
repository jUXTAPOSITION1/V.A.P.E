"""Tests for agents/scout.py's Grok strategic briefing — gating (only calls
Grok when something genuinely new appeared, to stay inside its free/one-time
credit) and graceful degradation. Hermetic: agents.llm.ask_safe is mocked,
no real network/API call.
"""
from unittest import mock

from agents import scout
from agents.llm import FRONTIER_ORDER


def _entry(name, fit=80, prize=1_000_000, platform="defillama-hack"):
    return {"name": name, "fitScore": fit, "prizeUsd": prize, "platform": platform,
            "status": "incident", "tags": ["forensics"], "desc": f"{name} exploit"}


def test_no_new_entries_skips_llm_entirely():
    with mock.patch("agents.llm.ask_safe") as m:
        result = scout._grok_briefing([], [_entry("Old One")])
    assert result == ""
    m.assert_not_called()


def test_empty_shown_list_skips_llm_entirely():
    with mock.patch("agents.llm.ask_safe") as m:
        result = scout._grok_briefing([_entry("New One")], [])
    assert result == ""
    m.assert_not_called()


def test_llm_unavailable_returns_empty_string():
    with mock.patch("agents.llm.ask_safe", return_value=("[llm unavailable: no keys]", None)):
        result = scout._grok_briefing([_entry("New One")], [_entry("New One")])
    assert result == ""


def test_successful_briefing_is_returned_and_uses_frontier_tier():
    with mock.patch("agents.llm.ask_safe", return_value=("Prioritize the bridge exploit.", "xai_1")) as m:
        result = scout._grok_briefing([_entry("Bridge Hack")], [_entry("Bridge Hack")])
    assert result == "Prioritize the bridge exploit."
    _, kwargs = m.call_args
    assert kwargs["tier"] == "frontier"
    assert kwargs["provider_order"] == FRONTIER_ORDER


def test_briefing_exception_is_swallowed():
    with mock.patch("agents.llm.ask_safe", side_effect=RuntimeError("boom")):
        result = scout._grok_briefing([_entry("New One")], [_entry("New One")])
    assert result == ""


def test_write_digest_includes_briefing_section_when_present(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "INTEL_DIR", str(tmp_path))
    entries = [_entry("Bridge Hack", fit=90)]
    with mock.patch.object(scout, "_grok_briefing", return_value="Go after the bridge first."):
        path = scout._write_digest(entries, 1, 1, entries)
    content = open(path).read()
    assert "## Strategic Briefing (Grok)" in content
    assert "Go after the bridge first." in content


def test_write_digest_omits_briefing_section_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "INTEL_DIR", str(tmp_path))
    entries = [_entry("Bridge Hack", fit=90)]
    with mock.patch.object(scout, "_grok_briefing", return_value=""):
        path = scout._write_digest(entries, 0, 1, [])
    content = open(path).read()
    assert "Strategic Briefing" not in content
