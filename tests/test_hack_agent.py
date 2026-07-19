"""Tests for agents/hack_agent.py — the per-incident threat-analysis writer
that patches data/attack-feed.json with a real analysis_report path per
incident. Hermetic: agents.llm.ask_oci_grok_safe and
agents.intel_common.web_search_snippets are mocked, no real network call;
all paths (ATTACK_FEED_PATH/STATE_PATH/ANALYSIS_DIR) are monkeypatched to
tmp_path so nothing touches the real repo state.
"""
import json
import os
from unittest import mock

from agents import hack_agent


def _incident(name="Across", date="2026-07-17", amount=1.5, technique="Bridge exploit",
               chains=None, lesson=None):
    h = {"date": date, "name": name, "amount_usd_m": amount,
         "technique": technique, "chains": chains or ["Solana"]}
    if lesson:
        h["lesson"] = lesson
    return h


def test_incident_id_matches_security_sweep_convention():
    h = _incident(name="Foo Bridge", date="2026-07-01")
    assert hack_agent._incident_id(h) == "2026-07-01:Foo Bridge"


def test_slug_lowercases_and_strips_punctuation():
    assert hack_agent._slug("Across Protocol!") == "across-protocol"
    assert hack_agent._slug("") == "incident"
    assert hack_agent._slug(None) == "incident"


def test_grounding_includes_real_fields_only():
    h = _incident(name="Foo", technique="Reentrancy", chains=["Base", "Ethereum"])
    text = hack_agent._grounding(h)
    assert "Foo" in text and "Reentrancy" in text and "Base, Ethereum" in text
    assert "prevention" not in text.lower()  # no lesson given — must not fabricate one


def test_grounding_includes_lesson_when_present():
    h = _incident(lesson={"label": "Oracle manipulation", "prevention": "Use TWAP oracles"})
    text = hack_agent._grounding(h)
    assert "Oracle manipulation" in text
    assert "Use TWAP oracles" in text


def test_state_round_trips(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(hack_agent, "STATE_PATH", str(state_path))
    assert hack_agent._load_state() == {}
    hack_agent._save_state({"2026-07-01:Foo": {"report": "intel/threat-analysis/x.md"}})
    assert hack_agent._load_state() == {"2026-07-01:Foo": {"report": "intel/threat-analysis/x.md"}}


class TestWriteAnalysis:
    def test_returns_none_when_llm_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe",
                             return_value=("[llm unavailable: no keys]", None)):
                report, provider = hack_agent._write_analysis(_incident())
        assert report is None and provider is None
        assert not os.listdir(tmp_path)  # nothing written on failure

    def test_writes_real_file_with_header_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe",
                             return_value=("Real analysis text.", "oci_grok")):
                report, provider = hack_agent._write_analysis(_incident(name="Across", date="2026-07-17"))
        assert provider == "oci_grok"
        assert report.endswith("2026-07-17-across.md")
        full_path = os.path.join(hack_agent.ic.ROOT, report)
        content = open(full_path).read()
        assert "# Across — Threat Analysis" in content
        assert "**Analysis by:** oci_grok" in content
        assert "Real analysis text." in content

    def test_passes_frontier_order_and_tier_to_oci_grok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        from agents.llm import FRONTIER_ORDER
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe",
                             return_value=("text", "oci_grok")) as m:
                hack_agent._write_analysis(_incident())
        _, kwargs = m.call_args
        assert kwargs["tier"] == "frontier"
        assert kwargs["provider_order"] == FRONTIER_ORDER


class TestRun:
    def _setup(self, tmp_path, monkeypatch, incidents):
        feed_path = tmp_path / "attack-feed.json"
        state_path = tmp_path / "state.json"
        analysis_dir = tmp_path / "analysis"
        feed_path.write_text(json.dumps({
            "generated_at": "2026-07-19T00:00:00Z", "source_report": "intel/reports/x.md",
            "threat_level": "LOW", "lookback_days": 56, "incidents": incidents,
        }))
        monkeypatch.setattr(hack_agent, "ATTACK_FEED_PATH", str(feed_path))
        monkeypatch.setattr(hack_agent, "STATE_PATH", str(state_path))
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(analysis_dir))
        return feed_path, state_path

    def test_no_feed_file_is_a_safe_noop(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ATTACK_FEED_PATH", str(tmp_path / "missing.json"))
        result = hack_agent.run()
        assert result == {"analyzed": 0, "patched": 0}

    def test_every_incident_gets_analyzed_and_patched_onto_feed(self, tmp_path, monkeypatch):
        incidents = [_incident(name="Foo", date="2026-07-01"), _incident(name="Bar", date="2026-07-02")]
        feed_path, _ = self._setup(tmp_path, monkeypatch, incidents)
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("analysis", "oci_grok")):
                result = hack_agent.run()
        assert result == {"analyzed": 2, "patched": 0}
        feed = json.loads(feed_path.read_text())
        assert all("analysis_report" in h for h in feed["incidents"])

    def test_already_analyzed_incident_is_patched_not_reanalyzed(self, tmp_path, monkeypatch):
        incidents = [_incident(name="Foo", date="2026-07-01")]
        feed_path, _ = self._setup(tmp_path, monkeypatch, incidents)
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("analysis", "oci_grok")) as m:
                hack_agent.run()  # first run: writes it
                result = hack_agent.run()  # second run: should just patch
        assert m.call_count == 1  # only ever called once across both runs
        assert result == {"analyzed": 0, "patched": 1}

    def test_max_analyses_per_run_caps_a_large_backlog(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "MAX_ANALYSES_PER_RUN", 2)
        incidents = [_incident(name=f"Foo{i}", date="2026-07-01") for i in range(5)]
        self._setup(tmp_path, monkeypatch, incidents)
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("analysis", "oci_grok")) as m:
                result = hack_agent.run()
        assert result == {"analyzed": 2, "patched": 0}
        assert m.call_count == 2

    def test_missing_report_file_triggers_reanalysis(self, tmp_path, monkeypatch):
        """If the analysis file was somehow deleted but state still points to
        it, the next run must self-heal by re-analyzing rather than silently
        patching a dead link onto the feed forever."""
        incidents = [_incident(name="Foo", date="2026-07-01")]
        feed_path, state_path = self._setup(tmp_path, monkeypatch, incidents)
        state_path.write_text(json.dumps({
            "2026-07-01:Foo": {"report": "intel/threat-analysis/does-not-exist.md", "provider": "oci_grok"}
        }))
        with mock.patch("agents.intel_common.web_search_snippets",
                        return_value={"available": False, "provider": None, "results": []}):
            with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("analysis", "oci_grok")) as m:
                result = hack_agent.run()
        assert m.call_count == 1
        assert result == {"analyzed": 1, "patched": 0}
