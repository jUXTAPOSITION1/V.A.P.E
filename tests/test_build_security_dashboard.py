"""Tests for agents/build_security_dashboard.py — real-data aggregation for
the site's Security Dashboard section. Hermetic: no real file I/O beyond
tmp_path, no real network (GitHubMCPWrapper is a hand-built stub).
"""
import json
from unittest import mock

from agents import build_security_dashboard as bsd


# ── normalize_severity() — one test per real branch ─────────────────────────

def test_normalize_severity_top_level_critical():
    assert bsd.normalize_severity({"severity": "CRITICAL"}) == "CRITICAL"


def test_normalize_severity_top_level_high():
    assert bsd.normalize_severity({"severity": "HIGH"}) == "HIGH"


def test_normalize_severity_top_level_medium_aliases():
    assert bsd.normalize_severity({"severity": "MEDIUM"}) == "MEDIUM"
    assert bsd.normalize_severity({"severity": "MED"}) == "MEDIUM"


def test_normalize_severity_top_level_low():
    assert bsd.normalize_severity({"severity": "LOW"}) == "LOW"


def test_normalize_severity_top_level_none_string_is_info():
    assert bsd.normalize_severity({"severity": "none"}) == "INFO"


def test_normalize_severity_verdict_reject_is_high():
    assert bsd.normalize_severity({"metadata": {"verdict": "REJECT"}}) == "HIGH"


def test_normalize_severity_verdict_caution_is_medium():
    assert bsd.normalize_severity({"metadata": {"verdict": "CAUTION"}}) == "MEDIUM"


def test_normalize_severity_verdict_proceed_is_info():
    assert bsd.normalize_severity({"metadata": {"verdict": "PROCEED"}}) == "INFO"


def test_normalize_severity_tag_worsened_is_high():
    assert bsd.normalize_severity({"tags": ["self-review", "worsened"]}) == "HIGH"


def test_normalize_severity_tag_reject_is_high():
    assert bsd.normalize_severity({"tags": ["reject"]}) == "HIGH"


def test_normalize_severity_tag_coverage_gap_is_medium():
    assert bsd.normalize_severity({"tags": ["coverage-gap"]}) == "MEDIUM"


def test_normalize_severity_tag_backtest_miss_is_medium():
    assert bsd.normalize_severity({"tags": ["backtest-miss"]}) == "MEDIUM"


def test_normalize_severity_tag_caution_is_medium():
    assert bsd.normalize_severity({"tags": ["caution"]}) == "MEDIUM"


def test_normalize_severity_tag_improved_is_info():
    assert bsd.normalize_severity({"tags": ["improved"]}) == "INFO"


def test_normalize_severity_bare_security_tag_falls_through_to_info():
    """A topical 'security' tag alone is categorization, not a rating --
    must not be mistaken for a real severity signal."""
    assert bsd.normalize_severity({"tags": ["security"]}) == "INFO"


def test_normalize_severity_no_signal_at_all_is_info():
    assert bsd.normalize_severity({}) == "INFO"


def test_normalize_severity_top_level_wins_over_verdict_and_tags():
    entry = {"severity": "LOW", "metadata": {"verdict": "REJECT"}, "tags": ["worsened"]}
    assert bsd.normalize_severity(entry) == "LOW"


def test_normalize_severity_verdict_wins_over_tags():
    entry = {"metadata": {"verdict": "PROCEED"}, "tags": ["coverage-gap"]}
    assert bsd.normalize_severity(entry) == "INFO"


# ── build_findings_summary() ────────────────────────────────────────────────

def test_build_findings_summary_counts_by_severity_and_verdict():
    entries = [
        {"severity": "CRITICAL", "timestamp": "2026-07-01T00:00:00Z"},
        {"metadata": {"verdict": "REJECT"}, "timestamp": "2026-07-01T00:00:00Z"},
        {"metadata": {"verdict": "PROCEED"}, "timestamp": "2026-07-01T00:00:00Z"},
        {"tags": ["caution"], "timestamp": "2026-07-08T00:00:00Z"},
    ]
    by_sev, by_verdict, timeline = bsd.build_findings_summary(entries)
    assert by_sev["CRITICAL"] == 1
    assert by_sev["HIGH"] == 1  # the REJECT-verdict row
    assert by_sev["MEDIUM"] == 1  # the caution-tag row
    assert by_sev["INFO"] == 1  # the PROCEED-verdict row
    assert by_verdict == {"PROCEED": 1, "CAUTION": 0, "REJECT": 1}
    assert len(timeline) == 2  # two distinct ISO weeks


def test_build_findings_summary_buckets_by_iso_week():
    entries = [
        {"timestamp": "2026-07-01T00:00:00Z"},  # 2026-W27
        {"timestamp": "2026-07-02T00:00:00Z"},  # same week
    ]
    _by_sev, _by_verdict, timeline = bsd.build_findings_summary(entries)
    assert len(timeline) == 1
    assert timeline[0]["total"] == 2


def test_build_findings_summary_skips_entries_with_unparseable_timestamp():
    entries = [{"severity": "HIGH", "timestamp": "not-a-date"}]
    by_sev, _by_verdict, timeline = bsd.build_findings_summary(entries)
    assert by_sev["HIGH"] == 1  # still counted for severity
    assert timeline == []  # but contributes no timeline bucket


def test_build_findings_summary_empty_input():
    by_sev, by_verdict, timeline = bsd.build_findings_summary([])
    assert by_sev == {s: 0 for s in bsd.SEVERITIES}
    assert by_verdict == {"PROCEED": 0, "CAUTION": 0, "REJECT": 0}
    assert timeline == []


# ── build_lanes() ────────────────────────────────────────────────────────────

class _FakeGitHub:
    """Hand-built stub matching GitHubMCPWrapper's real (bool, result) call
    contract, without any real HTTP."""

    def __init__(self, workflow_runs=None, code_scanning_ok=True, code_scanning_alerts=None):
        self._workflow_runs = workflow_runs or {}
        self._code_scanning_ok = code_scanning_ok
        self._code_scanning_alerts = code_scanning_alerts or []

    def list_workflow_runs(self, repo, workflow_file, per_page=1):
        runs = self._workflow_runs.get(workflow_file)
        if runs is None:
            return False, []
        return True, runs

    def list_code_scanning_alerts(self, repo, state="open"):
        return self._code_scanning_ok, self._code_scanning_alerts


def _run(conclusion="success", started="2026-08-01T00:00:00Z"):
    return [{"conclusion": conclusion, "run_started_at": started}]


def test_build_lanes_covers_every_security_workflow():
    gh = _FakeGitHub()
    with mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True}):
        lanes = bsd.build_lanes(gh, [], {"threat_level": "LOW"})
    assert len(lanes) == len(bsd.SECURITY_WORKFLOWS)
    assert {l["source_workflow"] for l in lanes} == {w for w, _label in bsd.SECURITY_WORKFLOWS}


def test_build_lanes_degrades_honestly_when_workflow_run_api_fails():
    gh = _FakeGitHub(workflow_runs={})  # every lookup returns False, []
    with mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True}):
        lanes = bsd.build_lanes(gh, [], {})
    codeql_lane = next(l for l in lanes if l["id"] == "codeql")
    assert codeql_lane["last_run_conclusion"] is None
    assert codeql_lane["last_run_at"] is None


def test_build_lanes_redteam_headline_counts_tagged_findings_in_window():
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    recent = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    stale = (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
    findings = [
        {"tags": ["ai-redteam"], "severity": "HIGH", "timestamp": recent},
        {"tags": ["ai-redteam"], "severity": "LOW", "timestamp": recent},
        {"tags": ["ai-redteam"], "severity": "HIGH", "timestamp": stale},  # outside 30d window
        {"tags": ["something-else"], "severity": "CRITICAL", "timestamp": recent},
    ]
    gh = _FakeGitHub(workflow_runs={"redteam.yml": _run()})
    with mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True}):
        lanes = bsd.build_lanes(gh, findings, {})
    redteam_lane = next(l for l in lanes if l["id"] == "redteam")
    assert redteam_lane["severity_breakdown"]["HIGH"] == 1
    assert redteam_lane["severity_breakdown"]["LOW"] == 1
    assert sum(redteam_lane["severity_breakdown"].values()) == 2  # the old + untagged rows excluded


def test_build_lanes_intel_sweeps_reports_real_threat_level_and_coverage():
    gh = _FakeGitHub(workflow_runs={"intel-sweeps.yml": _run()})
    with mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True}):
        lanes = bsd.build_lanes(gh, [], {"threat_level": "HIGH"})
    lane = next(l for l in lanes if l["id"] == "intel-sweeps")
    assert lane["threat_level"] == "HIGH"
    assert 0 <= lane["coverage_ratio"] <= 1
    assert isinstance(lane["gap_patterns"], list)
    assert len(lane["gap_patterns"]) > 0  # real ATTACK_PATTERNS has genuine gaps


def test_build_lanes_findings_seal_reflects_chain_verify_result():
    gh = _FakeGitHub(workflow_runs={"findings-seal.yml": _run()})
    with mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": False}):
        lanes = bsd.build_lanes(gh, [], {})
    lane = next(l for l in lanes if l["id"] == "findings-seal")
    assert lane["chain_intact"] is False
    assert lane["headline"] == "BROKEN"


def test_build_lanes_review_ledger_counts_recent_drift_lessons():
    findings = [
        {"category": "lesson", "tags": ["self-review", "worsened"], "timestamp": "2026-08-01T00:00:00Z"},
        {"category": "lesson", "tags": ["self-review", "improved"], "timestamp": "2026-08-01T00:00:00Z"},
        {"category": "finding", "tags": ["worsened"], "timestamp": "2026-08-01T00:00:00Z"},  # not a lesson
    ]
    gh = _FakeGitHub(workflow_runs={"review-ledger.yml": _run()})
    with mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True}):
        lanes = bsd.build_lanes(gh, findings, {})
    lane = next(l for l in lanes if l["id"] == "review-ledger")
    assert lane["worsened_30d"] == 1
    assert lane["improved_30d"] == 1


# ── build() end-to-end, all I/O redirected/mocked ───────────────────────────

def test_build_writes_snapshot_and_appends_history(tmp_path, monkeypatch):
    out_path = tmp_path / "security-dashboard.json"
    history_path = tmp_path / "security-dashboard-history.jsonl"
    findings_path = tmp_path / "findings.jsonl"
    findings_path.write_text(json.dumps({"severity": "HIGH", "timestamp": "2026-08-01T00:00:00Z"}) + "\n")
    attack_feed_path = tmp_path / "attack-feed.json"
    attack_feed_path.write_text(json.dumps({"threat_level": "MEDIUM"}))

    monkeypatch.setattr(bsd, "OUT_PATH", str(out_path))
    monkeypatch.setattr(bsd, "HISTORY_PATH", str(history_path))
    monkeypatch.setattr(bsd, "FINDINGS_PATH", str(findings_path))
    monkeypatch.setattr(bsd, "ATTACK_FEED_PATH", str(attack_feed_path))

    with mock.patch.object(bsd, "GitHubMCPWrapper", return_value=_FakeGitHub()), \
         mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True, "seals_checked": 0,
                                                                        "lines_covered": 0, "unsealed_lines": 1}):
        dashboard = bsd.build()

    assert dashboard["overall_threat_level"] == "MEDIUM"
    assert dashboard["findings_by_severity"]["HIGH"] == 1
    assert json.loads(out_path.read_text())["overall_threat_level"] == "MEDIUM"
    history_lines = history_path.read_text().strip().splitlines()
    assert len(history_lines) == 1
    assert json.loads(history_lines[0])["overall_threat_level"] == "MEDIUM"


def test_build_handles_missing_attack_feed_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(bsd, "OUT_PATH", str(tmp_path / "out.json"))
    monkeypatch.setattr(bsd, "HISTORY_PATH", str(tmp_path / "history.jsonl"))
    monkeypatch.setattr(bsd, "FINDINGS_PATH", str(tmp_path / "no-such-findings.jsonl"))
    monkeypatch.setattr(bsd, "ATTACK_FEED_PATH", str(tmp_path / "no-such-attack-feed.json"))

    with mock.patch.object(bsd, "GitHubMCPWrapper", return_value=_FakeGitHub()), \
         mock.patch.object(bsd.findings_chain, "verify", return_value={"ok": True}):
        dashboard = bsd.build()

    assert dashboard["overall_threat_level"] is None
    assert dashboard["findings_by_severity"] == {s: 0 for s in bsd.SEVERITIES}
