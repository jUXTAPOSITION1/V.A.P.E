"""Tests for agents/scout.py's Grok strategic briefing (runs every cycle
with anything to assess — no longer gated on new_entries, by explicit
direction: coverage over conserving Grok's one-time credit) and the real
action step (_act_on_base_incidents). Hermetic: agents.llm.ask_safe and the
security_sweep/data_fetchers delegation are mocked, no real network call.
"""
from unittest import mock

from agents import scout
from agents.llm import FRONTIER_ORDER


def _entry(name, fit=80, prize=1_000_000, platform="defillama-hack"):
    return {"name": name, "fitScore": fit, "prizeUsd": prize, "platform": platform,
            "status": "incident", "tags": ["forensics"], "desc": f"{name} exploit"}


def test_empty_shown_list_skips_llm_entirely():
    with mock.patch("agents.llm.ask_safe") as m:
        result = scout._grok_briefing([_entry("New One")], [])
    assert result == ""
    m.assert_not_called()


def test_no_new_entries_still_assesses_the_shown_set():
    # The whole point of the fix: an unchanged top-fit set must still get
    # assessed, not silently skipped just because nothing is new.
    with mock.patch("agents.llm.ask_safe", return_value=("Nothing new, still worth watching X.", "xai_1")) as m:
        result = scout._grok_briefing([], [_entry("Old One")])
    assert result == "Nothing new, still worth watching X."
    m.assert_called_once()


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


# ── _act_on_base_incidents() — the real action step ─────────────────────────

def test_act_on_base_incidents_delegates_to_security_sweep(monkeypatch):
    fake_incidents = [{"name": "Bridge Hack", "date": "2026-07-01", "chains": ["Base"],
                        "amount_usd_m": 1.0, "technique": "reentrancy"}]
    monkeypatch.setattr("agents.data_fetchers.get_hack_feed",
                        lambda limit=150: {"incidents": fake_incidents})
    called = {}

    def fake_forensics(incidents):
        called["incidents"] = incidents
        return [{"incident": "2026-07-01:Bridge Hack", "resolved": True, "address": "0x" + "aa" * 20}]

    monkeypatch.setattr("agents.security_sweep.attempt_incident_forensics", fake_forensics)
    result = scout._act_on_base_incidents()
    assert called["incidents"] == fake_incidents
    assert result[0]["resolved"] is True


def test_act_on_base_incidents_handles_missing_deps(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def fail_import(name, *a, **kw):
        if name == "agents.security_sweep":
            raise ImportError("no security_sweep")
        return real_import(name, *a, **kw)

    with mock.patch("builtins.__import__", side_effect=fail_import):
        result = scout._act_on_base_incidents()
    assert result == []


def test_act_on_base_incidents_swallows_runtime_errors(monkeypatch):
    monkeypatch.setattr("agents.data_fetchers.get_hack_feed",
                        lambda limit=150: {"incidents": []})
    monkeypatch.setattr("agents.security_sweep.attempt_incident_forensics",
                        mock.Mock(side_effect=RuntimeError("boom")))
    result = scout._act_on_base_incidents()
    assert result == []


def test_write_digest_shows_resolved_action(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "INTEL_DIR", str(tmp_path))
    entries = [_entry("Bridge Hack", fit=90)]
    outcomes = [{"incident": "2026-07-01:Bridge Hack", "resolved": True, "address": "0x" + "aa" * 20}]
    with mock.patch.object(scout, "_grok_briefing", return_value=""):
        path = scout._write_digest(entries, 0, 1, [], outcomes)
    content = open(path).read()
    assert "## Actions Taken This Cycle" in content
    assert "0x" + "aa" * 20 in content
    assert "real investigation launched" in content


def test_write_digest_shows_unresolved_action(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "INTEL_DIR", str(tmp_path))
    entries = [_entry("Bridge Hack", fit=90)]
    outcomes = [{"incident": "2026-07-01:Bridge Hack", "resolved": False}]
    with mock.patch.object(scout, "_grok_briefing", return_value=""):
        path = scout._write_digest(entries, 0, 1, [], outcomes)
    content = open(path).read()
    assert "## Actions Taken This Cycle" in content
    assert "could not verify a real address" in content


def test_write_digest_omits_actions_section_when_none(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "INTEL_DIR", str(tmp_path))
    entries = [_entry("Bridge Hack", fit=90)]
    with mock.patch.object(scout, "_grok_briefing", return_value=""):
        path = scout._write_digest(entries, 0, 1, [], [])
    content = open(path).read()
    assert "Actions Taken This Cycle" not in content
