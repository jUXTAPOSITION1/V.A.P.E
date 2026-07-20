"""Tests for agents/codex_data.py — the Codex.io GraphQL client's PARSING and
rate-limit logic. Live graph.codex.io is unreachable from CI's/dev's sandbox
(same as every external API in this repo), so these tests monkeypatch the
module's `_query` to return realistic Codex response shapes and assert the
parsing/degradation is correct, plus exercise the no-key and daily-cap paths
directly (the parts that are actually VAPE's code, not Codex's uptime).
"""
import agents.codex_data as cd


def _patch(monkeypatch, payload):
    monkeypatch.setattr(cd, "_query", lambda *a, **k: payload)


def test_trending_tokens_parses(monkeypatch):
    _patch(monkeypatch, {"filterTokens": {"results": [
        {"priceUSD": 1.5, "volume24": 900000, "token": {"name": "Foo", "symbol": "FOO"}},
    ]}})
    r = cd.trending_tokens(limit=20)
    assert r["tokens"][0]["token"]["symbol"] == "FOO"


def test_trending_tokens_propagates_error(monkeypatch):
    _patch(monkeypatch, {"error": "HTTP 500"})
    assert cd.trending_tokens().get("error") == "HTTP 500"


def test_trending_tokens_handles_empty_results(monkeypatch):
    _patch(monkeypatch, {"filterTokens": {"results": []}})
    r = cd.trending_tokens()
    assert r["tokens"] == []


def test_token_holders_parses(monkeypatch):
    _patch(monkeypatch, {"holders": {"count": 500, "top10HoldersPercent": 42.5,
                                      "items": [{"address": "0xabc", "balance": "100"}]}})
    r = cd.token_holders("0xToken", 8453)
    assert r["top10_holders_pct"] == 42.5
    assert r["count"] == 500
    assert r["items"][0]["address"] == "0xabc"


def test_token_holders_sends_composite_token_id(monkeypatch):
    # HoldersInput.tokenId is "address:networkId" — there's no separate
    # networkId field on this input, unlike DetailedWalletStatsInput.
    calls = []

    def fake_query(query, variables, **kwargs):
        calls.append(variables)
        return {"holders": {}}

    monkeypatch.setattr(cd, "_query", fake_query)
    cd.token_holders("0xToken", 8453)
    assert calls[0]["input"]["tokenId"] == "0xToken:8453"
    assert "networkId" not in calls[0]["input"]


def test_wallet_balances_parses(monkeypatch):
    _patch(monkeypatch, {"balances": {"items": [
        {"shiftedBalance": 12.3, "balanceUsd": 45.6, "token": {"symbol": "AERO", "networkId": 8453}},
    ]}})
    r = cd.wallet_balances("0xWallet")
    assert r["items"][0]["balanceUsd"] == 45.6


def test_wallet_pnl_stats_parses(monkeypatch):
    _patch(monkeypatch, {"detailedWalletStats": {"statsUsd": {
        "realizedProfitUsd": 1234.5, "realizedProfitPercentage": 12.3,
        "volume": 50000, "tokensTraded": 7}}})
    r = cd.wallet_pnl_stats("0xWallet", 8453)
    assert r["realized_profit_usd"] == 1234.5
    assert r["tokens_traded"] == 7


def test_wallet_pnl_stats_missing_fields_stays_honest(monkeypatch):
    _patch(monkeypatch, {"detailedWalletStats": {"statsUsd": {}}})
    r = cd.wallet_pnl_stats("0xWallet", 8453)
    assert r["realized_profit_usd"] is None


def test_wallet_pnl_chart_parses(monkeypatch):
    _patch(monkeypatch, {"walletChart": {"points": [
        {"timestamp": 1720000000, "realizedProfitUsd": 100.0},
        {"timestamp": 1720086400, "realizedProfitUsd": 150.0},
    ]}})
    r = cd.wallet_pnl_chart("0xWallet", 8453)
    assert len(r["points"]) == 2
    assert r["points"][1]["realizedProfitUsd"] == 150.0


def test_new_launchpad_tokens_parses(monkeypatch):
    _patch(monkeypatch, {"filterTokens": {"results": [
        {"priceUSD": 0.002, "volume24": 5000, "createdAt": 1720000000,
         "token": {"name": "Fresh", "symbol": "FRESH"}},
    ]}})
    r = cd.new_launchpad_tokens()
    assert r["tokens"][0]["token"]["symbol"] == "FRESH"


def test_new_launchpad_tokens_propagates_error(monkeypatch):
    _patch(monkeypatch, {"error": "HTTP 500"})
    assert cd.new_launchpad_tokens().get("error") == "HTTP 500"


def test_token_bars_parses(monkeypatch):
    _patch(monkeypatch, {"getBars": {
        "t": [1720000000, 1720086400],
        "o": [1.0, 1.1], "h": [1.2, 1.3], "l": [0.9, 1.0], "c": [1.1, 1.2], "v": [1000, 2000],
    }})
    r = cd.token_bars("0xToken", 8453)
    assert len(r["points"]) == 2
    assert r["points"][1]["c"] == 1.2


def test_token_bars_propagates_error(monkeypatch):
    _patch(monkeypatch, {"error": "HTTP 500"})
    assert cd.token_bars("0xToken", 8453).get("error") == "HTTP 500"


def test_query_without_api_key_returns_no_key_error(monkeypatch):
    monkeypatch.setattr(cd, "API_KEY", "")
    assert cd._query("query { x }").get("error") == "no_key"


def test_query_respects_daily_request_cap(monkeypatch):
    monkeypatch.setattr(cd, "API_KEY", "fake-key-for-test")
    monkeypatch.setattr(cd, "_cache_get", lambda *a, **k: None)
    monkeypatch.setenv("CODEX_DAILY_REQUEST_CAP", "1")
    cd._request_count["date"] = None  # force a fresh day so the test is deterministic
    called = {"n": 0}

    def fake_urlopen(*a, **k):
        called["n"] += 1
        raise AssertionError("should not reach the network past the cap")

    # First call is allowed through (count starts at 0 < cap of 1) but we don't
    # want to hit real urllib either — simulate a successful response once,
    # then confirm the second call is rejected before any network attempt.
    import json as _json
    from io import BytesIO

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return _json.dumps({"data": {"ok": True}}).encode()

    monkeypatch.setattr(cd.urllib.request, "urlopen", lambda *a, **k: _Resp())
    first = cd._query("query { x }", cache_key="cap-test-1")
    assert first.get("ok") is True

    monkeypatch.setattr(cd.urllib.request, "urlopen", fake_urlopen)
    second = cd._query("query { x }", cache_key="cap-test-2")
    assert second.get("error") == "daily_request_cap_reached"
    assert called["n"] == 0
