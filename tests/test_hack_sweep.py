"""Tests for agents/hack_sweep.py — the daily proactive escalation pipeline
from investigate.py's ledger (CAUTION verdicts) to deep_dive_audit.py's full
tool suite. Hermetic: investigate.py's ledger and deep_dive_audit.run_audit
are both mocked/monkeypatched, no real network call, no real subprocess.
"""
import json
from unittest import mock

from agents import hack_sweep


def _entry(address, verdict="CAUTION", chain="8453", symbol="TOK"):
    return {"address": address, "chain": chain, "symbol": symbol, "last_verdict": verdict}


def test_select_candidates_filters_to_caution_only(monkeypatch, tmp_path):
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(tmp_path / "state.json"))
    ledger = {
        "8453:0xaaa": _entry("0xaaa", verdict="CAUTION"),
        "8453:0xbbb": _entry("0xbbb", verdict="REJECT"),
        "8453:0xccc": _entry("0xccc", verdict="PROCEED"),
    }
    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger):
        candidates = hack_sweep._select_candidates(limit=5)
    assert len(candidates) == 1
    assert candidates[0][2] == "0xaaa"


def test_select_candidates_skips_entries_without_address(monkeypatch, tmp_path):
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(tmp_path / "state.json"))
    ledger = {"8453:bad": {"last_verdict": "CAUTION", "chain": "8453"}}
    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger):
        candidates = hack_sweep._select_candidates(limit=5)
    assert candidates == []


def test_select_candidates_prefers_never_swept_then_oldest(monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps({"8453:0xold": "2026-01-01T00:00:00+00:00"}))
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(state_path))
    ledger = {
        "8453:0xold": _entry("0xold"),
        "8453:0xnew": _entry("0xnew"),
    }
    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger):
        candidates = hack_sweep._select_candidates(limit=5)
    # never-swept ("") sorts before the old timestamp string
    assert [c[2] for c in candidates] == ["0xnew", "0xold"]


def test_select_candidates_respects_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(tmp_path / "state.json"))
    ledger = {f"8453:0x{i}": _entry(f"0x{i}") for i in range(10)}
    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger):
        candidates = hack_sweep._select_candidates(limit=3)
    assert len(candidates) == 3


def test_run_no_candidates_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(tmp_path / "state.json"))
    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value={}):
        result = hack_sweep.run()
    assert result == []


def test_run_deep_dives_selected_candidates_and_updates_state(monkeypatch, tmp_path):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(state_path))
    findings_path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(hack_sweep, "FINDINGS_PATH", str(findings_path))
    ledger = {"8453:0xaaa": _entry("0xaaa", symbol="TOK")}

    def fake_run_audit(address, chain, engagement=None):
        assert engagement == "sweep"
        return {"address": address, "chain": chain, "symbol": "TOK", "verdict": "CAUTION",
                "score": 55, "report": "intel/audits/hack-sweep-reports/x.md", "provider": "oci_grok",
                "engagement": "sweep"}

    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger), \
         mock.patch.object(hack_sweep.dda, "run_audit", side_effect=fake_run_audit):
        results = hack_sweep.run()

    assert len(results) == 1
    assert results[0]["address"] == "0xaaa"
    state = json.loads(state_path.read_text())
    assert "8453:0xaaa" in state
    findings = [json.loads(l) for l in findings_path.read_text().splitlines()]
    assert len(findings) == 1
    assert "0xaaa" in findings[0]["content"]
    assert findings[0]["source"] == "agents/hack_sweep.py"


def test_run_skips_candidate_on_error_result(monkeypatch, tmp_path):
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(hack_sweep, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    ledger = {"8453:0xaaa": _entry("0xaaa")}

    def fake_run_audit(address, chain, engagement=None):
        return {"error": "invalid address"}

    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger), \
         mock.patch.object(hack_sweep.dda, "run_audit", side_effect=fake_run_audit):
        results = hack_sweep.run()
    assert results == []


def test_run_swallows_run_audit_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(hack_sweep, "STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(hack_sweep, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    ledger = {"8453:0xaaa": _entry("0xaaa")}

    with mock.patch.object(hack_sweep.inv, "_load_ledger", return_value=ledger), \
         mock.patch.object(hack_sweep.dda, "run_audit", side_effect=RuntimeError("boom")):
        results = hack_sweep.run()
    assert results == []
