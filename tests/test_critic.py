"""Tests for agents/critic.py — the deterministic, same-cycle consistency
check on score()'s own output.

Two properties matter: (1) zero false positives against every real score()
scenario the existing test_investigate_score.py suite already exercises —
a critic that cries wolf on legitimate output is worse than no critic; and
(2) it actually catches genuine inconsistencies when they're deliberately
introduced, since that's the entire point of the module.
"""
from agents import critic
from agents.investigate import score
from tests.conftest import clean_gp, clean_dex, days_ago_ms


# ── zero false positives against real score() outputs ───────────────────────

def test_no_false_positive_on_clean_anonymous_token():
    gp, dex = clean_gp(), clean_dex()
    s, verdict, reasons, positives = score(gp, dex, {"is_contract": True}, {})
    result = critic.verify(gp, {}, s, verdict, reasons, positives)
    assert result["ok"], result["issues"]


def test_no_false_positive_on_legit_proceed():
    gp = clean_gp(owner_address="0x0000000000000000000000000000000000000000", holder_count="1200")
    dex = clean_dex(name="Legit", symbol="LEGIT", liquidity_usd=800000, pair_created_ms=days_ago_ms(200))
    verif = {"checked": True, "verified": True, "name": "LegitToken"}
    s, verdict, reasons, positives = score(gp, dex, {"is_contract": True}, verif)
    assert verdict == "PROCEED"
    result = critic.verify(gp, verif, s, verdict, reasons, positives)
    assert result["ok"], result["issues"]


def test_no_false_positive_on_honeypot_reject():
    gp = clean_gp(is_honeypot="1")
    dex = clean_dex()
    s, verdict, reasons, positives = score(gp, dex, {"is_contract": True}, {})
    assert verdict == "REJECT"
    result = critic.verify(gp, {}, s, verdict, reasons, positives)
    assert result["ok"], result["issues"]


def test_no_false_positive_on_explicit_unverified():
    gp = clean_gp()
    verif = {"checked": True, "verified": False, "name": "Foo"}
    s, verdict, reasons, positives = score(gp, clean_dex(), {"is_contract": True}, verif)
    result = critic.verify(gp, verif, s, verdict, reasons, positives)
    assert result["ok"], result["issues"]


def test_no_false_positive_on_owner_not_renounced():
    gp = clean_gp(owner_address="0xdeadbeef00000000000000000000000000dead")
    s, verdict, reasons, positives = score(gp, clean_dex(), {"is_contract": True}, {})
    result = critic.verify(gp, {}, s, verdict, reasons, positives)
    assert result["ok"], result["issues"]


# ── real inconsistencies are actually caught ────────────────────────────────

def test_catches_verdict_score_band_mismatch():
    result = critic.verify({}, {}, 40, "PROCEED", [], [])
    assert not result["ok"]
    assert any("verdict/score mismatch" in i for i in result["issues"])


def test_catches_honeypot_reason_without_honeypot_flag():
    gp = {"is_honeypot": "0"}
    result = critic.verify(gp, {}, 20, "REJECT", ["[-60] GoPlus: HONEYPOT detected"], [])
    assert not result["ok"]
    assert any("honeypot mismatch" in i for i in result["issues"])


def test_catches_legitimacy_cap_violation():
    result = critic.verify({}, {}, 90, "PROCEED", [], [])
    assert not result["ok"]
    assert any("exceeds the 55 cap" in i for i in result["issues"])


def test_catches_score_out_of_bounds():
    result = critic.verify({}, {}, 150, "PROCEED", [], [])
    assert not result["ok"]
    assert any("out of bounds" in i for i in result["issues"])


def test_catches_renounced_signal_contradicting_owner_present():
    gp = {"owner_address": "0xdeadbeef00000000000000000000000000dead"}
    result = critic.verify(gp, {}, 60, "CAUTION", [], ["Ownership renounced"])
    assert not result["ok"]
    assert any("renounced-signal present" in i for i in result["issues"])


def test_catches_unverified_reason_without_unverified_flag():
    # score kept <=55 so this stays isolated to the intended issue — 0
    # positive signals with a higher score would also trip the legitimacy cap.
    result = critic.verify({}, {"verified": True}, 50, "CAUTION",
                            ["[-15] Contract source UNVERIFIED"], [])
    assert not result["ok"]
    assert any("unverified-reason present" in i for i in result["issues"])


def test_catches_verified_signal_without_verified_flag():
    # A second signal clears the 1-signal/70 cap so PROCEED at 90 stays
    # isolated to the intended verified-signal contradiction.
    result = critic.verify({}, {"verified": False}, 90, "PROCEED", [],
                            ["Custom verified source (not a mass-produced factory template)",
                             "another positive signal"])
    assert not result["ok"]
    assert any("verified-signal present" in i for i in result["issues"])


def test_catches_owner_not_renounced_reason_without_owner_present():
    # score=50 keeps this in the CAUTION band (>=50) per _verdict_for_score,
    # and <=55 avoids the 0-signal cap — isolated to the intended issue.
    gp = {"owner_address": ""}
    result = critic.verify(gp, {}, 50, "CAUTION", ["[-10] Owner not renounced (0x0)"], [])
    assert not result["ok"]
    assert any("owner-not-renounced reason present" in i for i in result["issues"])


def test_catches_legitimacy_cap_violation_one_signal():
    result = critic.verify({}, {}, 90, "PROCEED", [], ["one signal"])
    assert not result["ok"]
    assert any("exceeds the 70 cap" in i for i in result["issues"])


def test_critic_never_raises_on_malformed_input():
    # gp/verif as None would break dict.get() calls elsewhere — the critic
    # must degrade to a reported issue, never propagate an exception.
    result = critic.verify(None, None, 50, "CAUTION", [], [])
    assert isinstance(result, dict) and "ok" in result


def test_log_finding_is_a_noop_without_issues():
    # Must not raise even when Memory isn't wired / issues list is empty.
    critic.log_finding("0x" + "a" * 40, "8453", "TEST", [])
