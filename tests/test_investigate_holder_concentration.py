"""Tests for agents/investigate.py::_holder_concentration()/_lp_lock_status()
and their scoring/report wiring — real, already-fetched GoPlus signals
(the "holders"/"lp_holders" arrays inside the same token_security response
every investigation already calls) that used to sit completely unused,
confirmed by grep: only the scalar holder_count was ever read anywhere in
this codebase. A raw holder count alone can't tell broad organic
distribution apart from a few whales plus a long dust tail, and no report
ever showed whether liquidity was actually locked -- both flagged directly
as missing factors against a live report (investigation-20260725-155143-
0xB8d7710f.md). GoPlus's exact live schema couldn't be verified from this
sandbox (network access blocked, like every other external API here), so
every helper here must degrade to None -- no penalty, no signal, no crash --
on any missing/malformed shape rather than ever guessing wrong.
"""
from agents.investigate import score, _holder_concentration, _lp_lock_status
from tests.conftest import clean_gp, clean_dex


def test_holder_concentration_none_when_holders_array_absent():
    assert _holder_concentration({}) is None
    assert _holder_concentration({"holder_count": "500"}) is None


def test_holder_concentration_none_on_malformed_shapes():
    assert _holder_concentration({"holders": "not a list"}) is None
    assert _holder_concentration({"holders": []}) is None
    assert _holder_concentration({"holders": [{"percent": "not a number"}]}) is None


def test_holder_concentration_sums_top10_excluding_burn_and_lp():
    holders = [
        {"address": "0x" + "11" * 20, "percent": "0.30"},
        {"address": "0x" + "22" * 20, "percent": "0.20"},
        {"address": "0x000000000000000000000000000000000000dead", "percent": "0.25"},  # burn, excluded
        {"address": "0x" + "33" * 20, "tag": "Uniswap V2 LP", "percent": "0.15"},  # LP, excluded
    ]
    result = _holder_concentration({"holders": holders})
    assert result is not None
    assert round(result["top_holders_pct"], 1) == 50.0
    assert result["holders_counted"] == 2


def test_holder_concentration_handles_0_to_100_scale_too():
    """Guard against a schema surprise inflating a 0-100 percent 10x if
    GoPlus's real format ever differs from the assumed 0-1 fraction."""
    holders = [{"address": "0x" + "11" * 20, "percent": "45"}]  # looks like 45%, not 4500%
    result = _holder_concentration({"holders": holders})
    assert result["top_holders_pct"] == 45.0


def test_holder_concentration_only_considers_first_10():
    holders = [{"address": f"0x{i:040x}", "percent": "0.05"} for i in range(1, 16)]
    result = _holder_concentration({"holders": holders})
    assert result["holders_counted"] == 10
    assert round(result["top_holders_pct"], 1) == 50.0


def test_lp_lock_status_none_when_absent_or_malformed():
    assert _lp_lock_status({}) is None
    assert _lp_lock_status({"lp_holders": "nope"}) is None
    assert _lp_lock_status({"lp_holders": [{"percent": "0"}]}) is None


def test_lp_lock_status_computes_locked_share_of_total():
    lp_holders = [
        {"percent": "0.60", "is_locked": "1"},
        {"percent": "0.40", "is_locked": "0"},
    ]
    result = _lp_lock_status({"lp_holders": lp_holders})
    assert result["locked_pct"] == 60.0
    assert result["lp_holders_counted"] == 2


def test_score_penalizes_high_concentration():
    gp = clean_gp(holder_count="5000", holders=[
        {"address": f"0x{i:040x}", "percent": "0.08"} for i in range(1, 11)
    ])
    dex = clean_dex()
    _s, _v, reasons, _p = score(gp, dex, {"is_contract": True}, {})
    assert any("control" in r and "80%" in r for r in reasons)


def test_score_signals_broad_distribution():
    gp = clean_gp(holder_count="5000", holders=[
        {"address": f"0x{i:040x}", "percent": "0.01"} for i in range(1, 11)
    ])
    dex = clean_dex()
    _s, _v, _r, positives = score(gp, dex, {"is_contract": True}, {})
    assert any("only 10%" in p for p in positives)


def test_score_penalizes_mostly_unlocked_liquidity():
    gp = clean_gp(lp_holders=[{"percent": "1.0", "is_locked": "0"}])
    dex = clean_dex()
    _s, _v, reasons, _p = score(gp, dex, {"is_contract": True}, {})
    assert any("liquidity is locked" in r and "deployer can pull" in r for r in reasons)


def test_score_signals_mostly_locked_liquidity():
    gp = clean_gp(lp_holders=[{"percent": "1.0", "is_locked": "1"}])
    dex = clean_dex()
    _s, _v, _r, positives = score(gp, dex, {"is_contract": True}, {})
    assert any("100%" in p and "locked" in p for p in positives)


def test_score_unaffected_when_holders_data_absent():
    """No holders/lp_holders arrays at all (the overwhelming majority of
    real GoPlus responses observed so far) must be a pure no-op, not a
    fabricated penalty or crash."""
    gp = clean_gp(holder_count="5000")
    dex = clean_dex()
    s, verdict, reasons, _p = score(gp, dex, {"is_contract": True}, {})
    assert not any("non-LP/burn holders control" in r for r in reasons)
    assert not any("liquidity is locked" in r for r in reasons)
