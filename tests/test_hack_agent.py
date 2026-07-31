"""Tests for agents/hack_agent.py — the per-incident threat-analysis writer
that patches data/attack-feed.json with a real analysis_report path per
incident. Hermetic: agents.research_engine.layered_research/synthesize/
review_output/log_review_finding are mocked at the module boundary (no real
network call, no real LLM call — research_engine's own internals are
covered by tests/test_research_engine.py); all paths (ATTACK_FEED_PATH/
STATE_PATH/ANALYSIS_DIR) are monkeypatched to tmp_path so nothing touches
the real repo state.
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


def test_safe_date_passes_through_a_real_iso_date_unchanged():
    assert hack_agent._safe_date("2026-07-17") == "2026-07-17"


def test_safe_date_strips_path_traversal_segments():
    # Real gap CodeRabbit flagged on PR #372: _slug() sanitized h['name']
    # right next to h['date'], which was spliced in raw — a '/' or '..'
    # here used to be able to escape ANALYSIS_DIR when joined into a path.
    assert "/" not in hack_agent._safe_date("../../etc/passwd")
    assert ".." not in hack_agent._safe_date("../../etc/passwd")
    assert hack_agent._safe_date("2026/07-17") == "2026-07-17"


def test_safe_date_empty_or_none_falls_back():
    assert hack_agent._safe_date("") == "unknown-date"
    assert hack_agent._safe_date(None) == "unknown-date"


def test_grounding_includes_real_fields_only():
    h = _incident(name="Foo", technique="Reentrancy", chains=["Base", "Ethereum"])
    facts = hack_agent._grounding(h)
    assert facts["protocol"] == "Foo"
    assert facts["technique"] == "Reentrancy"
    assert facts["chains"] == "Base, Ethereum"
    assert "known_prevention_measure" not in facts  # no lesson given — must not fabricate one


def test_grounding_includes_lesson_when_present():
    h = _incident(lesson={"label": "Oracle manipulation", "prevention": "Use TWAP oracles"})
    facts = hack_agent._grounding(h)
    assert facts["technique_classification_vape"] == "Oracle manipulation"
    assert facts["known_prevention_measure"] == "Use TWAP oracles"


def test_state_round_trips(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(hack_agent, "STATE_PATH", str(state_path))
    assert hack_agent._load_state() == {}
    hack_agent._save_state({"2026-07-01:Foo": {"report": "intel/threat-analysis/x.md"}})
    assert hack_agent._load_state() == {"2026-07-01:Foo": {"report": "intel/threat-analysis/x.md"}}


def _fake_result(task_type="threat_analysis"):
    return {"topic": "x", "task_type": task_type, "known_facts": {}, "findings": [],
            "deep_extracts": [], "log": {"queries": [], "unique_sources_found": 0}}


class TestWriteAnalysis:
    def test_returns_none_when_synthesis_unavailable(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "_Synthesis unavailable this cycle (LLM call failed)._",
                                           "gaps": [], "provider": None}):
                report, provider = hack_agent._write_analysis(_incident())
        assert report is None and provider is None
        assert not os.listdir(tmp_path)  # nothing written on failure

    def test_writes_real_file_with_header_gaps_and_methodology_on_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        fake_synth = {"narrative": "## Known Facts\nReal analysis text.",
                      "gaps": [{"description": "attacker identity unconfirmed", "confidence": 0.4,
                                "next_action": "monitor on-chain flow"}],
                      "provider": "oci_grok"}
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize", return_value=fake_synth):
                with mock.patch("agents.research_engine.review_output",
                                 return_value={"ok": True, "issues": []}) as mock_review:
                    report, provider = hack_agent._write_analysis(_incident(name="Across", date="2026-07-17"))
        assert provider == "oci_grok"
        assert report.endswith("2026-07-17-across.md")
        full_path = os.path.join(hack_agent.ic.ROOT, report)
        content = open(full_path).read()
        assert "# Across — Threat Analysis" in content
        assert "**Analysis by:** VAPE" in content  # attribution is always VAPE, never the raw provider codename
        assert "Real analysis text." in content
        assert "## Gaps & Confidence" in content
        assert "attacker identity unconfirmed" in content
        assert "## Research Methodology and Sources" in content
        mock_review.assert_called_once()

    def test_malicious_date_cannot_escape_analysis_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        fake_synth = {"narrative": "text", "gaps": [], "provider": "oci_grok"}
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize", return_value=fake_synth):
                with mock.patch("agents.research_engine.review_output", return_value={"ok": True, "issues": []}):
                    report, _ = hack_agent._write_analysis(_incident(name="Foo", date="../../etc/passwd"))
        full_path = os.path.join(hack_agent.ic.ROOT, report)
        assert os.path.commonpath([os.path.abspath(full_path), str(tmp_path)]) == str(tmp_path)

    def test_uses_threat_analysis_task_type_and_real_known_facts(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        captured = {}

        def fake_layered(topic, task_type=None, known_facts=None, **kw):
            captured["topic"] = topic
            captured["task_type"] = task_type
            captured["known_facts"] = known_facts
            return _fake_result(task_type)

        with mock.patch("agents.research_engine.layered_research", side_effect=fake_layered):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "text", "gaps": [], "provider": "oci_grok"}):
                with mock.patch("agents.research_engine.log_review_finding"):
                    hack_agent._write_analysis(_incident(name="Foo", technique="Reentrancy", chains=["Base"]))
        assert captured["task_type"] == "threat_analysis"
        assert captured["known_facts"]["protocol"] == "Foo"
        assert captured["known_facts"]["technique"] == "Reentrancy"

    def test_logs_review_finding_when_review_flags_issues(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "text", "gaps": [], "provider": "oci_grok"}):
                with mock.patch("agents.research_engine.review_output",
                                 return_value={"ok": False, "issues": ["missing expected section: Timeline"]}):
                    with mock.patch("agents.research_engine.log_review_finding") as mock_log:
                        hack_agent._write_analysis(_incident())
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[1] == "threat_analysis"
        assert args[2] == ["missing expected section: Timeline"]

    def test_does_not_log_review_finding_when_review_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "ANALYSIS_DIR", str(tmp_path))
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "text", "gaps": [], "provider": "oci_grok"}):
                with mock.patch("agents.research_engine.review_output",
                                 return_value={"ok": True, "issues": []}):
                    with mock.patch("agents.research_engine.log_review_finding") as mock_log:
                        hack_agent._write_analysis(_incident())
        mock_log.assert_not_called()


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
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "analysis", "gaps": [], "provider": "oci_grok"}):
                with mock.patch("agents.research_engine.log_review_finding"):
                    result = hack_agent.run()
        assert result == {"analyzed": 2, "patched": 0}
        feed = json.loads(feed_path.read_text())
        assert all("analysis_report" in h for h in feed["incidents"])

    def test_already_analyzed_incident_is_patched_not_reanalyzed(self, tmp_path, monkeypatch):
        incidents = [_incident(name="Foo", date="2026-07-01")]
        self._setup(tmp_path, monkeypatch, incidents)
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "analysis", "gaps": [], "provider": "oci_grok"}) as m:
                with mock.patch("agents.research_engine.log_review_finding"):
                    hack_agent.run()  # first run: writes it
                    result = hack_agent.run()  # second run: should just patch
        assert m.call_count == 1  # only ever called once across both runs
        assert result == {"analyzed": 0, "patched": 1}

    def test_max_analyses_per_run_caps_a_large_backlog(self, tmp_path, monkeypatch):
        monkeypatch.setattr(hack_agent, "MAX_ANALYSES_PER_RUN", 2)
        incidents = [_incident(name=f"Foo{i}", date="2026-07-01") for i in range(5)]
        self._setup(tmp_path, monkeypatch, incidents)
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "analysis", "gaps": [], "provider": "oci_grok"}) as m:
                with mock.patch("agents.research_engine.log_review_finding"):
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
        with mock.patch("agents.research_engine.layered_research", return_value=_fake_result()):
            with mock.patch("agents.research_engine.synthesize",
                             return_value={"narrative": "analysis", "gaps": [], "provider": "oci_grok"}) as m:
                with mock.patch("agents.research_engine.log_review_finding"):
                    result = hack_agent.run()
        assert m.call_count == 1
        assert result == {"analyzed": 1, "patched": 0}
