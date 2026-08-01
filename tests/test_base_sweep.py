"""Tests for the Base sweep report-quality overhaul: the historical-
comparison loader, the since-last-report delta clauses, and the rule-based
Bounty/Security Surface flags — all deterministic, real-data-only logic
added to agents/base_sweep.py."""
from agents import base_sweep as bs
from agents import intel_common as ic


def _write_prev_report(tmp_path, monkeypatch, body):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(ic, "REPORTS_DIR", str(reports_dir))
    path = reports_dir / "base-2026-07-31-09.md"
    path.write_text(body)
    return str(path)


_PREV_BODY = """# Base Blockchain Sweep Report

**Date:** 2026-07-31 09:00 UTC
**Chain:** Base (Coinbase Ethereum L2, Chain ID 8453)
**Wallet:** 0xabc

---

## BASE HEALTH SCORE: 6.5 / 10

---

## TVL & Chain Activity (real, DefiLlama + Base RPC)

| Metric | Value |
|--------|-------|
| Total TVL | $1,000,000 |
| 24h Change | 2.0% |
| Fees 24h | $10,000 |
| Gas Price | 0.02 gwei |
"""


def test_load_previous_base_report_parses_real_fields(tmp_path, monkeypatch):
    path = _write_prev_report(tmp_path, monkeypatch, _PREV_BODY)
    prev = bs._load_previous_base_report()
    assert prev["path"] == path
    assert prev["date"] == "2026-07-31 09:00 UTC"
    assert prev["health_score"] == 6.5
    assert prev["tvl_usd"] == 1_000_000.0
    assert prev["fees_24h_usd"] == 10_000.0


def test_load_previous_base_report_picks_most_recent_by_filename(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(ic, "REPORTS_DIR", str(reports_dir))
    (reports_dir / "base-2026-07-01-05.md").write_text(_PREV_BODY)
    newer = _PREV_BODY.replace("6.5", "7.0")
    newest_path = reports_dir / "base-2026-08-01-05.md"
    newest_path.write_text(newer)
    prev = bs._load_previous_base_report()
    assert prev["path"] == str(newest_path)
    assert prev["health_score"] == 7.0


def test_load_previous_base_report_returns_none_when_no_reports(tmp_path, monkeypatch):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    monkeypatch.setattr(ic, "REPORTS_DIR", str(reports_dir))
    assert bs._load_previous_base_report() is None


def test_since_last_report_lines_computes_real_deltas():
    prev = {"path": "x", "date": "2026-07-31 09:00 UTC", "health_score": 6.5,
            "tvl_usd": 1_000_000.0, "fees_24h_usd": 10_000.0}
    tvl = {"tvl_usd": 1_100_000.0}
    fees = {"total_fees_24h_usd": 12_000.0}
    lines = bs._since_last_report_lines(prev, 7.0, tvl, fees)
    joined = "\n".join(lines)
    assert "+0.5" in joined  # health score delta
    assert "$100,000" in joined  # TVL delta
    assert "+10.0%" in joined  # TVL % delta
    assert "$2,000" in joined  # fees delta


def test_since_last_report_lines_omits_fields_missing_on_either_side():
    prev = {"path": "x", "date": "d", "health_score": None, "tvl_usd": 1_000_000.0, "fees_24h_usd": None}
    tvl = {"tvl_usd": 1_100_000.0}
    fees = {"total_fees_24h_usd": 12_000.0}
    lines = bs._since_last_report_lines(prev, 7.0, tvl, fees)
    assert len(lines) == 1
    assert "Total TVL" in lines[0]


def test_since_last_report_lines_empty_without_prior_report():
    assert bs._since_last_report_lines(None, 7.0, {"tvl_usd": 1.0}, {}) == []


def test_bounty_security_surface_flags_high_tvl_negative_mover():
    protos = [{"name": "Big Lender", "share_of_base_pct": 40.0, "change_1d": -3.0,
               "change_7d": -1.0, "vape_score": 55}]
    lines = bs._bounty_security_surface(protos, {})
    assert len(lines) == 1
    assert "Big Lender" in lines[0]
    assert "down" in lines[0]


def test_bounty_security_surface_flags_low_vape_score_large_protocol():
    protos = [{"name": "Weak Vault", "share_of_base_pct": 12.0, "change_1d": 1.0,
               "change_7d": 2.0, "vape_score": 25}]
    lines = bs._bounty_security_surface(protos, {})
    assert len(lines) == 1
    assert "Weak Vault" in lines[0]
    assert "VAPE Score of 25" in lines[0]


def test_bounty_security_surface_ignores_small_protocols():
    protos = [{"name": "Tiny Pool", "share_of_base_pct": 1.0, "change_1d": -50.0,
               "change_7d": -50.0, "vape_score": 5}]
    assert bs._bounty_security_surface(protos, {}) == []


def test_bounty_security_surface_includes_base_hack_incidents():
    hacks = {"incidents": [{"date": "2026-07-15", "name": "Foo Bridge Exploit",
                             "amount_usd_m": 4.2, "technique": "reentrancy"}]}
    lines = bs._bounty_security_surface([], hacks)
    assert len(lines) == 1
    assert "Foo Bridge Exploit" in lines[0]
    assert "$4.2M" in lines[0]
    assert "via reentrancy" in lines[0]


def test_bounty_security_surface_empty_when_nothing_to_flag():
    protos = [{"name": "Healthy Dex", "share_of_base_pct": 30.0, "change_1d": 2.0,
               "change_7d": 4.0, "vape_score": 65}]
    assert bs._bounty_security_surface(protos, {}) == []


def test_compute_health_score_still_neutral_with_no_signal():
    assert bs.compute_health_score({}, {}) == 5.0
