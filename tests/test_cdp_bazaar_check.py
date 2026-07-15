"""Tests for agents/cdp_bazaar_check.py's state-change detection logic.
Hermetic: agents.cdp_bazaar_check._fetch_status is mocked (no real network
call to the worker or CDP); state/findings files are redirected to a tmp
path so nothing touches the real skillforge/memory/ files.
"""
import json
from unittest import mock

from agents import cdp_bazaar_check as C


def _run(status, monkeypatch, tmp_path, prior_state=None):
    state_path = tmp_path / "state.json"
    findings_path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(C, "STATE_PATH", str(state_path))
    monkeypatch.setattr(C, "FINDINGS_PATH", str(findings_path))
    if prior_state is not None:
        state_path.write_text(json.dumps(prior_state))
    with mock.patch.object(C, "_fetch_status", return_value=status):
        C.main()
    findings = [json.loads(l) for l in findings_path.read_text().splitlines()] if findings_path.exists() else []
    state = json.loads(state_path.read_text()) if state_path.exists() else None
    return findings, state


def test_first_run_logs_a_baseline_finding(tmp_path, monkeypatch):
    status = {"cdp_reachable": True, "indexed_count": 0, "total_offerings": 20, "missing": ["a", "b"]}
    findings, state = _run(status, monkeypatch, tmp_path)
    assert len(findings) == 1
    assert "baseline" in findings[0]["title"].lower()
    assert state == {"indexed_count": 0, "total": 20, "checked_at": mock.ANY}


def test_unchanged_count_logs_nothing(tmp_path, monkeypatch):
    prior = {"indexed_count": 5, "total": 20, "checked_at": "2026-07-01T00:00:00+00:00"}
    status = {"cdp_reachable": True, "indexed_count": 5, "total_offerings": 20, "missing": []}
    findings, state = _run(status, monkeypatch, tmp_path, prior_state=prior)
    assert findings == []
    # State file untouched (still the prior one) since nothing changed.
    assert state == prior


def test_indexed_count_increase_logs_a_finding(tmp_path, monkeypatch):
    prior = {"indexed_count": 0, "total": 20, "checked_at": "2026-07-01T00:00:00+00:00"}
    status = {"cdp_reachable": True, "indexed_count": 3, "total_offerings": 20, "missing": []}
    findings, state = _run(status, monkeypatch, tmp_path, prior_state=prior)
    assert len(findings) == 1
    assert "0 -> 3" in findings[0]["title"]
    assert "Improvement" in findings[0]["content"]
    assert state["indexed_count"] == 3


def test_indexed_count_regression_logs_a_finding(tmp_path, monkeypatch):
    prior = {"indexed_count": 3, "total": 20, "checked_at": "2026-07-01T00:00:00+00:00"}
    status = {"cdp_reachable": True, "indexed_count": 0, "total_offerings": 20, "missing": ["a"]}
    findings, state = _run(status, monkeypatch, tmp_path, prior_state=prior)
    assert len(findings) == 1
    assert "3 -> 0" in findings[0]["title"]
    assert "Regression" in findings[0]["content"]


def test_unreachable_status_never_logs_a_finding_or_updates_state(tmp_path, monkeypatch):
    status = {"error": "connection refused", "cdp_reachable": False}
    findings, state = _run(status, monkeypatch, tmp_path, prior_state={"indexed_count": 5, "total": 20, "checked_at": "x"})
    assert findings == []
    assert state == {"indexed_count": 5, "total": 20, "checked_at": "x"}  # unchanged


def test_missing_cdp_reachable_key_defaults_to_true(tmp_path, monkeypatch):
    """A worker error response that forgot cdp_reachable shouldn't be
    silently treated as unreachable-and-skip; only an explicit False (or
    a present `error` key) should skip logging."""
    status = {"indexed_count": 4, "total_offerings": 20, "missing": []}
    findings, _state = _run(status, monkeypatch, tmp_path)
    assert len(findings) == 1
