"""Tests for agents/token_scan.py::_top_holder_concentration_pct()/
_lp_locked_pct() and their wiring into scan() — the free Hunt console's own
scanning tier (also backing the paid x402 quick-check offerings, per
scan()'s docstring: "the free Hunt console, the paid x402 offerings, and
deep investigations never disagree on the checks they share"). Real gap
this closes: GoPlus's response already includes "holders"/"lp_holders"
arrays inside the SAME `gp` dict this function already fetches (keyless,
no new API call), mirroring the identical fix already shipped in
agents/investigate.py::_holder_concentration()/_lp_lock_status() — see
those functions' docstrings for the full context and the schema-
uncertainty caveat that also applies here.
"""
from unittest import mock

from agents import token_scan


def test_concentration_none_when_holders_array_absent():
    assert token_scan._top_holder_concentration_pct({}) is None


def test_concentration_none_on_malformed_shapes():
    assert token_scan._top_holder_concentration_pct({"holders": "nope"}) is None
    assert token_scan._top_holder_concentration_pct({"holders": []}) is None


def test_concentration_excludes_burn_and_lp_tagged_holders():
    holders = [
        {"address": "0x" + "11" * 20, "percent": "0.30"},
        {"address": "0x" + "22" * 20, "percent": "0.20"},
        {"address": "0x000000000000000000000000000000000000dead", "percent": "0.25"},
        {"address": "0x" + "33" * 20, "tag": "Uniswap V2 LP", "percent": "0.15"},
    ]
    result = token_scan._top_holder_concentration_pct({"holders": holders})
    assert round(result, 1) == 50.0


def test_lp_locked_pct_none_when_absent_or_malformed():
    assert token_scan._lp_locked_pct({}) is None
    assert token_scan._lp_locked_pct({"lp_holders": [{"percent": "0"}]}) is None


def test_lp_locked_pct_computes_locked_share():
    lp_holders = [{"percent": "0.6", "is_locked": "1"}, {"percent": "0.4", "is_locked": "0"}]
    assert token_scan._lp_locked_pct({"lp_holders": lp_holders}) == 60.0


def _mock_gp_dex(gp_extra=None):
    gp = {"is_honeypot": "0", "buy_tax": "0", "sell_tax": "0", "is_mintable": "0",
          "owner_address": "", "is_proxy": "0", "cannot_sell_all": "0",
          "transfer_pausable": "0", "holder_count": "5000", "lp_holder_count": "5"}
    if gp_extra:
        gp.update(gp_extra)
    return {"result": {"0x" + "aa" * 20: gp}}


def test_scan_flags_concentrated_holders(monkeypatch):
    holders = [{"address": f"0x{i:040x}", "percent": "0.08"} for i in range(1, 11)]
    gp_raw = _mock_gp_dex({"holders": holders})
    with mock.patch.object(token_scan, "_get", side_effect=[gp_raw, {"pairs": []}]):
        result = token_scan.scan("0x" + "aa" * 20)
    assert any(f.startswith("concentrated_holders_") for f in result["flags"])


def test_scan_flags_mostly_unlocked_liquidity(monkeypatch):
    gp_raw = _mock_gp_dex({"lp_holders": [{"percent": "1.0", "is_locked": "0"}]})
    with mock.patch.object(token_scan, "_get", side_effect=[gp_raw, {"pairs": []}]):
        result = token_scan.scan("0x" + "aa" * 20)
    assert any(f.startswith("lp_mostly_unlocked_") for f in result["flags"])


def test_scan_no_extra_flags_when_holders_data_absent(monkeypatch):
    gp_raw = _mock_gp_dex()
    with mock.patch.object(token_scan, "_get", side_effect=[gp_raw, {"pairs": []}]):
        result = token_scan.scan("0x" + "aa" * 20)
    assert not any(f.startswith("concentrated_holders_") or f.startswith("lp_mostly_unlocked_")
                   for f in result["flags"])
