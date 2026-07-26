"""Tests for market_intel's real upgrade (2026-07-26, direct user report
against a live $0.07 purchase): agents/data_fetchers.py::
get_base_tvl_and_protocols() now derives per-protocol share/category-
breakdown/concentration-risk/gainers-losers signals from data it already
fetches, get_token_price() no longer silently ships an empty `prices` dict
on a CoinGecko failure, and _market_overview_narrative() builds a real,
template-based (non-LLM) summary sentence from the same real numbers.
"""
from unittest import mock

from agents import data_fetchers as df


_CHAINS = [{"name": "Base", "tvl": 1_000_000.0, "change_1d": 2.0, "change_7d": 5.0}]
_PROTOCOLS = [
    {"name": "Alpha Lending", "chains": ["Base"], "category": "Lending",
     "chainTvls": {"Base": 700_000.0}, "change_1d": 1.0, "change_7d": 2.0, "change_1m": 3.0},
    {"name": "Beta DEX", "chains": ["Base"], "category": "Dexes",
     "chainTvls": {"Base": 200_000.0}, "change_1d": -5.0, "change_7d": -1.0, "change_1m": 0.0},
    {"name": "Gamma Yield", "chains": ["Base"], "category": "Yield",
     "chainTvls": {"Base": 100_000.0}, "change_1d": 10.0, "change_7d": 4.0, "change_1m": 1.0},
    {"name": "Excluded CEX", "chains": ["Base"], "category": "CEX",
     "chainTvls": {"Base": 50_000.0}, "change_1d": 0.0, "change_7d": 0.0, "change_1m": 0.0},
]


def _fake_get(url, *args, **kwargs):
    if "v2/chains" in url:
        return _CHAINS
    if "/protocols" in url:
        return _PROTOCOLS
    return {"error": "unexpected url in test", "url": url}


def test_top_protocols_carry_share_and_category():
    with mock.patch.object(df, "_get", side_effect=_fake_get):
        out = df.get_base_tvl_and_protocols(top_n=10)
    assert out["tvl_usd"] == 1_000_000.0
    top = {p["name"]: p for p in out["top_protocols"]}
    assert top["Alpha Lending"]["share_of_base_pct"] == 70.0
    assert top["Alpha Lending"]["category"] == "Lending"
    assert top["Beta DEX"]["share_of_base_pct"] == 20.0
    # CEX-category entries are excluded from the ranked/real-DeFi set.
    assert "Excluded CEX" not in top


def test_category_breakdown_covers_all_real_protocols_not_just_top_n():
    with mock.patch.object(df, "_get", side_effect=_fake_get):
        out = df.get_base_tvl_and_protocols(top_n=1)  # only Alpha Lending makes the top slice
    # Even though Beta/Gamma are cut from top_protocols, their categories
    # must still count in the breakdown (computed over base_protos, not top).
    assert out["category_breakdown_pct"]["Lending"] == 70.0
    assert out["category_breakdown_pct"]["Dexes"] == 20.0
    assert out["category_breakdown_pct"]["Yield"] == 10.0


def test_concentration_risk_reflects_top3_share():
    with mock.patch.object(df, "_get", side_effect=_fake_get):
        out = df.get_base_tvl_and_protocols(top_n=10)
    # Alpha(70) + Beta(20) + Gamma(10) = 100% of real (non-CEX) TVL.
    assert out["concentration_risk"].startswith("HIGH")
    assert "100.0%" in out["concentration_risk"]


def test_gainers_and_losers_split_by_sign():
    with mock.patch.object(df, "_get", side_effect=_fake_get):
        out = df.get_base_tvl_and_protocols(top_n=10)
    gainer_names = [g["name"] for g in out["top_gainers_24h"]]
    loser_names = [l["name"] for l in out["top_losers_24h"]]
    assert gainer_names[0] == "Gamma Yield"  # +10%, the biggest gainer
    assert loser_names[0] == "Beta DEX"  # -5%, the only loser


def test_get_token_price_falls_back_to_defillama_on_coingecko_failure():
    def fake_get(url, *args, **kwargs):
        if "simple/price" in url:
            return {}  # the exact silent-empty shape observed in production
        if "prices/current" in url:
            return {"coins": {"coingecko:ethereum": {"price": 2500.0},
                               "coingecko:bitcoin": {"price": 97000.0}}}
        return {"error": "unexpected url"}
    with mock.patch.object(df, "_get", side_effect=fake_get):
        out = df.get_token_price("ethereum,bitcoin")
    assert out["ethereum"]["usd"] == 2500.0
    assert out["bitcoin"]["usd"] == 97000.0


def test_get_token_price_fills_only_missing_ids_from_fallback():
    def fake_get(url, *args, **kwargs):
        if "simple/price" in url:
            return {"ethereum": {"usd": 2600.0}}  # bitcoin missing
        if "prices/current" in url:
            return {"coins": {"coingecko:bitcoin": {"price": 98000.0}}}
        return {"error": "unexpected url"}
    with mock.patch.object(df, "_get", side_effect=fake_get):
        out = df.get_token_price("ethereum,bitcoin")
    assert out["ethereum"]["usd"] == 2600.0  # kept from CoinGecko, not overwritten
    assert out["bitcoin"]["usd"] == 98000.0  # filled from the fallback


def test_get_token_price_returns_full_coingecko_result_untouched_when_complete():
    def fake_get(url, *args, **kwargs):
        assert "prices/current" not in url, "fallback must not be called when CoinGecko already has everything"
        return {"ethereum": {"usd": 2500.0}, "bitcoin": {"usd": 97000.0}}
    with mock.patch.object(df, "_get", side_effect=fake_get):
        out = df.get_token_price("ethereum,bitcoin")
    assert out == {"ethereum": {"usd": 2500.0}, "bitcoin": {"usd": 97000.0}}


def test_market_overview_narrative_builds_from_real_fields_only():
    tvl = {"tvl_usd": 4_500_000_000, "tvl_24h_change_pct": 1.5,
           "top_protocols": [{"name": "Alpha Lending", "share_of_base_pct": 68.0}],
           "category_breakdown_pct": {"Lending": 72.4, "Dexes": 11.8}}
    dex_vol = {"vol_24h_usd": 396_000_000}
    fng = {"value": 42, "classification": "Fear"}
    glob_m = {"mcap_change_24h_pct": -0.8}
    text = df._market_overview_narrative(tvl, dex_vol, fng, glob_m)
    assert "$4,500,000,000" in text
    assert "up 1.5%" in text
    assert "Lending leads" in text
    assert "68.0%" in text
    assert "$396,000,000" in text
    assert "42 (Fear)" in text
    assert "down 0.8%" in text


def test_market_overview_narrative_omits_missing_fields_honestly():
    text = df._market_overview_narrative({}, {}, {}, {})
    assert text == "Insufficient real data this cycle to summarize."
