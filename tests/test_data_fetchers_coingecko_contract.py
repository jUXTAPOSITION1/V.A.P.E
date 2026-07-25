"""Tests for agents/data_fetchers.py::get_token_market_by_contract() — real
gap this closes: the raw CoinGecko /coins/{platform}/contract/{address}
response already carries supply/FDV/description/homepage/twitter fields (the
SAME already-fetched response used for the stablecoin-verification check),
but this function used to discard all of it down to 4 price/volume fields.
Hermetic: agents.data_fetchers._get is mocked, no real network call.
"""
from unittest import mock

from agents import data_fetchers as df


_RAW = {
    "id": "arena-2",
    "name": "Arena",
    "symbol": "arena",
    "description": {"en": "The Arena is a <b>SocialFi</b> platform.<br>Stake to earn."},
    "links": {"homepage": ["https://arena.social", ""], "twitter_screen_name": "TheArenaApp"},
    "market_data": {
        "current_price": {"usd": 0.0013},
        "market_cap": {"usd": 5_500_000},
        "total_volume": {"usd": 313697},
        "price_change_percentage_24h": 15.8,
        "fully_diluted_valuation": {"usd": 11_700_000},
        "total_supply": 10_000_000_000,
        "circulating_supply": 4_700_000_000,
        "max_supply": 10_000_000_000,
    },
}


def test_extracts_supply_fdv_and_links():
    with mock.patch.object(df, "_get", return_value=_RAW):
        result = df.get_token_market_by_contract("0xabc", platform="avalanche")
    assert result["coingecko_id"] == "arena-2"
    assert result["total_supply"] == 10_000_000_000
    assert result["circulating_supply"] == 4_700_000_000
    assert result["max_supply"] == 10_000_000_000
    assert result["fdv_usd"] == 11_700_000
    assert result["homepage"] == "https://arena.social"
    assert result["twitter"] == "TheArenaApp"


def test_description_html_is_stripped_and_truncated():
    with mock.patch.object(df, "_get", return_value=_RAW):
        result = df.get_token_market_by_contract("0xabc", platform="avalanche")
    assert result["description"] == "The Arena is a SocialFi platform. Stake to earn."


def test_missing_optional_fields_stay_none_not_fabricated():
    raw = {"id": "x", "name": "X", "symbol": "x",
           "market_data": {"current_price": {"usd": 1.0}}}
    with mock.patch.object(df, "_get", return_value=raw):
        result = df.get_token_market_by_contract("0xabc")
    assert result["homepage"] is None
    assert result["twitter"] is None
    assert result["description"] is None
    assert result["total_supply"] is None


def test_no_market_data_returns_raw_passthrough():
    with mock.patch.object(df, "_get", return_value={"error": "not found"}):
        result = df.get_token_market_by_contract("0xabc")
    assert result == {"error": "not found"}
