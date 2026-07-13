"""Tests for agents/security_sweep.py's deterministic decision logic:
threat-level computation and the attack-pattern classifier. These are the
'rule-based first' pieces whose output the report and the homepage Threat
Ledger present as ground truth, so a reader must be able to recompute them.
"""
from datetime import datetime, timezone, timedelta

from agents import security_sweep as ss
from agents import investigate as inv


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


# ── _pick_chain_id() — real chain support, not Base-only ────────────────────

def test_pick_chain_id_prefers_base_when_present():
    assert ss._pick_chain_id(["Ethereum", "Base"], inv.EVM_CHAINS) == "8453"


def test_pick_chain_id_supports_non_base_evm_chain():
    # This is the exact gap that let Kelp ($293M, Ethereum+Arbitrum, no Base)
    # slip past the old Base-only filter forever.
    assert ss._pick_chain_id(["Ethereum", "Arbitrum"], inv.EVM_CHAINS) == "1"


def test_pick_chain_id_none_when_nothing_supported():
    assert ss._pick_chain_id(["Sonic", "Hedera"], inv.EVM_CHAINS) is None


def test_pick_chain_id_none_on_empty():
    assert ss._pick_chain_id([], inv.EVM_CHAINS) is None
    assert ss._pick_chain_id(None, inv.EVM_CHAINS) is None


# ── attempt_incident_forensics() — cross-chain + high-value age exception ──

def _hack(days_ago, amount_m, chains, name="Test Hack"):
    d = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d")
    return {"date": d, "name": name, "amount_usd_m": amount_m,
            "technique": "Exploit", "chains": list(chains)}


def _run_forensics(tmp_path, monkeypatch, incidents):
    monkeypatch.setattr(ss, "ATTACK_RESPONSE_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(ss.ic, "web_search_snippets", lambda *a, **kw: {"results": []})
    return ss.attempt_incident_forensics(incidents)


def test_old_but_high_value_incident_still_attempted(tmp_path, monkeypatch):
    old_and_huge = _hack(days_ago=90, amount_m=293, chains=["Ethereum", "Arbitrum"], name="Kelp")
    outcomes = _run_forensics(tmp_path, monkeypatch, [old_and_huge])
    assert len(outcomes) == 1
    assert outcomes[0]["incident"].endswith("Kelp")


def test_old_and_small_incident_skipped_by_age_gate(tmp_path, monkeypatch):
    old_and_small = _hack(days_ago=90, amount_m=1, chains=["Ethereum"], name="Tiny Old Hack")
    outcomes = _run_forensics(tmp_path, monkeypatch, [old_and_small])
    assert outcomes == []


def test_incident_on_unsupported_chain_only_is_skipped(tmp_path, monkeypatch):
    sonic_only = _hack(days_ago=1, amount_m=500, chains=["Sonic"], name="Unsupported Chain Hack")
    outcomes = _run_forensics(tmp_path, monkeypatch, [sonic_only])
    assert outcomes == []


def test_recent_small_incident_still_attempted(tmp_path, monkeypatch):
    # Ordinary fast-incident-response behavior must survive the age-gate change.
    recent_small = _hack(days_ago=1, amount_m=1, chains=["Base"], name="Fresh Small Hack")
    outcomes = _run_forensics(tmp_path, monkeypatch, [recent_small])
    assert len(outcomes) == 1
    assert outcomes[0]["resolved"] is False
