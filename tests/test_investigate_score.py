"""Tests for agents/investigate.py::score() — VAPE's crown-jewel risk verdict.

The single most important property this file guards is the one the scoring
rework was built around: the ABSENCE of red flags is NOT evidence of safety.
A clean-looking but anonymous/young/undistributed token must not earn a
PROCEED just because nothing tripped a red flag. If a future change (human or
self-improvement bot) ever regresses that, these tests fail loudly.
"""
from agents.investigate import score
from tests.conftest import clean_gp, clean_dex, days_ago_ms


def _legit_inputs():
    """A genuinely legitimate token: renounced owner, deep liquidity, real
    holder base, long track record, custom-verified source — enough real
    positive evidence to clear the legitimacy cap and reach PROCEED."""
    gp = clean_gp(owner_address="0x0000000000000000000000000000000000000000",
                  holder_count="1200")
    dex = clean_dex(name="Legit Token", symbol="LEGIT",
                    liquidity_usd=800000, pair_created_ms=days_ago_ms(200))
    onchain = {"is_contract": True}
    verif = {"checked": True, "verified": True, "name": "LegitToken"}
    return gp, dex, onchain, verif


def test_honeypot_is_rejected():
    gp = clean_gp(is_honeypot="1")
    s, verdict, reasons, _ = score(gp, clean_dex(), {"is_contract": True}, {})
    assert verdict == "REJECT"
    assert any("HONEYPOT" in r for r in reasons)


def test_clean_but_anonymous_token_is_capped_not_proceed():
    """The load-bearing test: no red flags, but also no real legitimacy
    evidence -> must be capped below PROCEED, never sail through at 90+."""
    gp = clean_gp()  # no owner info, no holders
    dex = clean_dex()  # no liquidity, no age
    s, verdict, reasons, positives = score(gp, dex, {"is_contract": True}, {})
    assert verdict != "PROCEED", f"clean-but-anonymous token wrongly got PROCEED at {s}"
    assert s <= 55
    assert len(positives) == 0
    assert any("capped" in r.lower() for r in reasons)


def test_legit_token_reaches_proceed():
    s, verdict, reasons, positives = score(*_legit_inputs())
    assert verdict == "PROCEED", f"legit token should PROCEED, got {verdict} at {s}: {reasons}"
    assert s >= 80
    assert len(positives) >= 2


def test_verdict_thresholds_are_monotonic():
    """PROCEED >= 80 > CAUTION >= 50 > REJECT. A stronger token never scores
    below a weaker one across the honeypot / clean / legit spectrum."""
    honeypot = score(clean_gp(is_honeypot="1"), clean_dex(), {"is_contract": True}, {})[0]
    anon = score(clean_gp(), clean_dex(), {"is_contract": True}, {})[0]
    legit = score(*_legit_inputs())[0]
    assert honeypot < anon < legit


def test_brand_impersonation_penalized():
    gp = clean_gp(owner_address="0x0000000000000000000000000000000000000000", holder_count="1200")
    dex = clean_dex(name="OpenAI", symbol="OPENAI", liquidity_usd=800000,
                    pair_created_ms=days_ago_ms(200))
    s_imp, v_imp, reasons, _ = score(gp, dex, {"is_contract": True}, {"checked": True, "verified": True, "name": "OpenAI"})
    s_clean = score(*_legit_inputs())[0]
    assert s_imp < s_clean
    assert any("impersonat" in r.lower() for r in reasons)


def test_meme_factory_template_penalized():
    gp = clean_gp(owner_address="0x0000000000000000000000000000000000000000", holder_count="1200")
    dex = clean_dex(name="Some Token", symbol="TKN", liquidity_usd=800000,
                    pair_created_ms=days_ago_ms(200))
    verif = {"checked": True, "verified": True, "name": "ClankerToken"}
    s_factory, _, reasons, _ = score(gp, dex, {"is_contract": True}, verif)
    s_custom = score(*_legit_inputs())[0]
    assert s_factory < s_custom
    assert any("factory" in r.lower() for r in reasons)


def test_deployer_repeat_offender_penalized():
    args = _legit_inputs()
    baseline = score(*args)[0]
    flagged, _, reasons, _ = score(*args, deployer_repeat_offender="0xBADdeployer")
    assert flagged < baseline
    assert any("deployer" in r.lower() for r in reasons)


def test_score_never_out_of_bounds():
    """Even with every red flag on and every legitimacy signal absent, the
    score stays clamped to [0, 100] and returns a valid verdict."""
    gp = clean_gp(**{k: "1" for k in ("is_honeypot", "cannot_sell_all", "is_mintable",
                                      "can_take_back_ownership", "owner_change_balance",
                                      "hidden_owner", "is_proxy", "transfer_pausable")})
    gp["buy_tax"] = "0.5"
    gp["sell_tax"] = "0.5"
    gp["holder_count"] = "1"
    dex = clean_dex(name="OpenAI", liquidity_usd=100, change_24h_pct=500,
                    pair_created_ms=days_ago_ms(0.1))
    s, verdict, _, _ = score(gp, dex, {"is_contract": True},
                             {"checked": True, "verified": False, "name": "ClankerX"},
                             web_rep={"hits": [1, 2]}, deployer_repeat_offender="0xBAD")
    assert 0 <= s <= 100
    assert verdict == "REJECT"
