"""Tests for agents/prediction_markets.py — the Polymarket/Kalshi crypto-
relevance filter and response-parsing logic. Live gamma-api.polymarket.com
and api.elections.kalshi.com are unreachable from CI's/dev's sandbox (same as
every external API in this repo), so these tests monkeypatch the module's
`_get` to return realistic response shapes and assert the filtering/parsing
is correct.
"""
import agents.prediction_markets as pm


def _patch(monkeypatch, mapping):
    def fake_get(url, ttl=120, cache_key=None, timeout=12):
        for needle, payload in mapping.items():
            if needle in url:
                return payload
        return {"error": "unexpected url in test", "url": url}
    monkeypatch.setattr(pm, "_get", fake_get)


POLY_MIXED = [
    {"id": "1", "question": "Will Bitcoin hit $150k by end of 2026?", "category": "Crypto",
     "outcomePrices": '["0.62", "0.38"]', "outcomes": '["Yes", "No"]',
     "volume": "125000.5", "liquidity": "40000", "endDate": "2099-12-31", "slug": "btc-150k-2026"},
    {"id": "2", "question": "Will the Lakers win the championship?", "category": "Sports",
     "outcomePrices": '["0.1", "0.9"]', "outcomes": '["Yes", "No"]',
     "volume": "500000", "liquidity": "90000", "endDate": "2099-06-01", "slug": "lakers-champ"},
]

# A grouped/multi-outcome market — its own slug isn't a valid /event/ path,
# only its parent event's slug is.
POLY_GROUPED = [
    {"id": "3", "question": "Will the Fed cut rates and will that move crypto markets?", "category": "Crypto",
     "outcomePrices": '["0.4", "0.6"]', "outcomes": '["Yes", "No"]',
     "volume": "70000", "liquidity": "15000", "endDate": "2099-09-01",
     "slug": "fed-decision-sub-market", "events": [{"slug": "fed-rate-decision-2026"}]},
]

# Same crypto-relevant question but already past its endDate — Polymarket's
# active=true&closed=false leaves these in the list past resolution.
POLY_EXPIRED = [
    {"id": "4", "question": "Will Ethereum flip Bitcoin by Q1 2026?", "category": "Crypto",
     "outcomePrices": '["0.05", "0.95"]', "outcomes": '["Yes", "No"]',
     "volume": "300000", "liquidity": "50000", "endDate": "2020-01-01", "slug": "eth-flip-q1-2026"},
]

KALSHI_MIXED = {"markets": [
    {"ticker": "KXETHHACK-26JUL31-B1", "series_ticker": "KXETHHACK", "event_ticker": "KXETHHACK-26JUL31",
     "title": "Will a major DeFi protocol on Ethereum be hacked in July?",
     "yes_bid": 15, "yes_ask": 18, "volume": 8000, "close_time": "2026-07-31"},
    {"ticker": "KXPRES-26", "series_ticker": "KXPRES", "event_ticker": "KXPRES-26",
     "title": "Who will win the presidency?",
     "yes_bid": 50, "yes_ask": 52, "volume": 900000, "close_time": "2026-11-01"},
]}


def test_polymarket_filters_to_crypto_relevant_only(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": POLY_MIXED})
    r = pm.polymarket_crypto_markets(limit=10)
    assert r["count"] == 1
    assert r["markets"][0]["question"].startswith("Will Bitcoin")


def test_polymarket_parses_json_encoded_price_fields(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": POLY_MIXED})
    r = pm.polymarket_crypto_markets(limit=10)
    m = r["markets"][0]
    assert m["prices"] == [0.62, 0.38]
    assert m["outcomes"] == ["Yes", "No"]
    assert m["volume"] == 125000.5
    assert m["url"] == "https://polymarket.com/event/btc-150k-2026"


def test_polymarket_propagates_error_honestly(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": {"error": "HTTP 503"}})
    r = pm.polymarket_crypto_markets()
    assert r["error"] == "HTTP 503"


def test_polymarket_handles_unexpected_shape(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": {"not": "a list"}})
    r = pm.polymarket_crypto_markets()
    assert "error" in r


def test_polymarket_prefers_parent_event_slug_for_grouped_markets(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": POLY_GROUPED})
    r = pm.polymarket_crypto_markets(limit=10)
    assert r["count"] == 1
    assert r["markets"][0]["url"] == "https://polymarket.com/event/fed-rate-decision-2026"


def test_polymarket_excludes_expired_markets(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": POLY_EXPIRED})
    r = pm.polymarket_crypto_markets(limit=10)
    assert r["count"] == 0


def test_is_expired():
    assert pm._is_expired("2020-01-01")
    assert not pm._is_expired("2099-01-01")
    assert not pm._is_expired(None)
    assert not pm._is_expired("not-a-date")


def test_kalshi_filters_to_crypto_relevant_only(monkeypatch):
    _patch(monkeypatch, {"api.elections.kalshi.com": KALSHI_MIXED})
    r = pm.kalshi_crypto_markets(limit=10)
    assert r["count"] == 1
    assert r["markets"][0]["id"] == "KXETHHACK-26JUL31-B1"
    assert r["markets"][0]["url"] == "https://kalshi.com/markets/kxethhack/kxethhack-26jul31"


def test_kalshi_propagates_error_honestly(monkeypatch):
    _patch(monkeypatch, {"api.elections.kalshi.com": {"error": "HTTP 500"}})
    r = pm.kalshi_crypto_markets()
    assert r["error"] == "HTTP 500"


def test_combined_merges_and_sorts_by_volume(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": POLY_MIXED, "api.elections.kalshi.com": KALSHI_MIXED})
    r = pm.crypto_prediction_markets(limit=10)
    assert r["count"] == 2
    assert r["sources"] == {"polymarket": "ok", "kalshi": "ok"}
    # polymarket's crypto market (125000.5 volume) outranks kalshi's (8000)
    assert r["markets"][0]["platform"] == "polymarket"
    assert r["markets"][1]["platform"] == "kalshi"


def test_combined_degrades_honestly_when_one_source_errors(monkeypatch):
    _patch(monkeypatch, {"gamma-api.polymarket.com": {"error": "HTTP 503"}, "api.elections.kalshi.com": KALSHI_MIXED})
    r = pm.crypto_prediction_markets(limit=10)
    assert r["count"] == 1
    assert r["markets"][0]["platform"] == "kalshi"
    assert r["sources"]["polymarket"] == "HTTP 503"
    assert r["sources"]["kalshi"] == "ok"


def test_is_crypto_relevant_matches_keywords():
    assert pm._is_crypto_relevant("Will Ethereum flip Bitcoin?")
    assert pm._is_crypto_relevant("Will a stablecoin depeg this month?")
    assert not pm._is_crypto_relevant("Who wins the Super Bowl?")
