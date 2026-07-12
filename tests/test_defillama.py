"""Tests for agents/defillama.py — the keyless free-API fetcher's PARSING logic.

Live DefiLlama hosts are unreachable from CI's/dev's sandbox (same as every
llama.fi call in this repo; the real calls run in the scheduled Actions). So
these tests monkeypatch the module's `_get` to return realistic DefiLlama
response shapes and assert the parsing/degradation is correct — the part that's
actually VAPE's code, not DefiLlama's uptime.
"""
import agents.defillama as dl


def _patch(monkeypatch, payload):
    monkeypatch.setattr(dl, "_get", lambda *a, **k: payload)


def test_token_price_parses(monkeypatch):
    _patch(monkeypatch, {"coins": {"base:0xabc": {"price": 1.23, "symbol": "TKN",
                                                  "confidence": 0.99, "timestamp": 1720000000}}})
    r = dl.token_price("base", "0xABC")  # address lowercased into the coin id
    assert r["price"] == 1.23 and r["symbol"] == "TKN" and r["confidence"] == 0.99


def test_token_price_missing_coin_is_honest_error(monkeypatch):
    _patch(monkeypatch, {"coins": {}})
    r = dl.token_price("base", "0xABC")
    assert r.get("error")


def test_token_price_propagates_fetch_error(monkeypatch):
    _patch(monkeypatch, {"error": "HTTP 500"})
    assert dl.token_price("base", "0xabc").get("error") == "HTTP 500"


def test_first_price_computes_age(monkeypatch):
    import time
    ninety_days_ago = int(time.time() - 90 * 86400)
    _patch(monkeypatch, {"coins": {"base:0xabc": {"price": 0.5, "symbol": "OLD",
                                                  "timestamp": ninety_days_ago}}})
    r = dl.token_first_price("base", "0xabc")
    assert 89 <= r["age_days"] <= 91
    assert r["first_seen_iso"].endswith("Z")


def test_protocols_on_chain_filters_and_ranks(monkeypatch):
    _patch(monkeypatch, [
        {"name": "Big", "slug": "big", "logo": "u1", "category": "Dexes", "chainTvls": {"Base": 5e8}},
        {"name": "Small", "slug": "small", "logo": "u2", "category": "Lending", "chainTvls": {"Base": 1e6}},
        {"name": "Elsewhere", "slug": "e", "chainTvls": {"Ethereum": 9e9}},   # not on Base
        {"name": "Zero", "slug": "z", "chainTvls": {"Base": 0}},               # zero TVL, excluded
    ])
    r = dl.protocols_on_chain("Base", top_n=10)
    names = [p["name"] for p in r["protocols"]]
    assert names == ["Big", "Small"]                 # Base-only, TVL-ranked
    assert r["protocols"][0]["logo"] == "u1"         # logo carried through (rich data)


def test_yield_pools_flags_trap_shape(monkeypatch):
    _patch(monkeypatch, {"data": [
        {"pool": "p1", "chain": "Base", "project": "aave-v3", "symbol": "USDC",
         "tvlUsd": 5e6, "apy": 4.2, "apyBase": 4.2, "ilRisk": "no", "exposure": "single"},
        {"pool": "p2", "chain": "Base", "project": "rug", "symbol": "SCAM",
         "tvlUsd": 500, "apy": 90000, "ilRisk": "yes", "exposure": "single"},  # below min_tvl
    ]})
    r = dl.yield_pools(chain="Base", min_tvl=10000)
    assert r["count"] == 1 and r["pools"][0]["project"] == "aave-v3"


def test_stablecoins_computes_depeg(monkeypatch):
    _patch(monkeypatch, {"peggedAssets": [
        {"name": "USD Coin", "symbol": "USDC", "circulating": {"peggedUSD": 3e10}, "price": 1.0},
        {"name": "Broken", "symbol": "BRK", "circulating": {"peggedUSD": 2e8}, "price": 0.87},
        {"name": "Tiny", "symbol": "T", "circulating": {"peggedUSD": 100}, "price": 1.0},  # below min
    ]})
    r = dl.stablecoins(min_mcap=1e8)
    syms = {s["symbol"]: s for s in r["stablecoins"]}
    assert "T" not in syms
    assert syms["BRK"]["depeg"] == 0.13
    assert syms["USDC"]["depeg"] == 0.0


def test_bridges_rank_by_volume(monkeypatch):
    _patch(monkeypatch, {"bridges": [
        {"id": 1, "name": "a", "displayName": "Alpha", "chains": ["Base"], "lastDailyVolume": 100},
        {"id": 2, "name": "b", "displayName": "Beta", "chains": ["Base"], "lastDailyVolume": 900},
    ]})
    r = dl.bridges()
    assert r["bridges"][0]["name"] == "Beta"


def test_treasury_own_token_share(monkeypatch):
    _patch(monkeypatch, {"name": "X", "currentChainTvls": {"OwnTokens": 90, "stablecoins": 10}})
    r = dl.treasury("x")
    assert r["own_token_share"] == 0.9  # 90% own-token treasury = fragility signal


def test_unlocks_surfaces_next_upcoming(monkeypatch):
    import time
    future = time.time() + 10 * 86400
    _patch(monkeypatch, {"name": "X", "events": [
        {"timestamp": time.time() - 86400, "description": "past"},
        {"timestamp": future, "description": "cliff", "noOfTokens": 1000},
    ]})
    r = dl.unlocks("x")
    assert r["next_unlock"]["description"] == "cliff"
    assert 9 <= r["next_unlock"]["in_days"] <= 11


def test_token_intel_degrades_per_field(monkeypatch):
    # price errors, first-price ok — the good field survives the bad one.
    calls = {"n": 0}

    def fake_get(url, *a, **k):
        calls["n"] += 1
        if "prices/current" in url:
            return {"error": "HTTP 429"}
        if "prices/first" in url:
            return {"coins": {"base:0xabc": {"price": 1, "symbol": "T", "timestamp": 1700000000}}}
        return {"error": "n/a"}

    monkeypatch.setattr(dl, "_get", fake_get)
    r = dl.token_intel("base", "0xabc")
    assert r["price"] is None            # errored field nulled, not crashed
    assert r["first_price"]["symbol"] == "T"


# ── DefiLlama signals wired into investigate.py::score() ─────────────────────
# Self-contained (no conftest dependency): this branch predates the shared
# test fixtures, and score()'s new `defillama` param is optional/backward-
# compatible so it composes cleanly once both land.
import time as _time
from agents.investigate import score as _score


def _clean_gp(**o):
    base = {"is_honeypot": "0", "cannot_sell_all": "0", "is_mintable": "0",
            "can_take_back_ownership": "0", "owner_change_balance": "0",
            "hidden_owner": "0", "is_proxy": "0", "transfer_pausable": "0",
            "buy_tax": "0", "sell_tax": "0",
            "owner_address": "0x0000000000000000000000000000000000000000",
            "holder_count": "1200"}
    base.update(o)
    return base


def _legit_dex(**o):
    base = {"name": "Real", "symbol": "REAL", "liquidity_usd": 800000,
            "change_24h_pct": None, "pair_created_ms": (_time.time() - 200 * 86400) * 1000}
    base.update(o)
    return base


def test_score_backward_compatible_without_defillama():
    # Old 6-arg call path must still work unchanged.
    s, verdict, reasons, positives = _score({}, {}, {"is_contract": True}, {})
    assert verdict in ("PROCEED", "CAUTION", "REJECT")


def test_score_low_defillama_confidence_penalized():
    dl = {"price": {"price": 0.001, "confidence": 0.2, "symbol": "X"}, "first_price": {}}
    _s, _v, reasons, _p = _score(_clean_gp(), _legit_dex(), {"is_contract": True},
                                 {"checked": True, "verified": True, "name": "Real"}, defillama=dl)
    assert any("confidence low" in r for r in reasons)


def test_score_defillama_longevity_is_positive_signal():
    dl = {"price": {"price": 1.0, "confidence": 0.99, "symbol": "X"},
          "first_price": {"age_days": 200, "first_seen_iso": "2025-01-01T00:00:00Z"}}
    _s, _v, _r, positives = _score(_clean_gp(), _legit_dex(), {"is_contract": True},
                                   {"checked": True, "verified": True, "name": "Real"}, defillama=dl)
    assert any("longevity" in p for p in positives)


def test_score_defillama_none_is_noop():
    # Absence of DefiLlama data must not change the verdict vs the no-arg path.
    args = (_clean_gp(), _legit_dex(), {"is_contract": True},
            {"checked": True, "verified": True, "name": "Real"})
    a = _score(*args)[0]
    b = _score(*args, defillama=None)[0]
    assert a == b
