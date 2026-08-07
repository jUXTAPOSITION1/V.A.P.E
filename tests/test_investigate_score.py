"""Tests for agents/investigate.py::score() — VAPE's crown-jewel risk verdict.

The single most important property this file guards is the one the scoring
rework was built around: the ABSENCE of red flags is NOT evidence of safety.
A clean-looking but anonymous/young/undistributed token must not earn a
PROCEED just because nothing tripped a red flag. If a future change (human or
self-improvement bot) ever regresses that, these tests fail loudly.
"""
from agents.investigate import score, _stablecoin_context, _apply_confidence_gap_cap
from tests.conftest import clean_gp, clean_dex, days_ago_ms


def _real_usdt_shaped_inputs():
    """Real, observed shape of the USDT-on-Base miss (user-reported):
    is_mintable + owner_change_balance + owner-not-renounced all firing at
    full weight on a globally recognized, deeply liquid stablecoin, with
    only holder count as positive evidence — scored 45/100 REJECT before
    the stablecoin-context fix. Owner address is Base's real predeploy
    proxy admin (0x4200...000010, matches the report screenshot), not a
    fabricated stand-in."""
    gp = clean_gp(is_mintable="1", owner_change_balance="1",
                  owner_address="0x4200000000000000000000000000000000000010",
                  holder_count="612036")
    dex = clean_dex(name="Tether USD", symbol="USDT", liquidity_usd=200000)
    onchain = {"is_contract": True}
    verif = {"checked": False}
    return gp, dex, onchain, verif


CG_USDT = {"name": "Tether", "symbol": "usdt", "price_usd": 0.999, "market_cap_usd": 1.6e11}


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
    _s, verdict, reasons, _ = score(gp, clean_dex(), {"is_contract": True}, {})
    assert verdict == "REJECT"
    assert any("HONEYPOT" in r for r in reasons)


def test_very_low_liquidity_is_not_double_counted():
    """Real bug this pins (confirmed against a live report): liquidity < $10k
    used to trip BOTH "Very low liquidity" (-25) and "Low liquidity" (-10)
    since the second check's `< 50000` had no lower bound at the first
    tier's own cutoff -- one real fact (liquidity is very low) penalized
    twice. Every other tiered check in score() (holders, top-holder
    concentration, pair age) already uses mutually exclusive bounded
    ranges; this pins that liquidity now does too."""
    gp = clean_gp()
    dex = clean_dex(liquidity_usd=3)
    _s, _verdict, reasons, _positives = score(gp, dex, {"is_contract": True}, {})
    liquidity_reasons = [r for r in reasons if "liquidity" in r.lower() and "$3" in r]
    assert len(liquidity_reasons) == 1, f"expected exactly one liquidity penalty, got {liquidity_reasons}"
    assert "[-25]" in liquidity_reasons[0]  # the more severe tier wins, not both


def test_confidence_gap_caps_proceed_to_caution():
    """Real bug this pins (confirmed against a live report,
    investigation-20260807-152512-0x72e4f9F8.md, BITCOIN/HarryPotterObamaSonic10Inu):
    a 100/100 PROCEED score sat right next to the same report's own Gaps &
    Confidence section rating independent confirmation of claimed CEX
    listings/audit at only 30% confidence, and an Expert Assessment that
    recommended only a small, high-risk speculative position. A low-confidence
    gap on something material must pull the DISPLAYED score/verdict down, not
    leave a perfect score standing next to a hedged conclusion."""
    gaps = [{"description": "Independent confirmation of claimed CEX listings and audit",
             "confidence": 0.3, "next_action": "Verify listings directly with exchanges"}]
    s, verdict, reasons = _apply_confidence_gap_cap(100, "PROCEED", ["[+10] some positive signal"], gaps)
    assert s == 69
    assert verdict == "CAUTION"
    assert any("[capped at 69]" in r for r in reasons)
    assert any("30%" in r for r in reasons)


def test_confidence_gap_cap_is_noop_when_confident():
    """A gap with confidence >= 0.75 is not material enough to cap anything —
    must be a pure no-op so well-supported reports aren't penalized for
    routine, low-stakes follow-ups."""
    gaps = [{"description": "Minor cosmetic detail", "confidence": 0.9, "next_action": "n/a"}]
    reasons_in = ["[+10] some positive signal"]
    s, verdict, reasons = _apply_confidence_gap_cap(100, "PROCEED", reasons_in, gaps)
    assert s == 100
    assert verdict == "PROCEED"
    assert reasons == reasons_in


def test_confidence_gap_cap_ignores_empty_gaps():
    reasons_in = ["[+10] some positive signal"]
    s, verdict, reasons = _apply_confidence_gap_cap(100, "PROCEED", reasons_in, [])
    assert (s, verdict, reasons) == (100, "PROCEED", reasons_in)
    s, verdict, reasons = _apply_confidence_gap_cap(100, "PROCEED", reasons_in, None)
    assert (s, verdict, reasons) == (100, "PROCEED", reasons_in)


def test_confidence_gap_cap_never_raises_score():
    """A low-confidence gap on an already-low score must never push it UP to
    the cap ceiling -- this is strictly a ceiling, never a floor."""
    gaps = [{"description": "x", "confidence": 0.3, "next_action": "y"}]
    s, verdict, reasons = _apply_confidence_gap_cap(40, "REJECT", ["[-40] some red flag"], gaps)
    assert s == 40
    assert verdict == "REJECT"
    assert not any("capped" in r.lower() for r in reasons)


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
    s_imp, _v_imp, reasons, _ = score(gp, dex, {"is_contract": True}, {"checked": True, "verified": True, "name": "OpenAI"})
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


def test_deployer_cluster_size_is_a_distinct_penalty():
    """The graph-derived factory-scale signal must fire independently of
    deployer_repeat_offender — a mass-token-factory deployer whose OTHER
    tokens are all still PROCEED (so repeat_offender never trips) is still a
    real, distinct risk this signal exists to catch. Uses a legit-shaped
    input (enough positive signals to clear the legitimacy cap) so the
    incremental deduction is visible rather than absorbed by the cap."""
    gp = clean_gp(owner_address="0x0000000000000000000000000000000000000000", holder_count="1200")
    dex = clean_dex(name="Legit", symbol="LEGIT", liquidity_usd=800000, pair_created_ms=days_ago_ms(200))
    verif = {"checked": True, "verified": True, "name": "LegitToken"}
    baseline, _, _, _ = score(gp, dex, {"is_contract": True}, verif)
    clustered, _, reasons, _ = score(gp, dex, {"is_contract": True}, verif, deployer_cluster_size=5)
    assert clustered == baseline - 15
    assert any("mass-token-factory" in r for r in reasons)


def test_deployer_cluster_size_and_repeat_offender_both_apply_additively():
    gp, dex = clean_gp(), clean_dex()
    both, _, reasons, _ = score(gp, dex, {"is_contract": True}, {},
                                deployer_repeat_offender="0xBAD", deployer_cluster_size=5)
    just_repeat, _, _, _ = score(gp, dex, {"is_contract": True}, {},
                                 deployer_repeat_offender="0xBAD")
    assert both < just_repeat  # cluster signal stacks on top, doesn't replace
    assert any("prior CAUTION/REJECT" in r for r in reasons)
    assert any("mass-token-factory" in r for r in reasons)


def test_deployer_cluster_size_none_is_noop():
    gp, dex = clean_gp(), clean_dex()
    a = score(gp, dex, {"is_contract": True}, {})[0]
    b = score(gp, dex, {"is_contract": True}, {}, deployer_cluster_size=None)[0]
    assert a == b


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


# ── stablecoin context (real, address-verified CoinGecko contract lookup) ──

def test_stablecoin_context_recognizes_real_verified_stablecoin():
    ctx = _stablecoin_context(CG_USDT)
    assert ctx is not None
    assert ctx["market_cap_usd"] == CG_USDT["market_cap_usd"]


def test_stablecoin_context_none_without_coingecko_match():
    """No CoinGecko contract data at all (404/untracked/outage) — the
    default, honest "no evidence either way" case for the vast majority of
    tokens, which are not stablecoins."""
    assert _stablecoin_context(None) is None


def test_stablecoin_context_none_below_mcap_quality_bar():
    """A thin/failed stablecoin experiment doesn't get the exception just
    because its price happens to sit near $1 — matches
    agents/defillama.py::stablecoins()'s own $100M quality bar."""
    small = {"name": "Nano Dollar", "symbol": "nusd", "price_usd": 1.0, "market_cap_usd": 5e6}
    assert _stablecoin_context(small) is None


def test_stablecoin_context_none_when_depegging():
    """A real asset that's actually depegging is a live risk signal, not a
    case for waiving mint/admin-key penalties."""
    depegged = {"name": "Some Stable", "symbol": "sst", "price_usd": 0.80, "market_cap_usd": 2e8}
    assert _stablecoin_context(depegged) is None


def test_stablecoin_context_none_on_missing_price_or_mcap_fields():
    assert _stablecoin_context({"name": "X", "symbol": "x"}) is None


def test_real_usdt_case_scores_proceed_with_coingecko_verification():
    """Direct regression test for the user-reported bug: real USDT-shaped
    inputs (mintable + owner-controlled-balance-change + unrenounced owner,
    the exact three flags GoPlus reported) scored 45/100 REJECT before this
    fix. With a real, address-verified CoinGecko match, those three specific
    penalties are refunded and the verdict recovers to PROCEED."""
    args = _real_usdt_shaped_inputs()
    without_cg = score(*args)
    with_cg = score(*args, coingecko_contract=CG_USDT)
    assert without_cg[1] == "REJECT", f"sanity check: unfixed case should still reproduce REJECT, got {without_cg}"
    assert with_cg[0] > without_cg[0]
    assert with_cg[1] == "PROCEED", f"expected PROCEED with real stablecoin verification, got {with_cg}"
    assert any("Verified major stablecoin" in r for r in with_cg[2])
    assert any("market-data-recognized major stablecoin" in p for p in with_cg[3])


def test_stablecoin_refund_never_touches_unrelated_red_flags():
    """The stablecoin context must only refund the three specific
    compliance-mechanism flags — a genuinely honeypot-flagged or high-tax
    token must still REJECT even if it happens to match a stablecoin lookup
    (e.g. a compromised/malicious fork of a real asset)."""
    gp = clean_gp(is_honeypot="1", is_mintable="1", owner_change_balance="1",
                  owner_address="0x4200000000000000000000000000000000000010",
                  holder_count="612036")
    dex = clean_dex(name="Tether USD", symbol="USDT", liquidity_usd=200000)
    s, verdict, reasons, _ = score(gp, dex, {"is_contract": True}, {"checked": False},
                                   coingecko_contract=CG_USDT)
    assert verdict == "REJECT"
    assert any("HONEYPOT" in r for r in reasons)


def test_stablecoin_context_none_is_a_noop_on_score():
    gp, dex = clean_gp(), clean_dex()
    a = score(gp, dex, {"is_contract": True}, {})[0]
    b = score(gp, dex, {"is_contract": True}, {}, coingecko_contract=None)[0]
    assert a == b


# ── stablecoin-brand impersonation (the inverse of the exception above) ──

def test_fake_usdc_claiming_ticker_far_off_peg_is_penalized():
    """Direct regression test for the user-reported bug: a token
    self-declaring symbol "USDC" but actually named "United States of Doge
    CashCat" and trading at $0.0001865 (real report: intel/investigations/
    investigation-20260725-041324-0x8dB2be2b.md) scored only 68/100 CAUTION
    with no penalty at all for stealing the ticker. With no CoinGecko
    verification and a price nowhere near $1, this must now take a real
    impersonation penalty."""
    gp = clean_gp(is_mintable="1", holder_count="24581")
    dex = clean_dex(name="United States of Doge CashCat", symbol="USDC",
                     liquidity_usd=158553.85, price_usd=0.0001865,
                     pair_created_ms=days_ago_ms(8.5))
    s, verdict, reasons, _ = score(gp, dex, {"is_contract": True},
                                   {"checked": True, "verified": True, "name": "DropERC20"})
    assert any("brand impersonation" in r for r in reasons), reasons
    assert verdict != "PROCEED"


def test_stablecoin_brand_impersonation_does_not_trip_on_real_verified_stablecoin():
    """A real, CoinGecko-address-verified stablecoin claiming its own real
    ticker (e.g. real USDT) must never trip the impersonation penalty —
    stable_ctx being truthy short-circuits the check entirely."""
    args = _real_usdt_shaped_inputs()
    _s, _verdict, reasons, _ = score(*args, coingecko_contract=CG_USDT)
    assert not any("brand impersonation" in r for r in reasons)


def test_stablecoin_brand_impersonation_stays_neutral_on_unindexed_but_pegged_asset():
    """A genuine ~$1 asset that simply isn't in CoinGecko's contract index
    (thin/bridged/wrapped variant, never independently verified) must stay
    neutral -- no bonus, no penalty -- rather than being treated as an
    impersonator merely for lacking CoinGecko coverage."""
    gp = clean_gp()
    dex = clean_dex(name="Wrapped USD Coin (Bridge)", symbol="USDC",
                     liquidity_usd=50000, price_usd=1.01)
    _s, _verdict, reasons, _ = score(gp, dex, {"is_contract": True}, {"checked": False})
    assert not any("brand impersonation" in r for r in reasons)


def test_stablecoin_brand_impersonation_does_not_trip_on_unrelated_symbol_substring():
    """Exact-ticker matching guard: an unrelated token whose symbol merely
    contains a stablecoin ticker's letters (e.g. "DAIYA" containing "dai")
    must not false-positive -- only an exact symbol match counts."""
    gp = clean_gp()
    dex = clean_dex(name="Daiya Token", symbol="DAIYA",
                     liquidity_usd=50000, price_usd=0.002)
    _s, _verdict, reasons, _ = score(gp, dex, {"is_contract": True}, {"checked": False})
    assert not any("brand impersonation" in r for r in reasons)
