"""
VAPE's Codex.io intelligence layer — real-time, enriched on-chain data via
Codex's GraphQL API (graph.codex.io/graphql): token discovery/trending,
holders, wallet PnL, and launchpad activity across 80+ networks.

Design (matches agents/defillama.py / agents/data_fetchers.py): one cached
POST helper, every function returns real data or a `{"error": ...}` dict and
NEVER raises — so a caller always degrades honestly rather than crashing.
Unlike DefiLlama, Codex requires an API key (CODEX_API_KEY) and is a paid
service with a free tier — `_query()` enforces a conservative, overridable
daily request cap (CODEX_DAILY_REQUEST_CAP, default 500) so a bug or a
tight polling loop can't quietly blow through free-tier quota; requests
past the cap return `{"error": "daily_request_cap_reached", ...}` rather
than firing.

Query field names below are sourced from Codex's public SDK examples
(github.com/Codex-Data/sdk) and docs.codex.io/agents/codex-skills — live
network is blocked from this dev sandbox (same as every other external API
in this repo), so exact schema shapes should be spot-checked against a real
response the first time each function actually runs in GitHub Actions,
exactly like the existing sweeps.

Confirmed gaps (as of this module's introduction):
- Prediction markets (Polymarket/Kalshi) are beta-gated to Codex's paid
  Growth/Enterprise plans — not reachable on a free-tier key. VAPE sources
  prediction-market data straight from Polymarket's own free, keyless
  Gamma API instead (see agents/prediction_markets.py), not through Codex.
- Launchpad new-token tracking is exposed via Codex as a GraphQL
  *subscription* (onLaunchpadTokenEvent/Batch), not a plain query — this
  stdlib-urllib client can't hold a WebSocket open the way a cron-style
  agent run needs to. `new_launchpad_tokens()` is a placeholder that
  returns `{"error": "requires_websocket_subscription", ...}` until a
  poll-friendly query is confirmed against Codex's real schema.
"""
import json
import os
import time
import urllib.request
import urllib.error

try:
    from agents.data_fetchers import _cache_get, _cache_put, _now_iso  # noqa
except Exception:  # pragma: no cover
    def _now_iso():
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _cache_get(key, ttl):
        return None

    def _cache_put(key, value):
        return value

GRAPHQL_URL = "https://graph.codex.io/graphql"
UA = {"User-Agent": "VAPE-PrivateEye/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)"}

API_KEY = os.getenv("CODEX_API_KEY", "")
DEFAULT_DAILY_REQUEST_CAP = 500
_request_count = {"date": None, "count": 0}


def _daily_request_cap():
    """Read CODEX_DAILY_REQUEST_CAP fresh on each call (same pattern as
    agents/llm.py's *_daily_spend_cap() helpers) so it can be tuned without
    a redeploy."""
    try:
        return int(os.getenv("CODEX_DAILY_REQUEST_CAP", DEFAULT_DAILY_REQUEST_CAP))
    except (TypeError, ValueError):
        return DEFAULT_DAILY_REQUEST_CAP


def _over_daily_cap():
    """`_request_count` is in-memory, but agents/codex_data.py is invoked as a
    fresh process per run (cron/GitHub Actions) — an in-memory-only counter
    would silently reset to 0 every run and never actually bound usage across
    a real day. Persist the running count on the same disk cache every other
    fetcher here already uses, keyed by date, so the cap holds across
    restarts."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if _request_count["date"] != today:
        _request_count["date"] = today
        persisted = _cache_get(f"codex_daily_count_{today}", 90000)
        _request_count["count"] = persisted if isinstance(persisted, int) else 0
    return _request_count["count"] >= _daily_request_cap()


def _err(x):
    return isinstance(x, dict) and x.get("error")


def _query(query, variables=None, ttl=300, cache_key=None, timeout=15):
    """POST a GraphQL query to Codex, cached on disk like every other
    fetcher in this repo. Returns the `data` object on success, or
    `{"error": ...}` — never raises."""
    if not API_KEY:
        return {"error": "no_key", "note": "set CODEX_API_KEY for Codex.io data"}
    key = cache_key or (query + json.dumps(variables or {}, sort_keys=True))
    cached = _cache_get(key, ttl)
    if cached is not None:
        return cached
    if _over_daily_cap():
        return {"error": "daily_request_cap_reached",
                "note": f"CODEX_DAILY_REQUEST_CAP ({_daily_request_cap()}) hit for today — "
                        "raise the env var if the free-tier plan actually allows more"}
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    try:
        req = urllib.request.Request(
            GRAPHQL_URL, data=payload,
            headers={**UA, "Content-Type": "application/json", "Authorization": API_KEY})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode())
        _request_count["count"] += 1
        _cache_put(f"codex_daily_count_{_request_count['date']}", _request_count["count"])
        if body.get("errors"):
            return {"error": "; ".join(e.get("message", str(e)) for e in body["errors"])}
        return _cache_put(key, body.get("data") or {})
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "url": GRAPHQL_URL}
    except Exception as e:
        return {"error": str(e)}


# ── Token discovery / trending (filterTokens) ────────────────────────────────
def trending_tokens(network_ids=None, limit=20):
    """Top tokens ranked by Codex's own trending/volume signal — real
    discovery data, not a hand-picked watchlist. `network_ids` optionally
    scopes to specific chain ids (Codex's own numeric network ids, e.g. 8453
    for Base); omit for cross-chain trending."""
    query = """
    query TrendingTokens($limit: Int!, $networkFilter: [Int!]) {
      filterTokens(limit: $limit, filters: {network: $networkFilter}) {
        results {
          priceUSD
          volume24
          liquidity
          marketCap
          change24
          token { name symbol address networkId }
        }
      }
    }"""
    d = _query(query, {"limit": limit, "networkFilter": network_ids},
               ttl=180, cache_key=f"codex_trending_{network_ids}_{limit}")
    if _err(d):
        return d
    results = ((d.get("filterTokens") or {}).get("results")) or []
    return {"ts": _now_iso(), "tokens": results}


# ── Holders (rug-risk / concentration signal) ────────────────────────────────
def token_holders(token_id, network_id, limit=10):
    """Top holders for a token by balance, plus the percent of supply held
    by the top 10 wallets — a fast rug-risk/concentration signal. `token_id`
    is the token contract address."""
    query = """
    query TokenHolders($input: HoldersInput!) {
      holders(input: $input) {
        count
        top10HoldersPercent
        items { address balance }
      }
    }"""
    d = _query(query, {"input": {"tokenId": token_id, "networkId": network_id, "limit": limit}},
               ttl=900, cache_key=f"codex_holders_{network_id}_{token_id}_{limit}")
    if _err(d):
        return d
    h = d.get("holders") or {}
    return {"ts": _now_iso(), "token_id": token_id, "count": h.get("count"),
            "top10_holders_pct": h.get("top10HoldersPercent"), "items": h.get("items") or []}


# ── Wallet balances + PnL (feeds the paid wallet deep-dive offering) ─────────
def wallet_balances(wallet_address, network_ids=None):
    """Current token balances (with USD values) for a wallet across the
    given networks — the "what do they hold right now" half of a wallet
    deep-dive; pair with wallet_pnl_stats() for the "how did they do" half."""
    query = """
    query WalletBalances($wallet: String!, $networks: [Int!]) {
      balances(input: {walletAddress: $wallet, networks: $networks, includeNative: true, removeScams: true, limit: 100}) {
        items { shiftedBalance balanceUsd token { name symbol networkId } }
      }
    }"""
    d = _query(query, {"wallet": wallet_address, "networks": network_ids},
               ttl=120, cache_key=f"codex_bal_{wallet_address}_{network_ids}")
    if _err(d):
        return d
    return {"ts": _now_iso(), "wallet": wallet_address,
            "items": ((d.get("balances") or {}).get("items")) or []}


def wallet_pnl_stats(wallet_address, network_id):
    """Aggregate realized P&L for a wallet — the headline numbers for the
    $0.25 wallet deep-dive offering, sourced straight from Codex instead of
    VAPE reconstructing a trade ledger from raw transfers itself."""
    query = """
    query WalletStats($wallet: String!, $networkId: Int!) {
      detailedWalletStats(input: {walletAddress: $wallet, networkId: $networkId}) {
        statsUsd { realizedProfitUsd realizedProfitPercentage volume tokensTraded }
      }
    }"""
    d = _query(query, {"wallet": wallet_address, "networkId": network_id},
               ttl=300, cache_key=f"codex_pnl_{wallet_address}_{network_id}")
    if _err(d):
        return d
    stats = (d.get("detailedWalletStats") or {}).get("statsUsd") or {}
    return {"ts": _now_iso(), "wallet": wallet_address, "network_id": network_id,
            "realized_profit_usd": stats.get("realizedProfitUsd"),
            "realized_profit_pct": stats.get("realizedProfitPercentage"),
            "volume_usd": stats.get("volume"), "tokens_traded": stats.get("tokensTraded")}


def wallet_pnl_chart(wallet_address, network_id, resolution="1D"):
    """Time-series realized-P&L progression for a wallet — feeds a P&L
    chart in the deep-dive report/PDF, same range-selector idea as every
    other chart on the site."""
    query = """
    query WalletChart($wallet: String!, $networkId: Int!, $resolution: String!) {
      walletChart(input: {walletAddress: $wallet, networkId: $networkId, resolution: $resolution}) {
        points { timestamp realizedProfitUsd }
      }
    }"""
    d = _query(query, {"wallet": wallet_address, "networkId": network_id, "resolution": resolution},
               ttl=300, cache_key=f"codex_pnlchart_{wallet_address}_{network_id}_{resolution}")
    if _err(d):
        return d
    return {"ts": _now_iso(), "wallet": wallet_address,
            "points": ((d.get("walletChart") or {}).get("points")) or []}


# ── Launchpad (new token launches) ───────────────────────────────────────────
def new_launchpad_tokens(*_args, **_kwargs):
    """Codex exposes launchpad token creation/graduation events as a
    GraphQL *subscription* (onLaunchpadTokenEvent / onLaunchpadTokenEventBatch),
    not a plain request/response query — this stdlib-urllib client has no
    WebSocket support, and a cron-style agent run can't hold a subscription
    open between runs anyway. Left as an explicit, honest placeholder rather
    than a fabricated query name; needs a real schema check (a poll-friendly
    query, if Codex has one) before this can return real data."""
    return {"error": "requires_websocket_subscription",
            "note": "Codex launchpad events are subscription-only (onLaunchpadTokenEvent"
                    "/onLaunchpadTokenEventBatch) — see this function's docstring."}
