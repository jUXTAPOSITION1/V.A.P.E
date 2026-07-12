"""Tests for agents/security_sweep.py's deterministic decision logic:
threat-level computation and the attack-pattern classifier. These are the
'rule-based first' pieces whose output the report and the homepage Threat
Ledger present as ground truth, so a reader must be able to recompute them.
"""
from datetime import datetime, timezone, timedelta

from agents import security_sweep as ss


def _incident(days_ago, amount_m, technique="Some Exploit", chains=("Ethereum",)):
    d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    return {"date": d, "name": f"Test-{days_ago}d", "amount_usd_m": amount_m,
            "technique": technique, "chains": list(chains)}


def test_threat_high_on_big_recent_hack():
    incidents = [_incident(2, ss.BIG_HACK_USD_M + 10)]
    threat, _recent, big = ss.compute_threat_level(incidents)
    assert threat == "HIGH"
    assert len(big) == 1


def test_threat_high_on_three_recent_hacks():
    incidents = [_incident(1, 1), _incident(2, 1), _incident(3, 1)]
    threat, recent, _big = ss.compute_threat_level(incidents)
    assert threat == "HIGH"
    assert len(recent) == 3


def test_threat_medium_on_single_small_recent_hack():
    incidents = [_incident(2, 1)]
    threat, _recent, big = ss.compute_threat_level(incidents)
    assert threat == "MEDIUM"
    assert big == []


def test_threat_low_when_nothing_recent():
    incidents = [_incident(60, 1), _incident(90, 5)]
    threat, recent, _big = ss.compute_threat_level(incidents)
    assert threat == "LOW"
    assert recent == []


def test_threat_low_on_empty_feed():
    assert ss.compute_threat_level([])[0] == "LOW"


def test_classify_technique_known_categories():
    assert ss._classify_technique("Malicious Governance Proposal")["id"] == "governance"
    assert ss._classify_technique("Flashloan Price Oracle Attack")["id"] == "oracle_flashloan"
    assert ss._classify_technique("Reverse MEV Honeypot")["id"] == "honeypot"
    assert ss._classify_technique("LayerZero bridge message spoofing")["id"] == "bridge_exploit"


def test_classify_technique_returns_none_on_unknown():
    assert ss._classify_technique("Some Totally Novel Unmapped Thing") is None
    assert ss._classify_technique("") is None
    assert ss._classify_technique(None) is None


def test_every_pattern_has_required_fields():
    """Guards the ATTACK_PATTERNS table itself: every entry must carry the
    fields learn_from_incidents()/_render_lessons_section() rely on, so a
    malformed addition can't silently break the lesson pipeline."""
    for p in ss.ATTACK_PATTERNS:
        assert p.get("id") and p.get("label") and p.get("keywords")
        assert "prevention" in p and "covered_by" in p


def test_covered_by_claims_are_non_empty_strings_or_none():
    """A 'covered_by' claim asserts a real investigate.py check exists — it
    must be either a real description string or an explicit None, never an
    empty/whitespace string that reads as a claim but says nothing."""
    for p in ss.ATTACK_PATTERNS:
        cb = p["covered_by"]
        assert cb is None or (isinstance(cb, str) and cb.strip())
