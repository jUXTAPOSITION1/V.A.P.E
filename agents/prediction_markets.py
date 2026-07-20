"""
VAPE's prediction-markets intelligence layer — real crypto/Base-relevant
prediction-market odds from Polymarket's free, keyless Gamma API and
Kalshi's free, keyless markets API.

Scope is deliberately narrow: crypto/Base-ecosystem-relevant markets only
(keyword-filtered from each platform's full active-market list), not general
politics/sports/macro markets — this stays a security/intel signal (market-
implied odds on hacks, depegs, price thresholds, protocol milestones) rather
than turning into a general betting-odds aggregator that doesn't fit VAPE's
brand.

Design (matches agents/defillama.py exactly): reuse data_fetchers' cached
`_get` + `_now_iso` so this traffic shares one disk cache and one UA identity;
every function returns real data or a `{"error": ...}` dict and NEVER raises,
so a caller always degrades honestly rather than crashing or fabricating.

Live network is blocked from this dev sandbox (same constraint as every other
external API in this repo) — field names below are sourced from Polymarket's
and Kalshi's public API docs, not independently verified against a live
response; spot-check the first real response in production, exactly like the
existing sweeps.

Codex.io's own prediction-market data is beta-gated to paid Growth/Enterprise
plans (see agents/codex_data.py's module docstring) — not reachable on a
free-tier key, hence going straight to Polymarket/Kalshi instead.
"""
import json
import re
import time
from datetime import datetime, timezone

try:
    from agents.data_fetchers import _get, _now_iso  # noqa
except Exception:  # pragma: no cover
    import urllib.request
    import urllib.error

    _UA = {"User-Agent": "VAPE/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)"}

    def _now_iso():
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _get(url, ttl=120, cache_key=None, timeout=12):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "url": url}
        except Exception as e:
            return {"error": str(e), "url": url}

POLYMARKET_GAMMA = "https://gamma-api.polymarket.com"
# api.kalshi.com is a mirror of the same host — api.elections.kalshi.com is
# Kalshi's current documented public host; trading-api.kalshi.com (used here
# previously) is legacy and no longer reliable.
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"

# Crypto/Base-ecosystem relevance filter, applied to each market's own
# question/title text — deliberately keyword-based rather than relying on
# either platform's internal category/tag taxonomy, since that taxonomy
# can't be confirmed from this sandbox and a wrong tag ID would silently
# return zero markets instead of an honest error.
_CRYPTO_RE = re.compile(
    r"\b(crypto|bitcoin|btc|ethereum|eth|base|solana|\bsol\b|xrp|defi|"
    r"stablecoin|usdc|usdt|coinbase|binance|token|blockchain|web3|nft|"
    r"altcoin|memecoin|hack|exploit|rug ?pull|depeg)\b",
    re.IGNORECASE,
)


def _err(x):
    return isinstance(x, dict) and x.get("error")


def _is_crypto_relevant(*texts):
    return any(t and _CRYPTO_RE.search(str(t)) for t in texts)


def _is_expired(end_date):
    """True only if end_date parses AND is clearly in the past — Polymarket's
    active=true&closed=false filter leaves resolved-but-not-yet-closed markets
    in the list past their real end date, which read as "outdated" on the
    site. Never excludes on a parse failure — an unparseable date is not
    evidence the market is stale."""
    if not end_date:
        return False
    try:
        dt = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt < datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


def _parse_json_field(v):
    """Polymarket's Gamma API returns some array fields (outcomes,
    outcomePrices) as JSON-encoded strings rather than real JSON arrays —
    decode defensively, None on anything unexpected rather than raising."""
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (TypeError, ValueError):
            return None
    return None


def polymarket_crypto_markets(limit=20):
    """Active Polymarket markets, keyword-filtered to crypto/Base relevance.
    Real data or an honest {error} — never fabricated, never raises."""
    d = _get(f"{POLYMARKET_GAMMA}/markets?active=true&closed=false&limit=200"
             "&order=volume&ascending=false",
             ttl=120, cache_key="pm_gamma_active_markets")
    if _err(d):
        return d
    if not isinstance(d, list):
        return {"error": "unexpected response shape (expected a list)"}
    out = []
    for m in d:
        question = m.get("question") or m.get("title") or ""
        if not _is_crypto_relevant(question, m.get("category")):
            continue
        end_date = m.get("endDate")
        if _is_expired(end_date):
            continue
        prices = _parse_json_field(m.get("outcomePrices"))
        outcomes = _parse_json_field(m.get("outcomes"))
        try:
            prices = [float(p) for p in prices] if prices else None
        except (TypeError, ValueError):
            prices = None
        # A market's own slug is only a valid /event/ path for single-outcome
        # events; grouped/multi-outcome markets need the parent event's slug
        # (the market's `events` array) or the link 404s.
        events = m.get("events") or []
        event_slug = events[0].get("slug") if events and isinstance(events[0], dict) else None
        slug = event_slug or m.get("slug")
        out.append({
            "platform": "polymarket",
            "id": m.get("id"),
            "question": question,
            "outcomes": outcomes,
            "prices": prices,
            "volume": _to_float(m.get("volume")),
            "liquidity": _to_float(m.get("liquidity")),
            "end_date": end_date,
            "url": f"https://polymarket.com/event/{slug}" if slug else None,
        })
        if len(out) >= limit:
            break
    return {"ts": _now_iso(), "count": len(out), "markets": out}


def kalshi_crypto_markets(limit=20):
    """Active Kalshi markets, keyword-filtered to crypto/Base relevance.
    Real data or an honest {error} — never fabricated, never raises."""
    d = _get(f"{KALSHI_API}/markets?status=open&limit=200",
             ttl=120, cache_key="kalshi_open_markets")
    if _err(d):
        return d
    markets = d.get("markets") if isinstance(d, dict) else None
    if markets is None:
        return {"error": "unexpected response shape (expected a 'markets' list)"}
    out = []
    for m in markets:
        title = m.get("title") or m.get("subtitle") or ""
        if not _is_crypto_relevant(title):
            continue
        # Kalshi's site URLs are /markets/{series_ticker}/{event_ticker}
        # (lowercased) — the full per-strike market ticker (e.g.
        # "KXBTCD-25JUL19-B50000") never appears in the path on its own.
        series_ticker = m.get("series_ticker")
        event_ticker = m.get("event_ticker")
        url = (f"https://kalshi.com/markets/{series_ticker.lower()}/{event_ticker.lower()}"
               if series_ticker and event_ticker else None)
        out.append({
            "platform": "kalshi",
            "id": m.get("ticker"),
            "question": title,
            "yes_bid_cents": m.get("yes_bid"),
            "yes_ask_cents": m.get("yes_ask"),
            "volume": _to_float(m.get("volume")),
            "end_date": m.get("close_time"),
            "url": url,
        })
        if len(out) >= limit:
            break
    return {"ts": _now_iso(), "count": len(out), "markets": out}


def _to_float(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def crypto_prediction_markets(limit=20):
    """Combined crypto/Base-relevant prediction markets from both platforms,
    ranked by volume. Each source is independent — one platform erroring
    doesn't sink the other, same honest-partial-degradation pattern as
    Promise.allSettled elsewhere in this repo (e.g. app.js's virtuals())."""
    pm = polymarket_crypto_markets(limit)
    kl = kalshi_crypto_markets(limit)
    markets = []
    if not _err(pm):
        markets.extend(pm.get("markets", []))
    if not _err(kl):
        markets.extend(kl.get("markets", []))
    markets.sort(key=lambda m: m.get("volume") or 0, reverse=True)
    return {
        "ts": _now_iso(),
        "count": len(markets),
        "markets": markets[:limit],
        "sources": {
            "polymarket": "ok" if not _err(pm) else pm["error"],
            "kalshi": "ok" if not _err(kl) else kl["error"],
        },
    }
