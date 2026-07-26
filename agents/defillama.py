"""
VAPE's DefiLlama intelligence layer — the full open-API surface, in one module.

Powers three things off real DefiLlama data: investigation cross-checks (price
oracle + token age), the security/threat sweeps, and the market-data tool tier.

Design (matches agents/data_fetchers.py exactly): stdlib-only urllib, one cached
`_get`, every function returns real data or a `{"error": ...}` dict and NEVER
raises — so a caller can always degrade honestly rather than crash.

Hosts:
  api.llama.fi          TVL, protocols, chains, fees/revenue, dexs, treasury,
                        unlocks/emissions
  coins.llama.fi        prices (current/first/historical/% change) — the
                        multichain price oracle
  yields.llama.fi       yield pools + per-pool history
  stablecoins.llama.fi  stablecoin supply + peg
  bridges.llama.fi      bridge list (feeds threat work — bridge exploits are
                        a top attack class)

Note: DefiLlama moved overview/derivatives (and bridges' per-chain
`includeChains` detail) behind its Pro API tier — both were observed 402ing
in production. There is no free `derivatives` fetcher here anymore (the
offering was retired rather than sold undeliverable); `bridges()` below
drops `includeChains` to stay on the still-free list endpoint.

Live network is blocked from the dev sandbox (same as every llama.fi call in
this repo); real validation runs in GitHub Actions where these hosts are
reachable, exactly like the existing sweeps.
"""
import json
import time
import urllib.parse
import urllib.request
import urllib.error

# Reuse data_fetchers' cache + UA so DefiLlama traffic shares one disk cache and
# one identity, and we don't re-implement the HTTP plumbing. Fall back to a
# local minimal fetcher if data_fetchers can't be imported (keeps this module
# runnable stand-alone / in the worker-port test harness).
try:
    from agents.data_fetchers import _get, _now_iso, get_hack_feed  # noqa
except Exception:  # pragma: no cover
    _UA = {"User-Agent": "VAPE/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)"}

    def _now_iso():
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _get(url, ttl=600, cache_key=None, timeout=12):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "url": url}
        except Exception as e:
            return {"error": str(e), "url": url}

    def get_hack_feed(limit=8, chain=None):  # pragma: no cover
        return {"error": "hack feed unavailable in standalone mode"}

API = "https://api.llama.fi"
COINS = "https://coins.llama.fi"
YIELDS = "https://yields.llama.fi"
STABLE = "https://stablecoins.llama.fi"
BRIDGES = "https://bridges.llama.fi"


def _err(x):
    return isinstance(x, dict) and x.get("error")


def _coin_key(chain, address):
    """DefiLlama coin id: '{chain}:{address}' (chain slug, lowercased addr).
    DefiLlama uses its own chain slugs — 'base', 'ethereum', 'arbitrum'."""
    return f"{str(chain).lower()}:{str(address).lower()}"


# ── Prices — the multichain oracle (coins.llama.fi) ──────────────────────────
def token_price(chain, address):
    """Current DefiLlama price for a token by chain+address — an independent
    cross-check on DexScreener/CoinGecko. Returns {price, symbol, decimals,
    confidence, timestamp} or {error}. `confidence` (0-1) is DefiLlama's own
    price-reliability score — a real signal in itself (low confidence = thinly
    priced / unreliable)."""
    cid = _coin_key(chain, address)
    d = _get(f"{COINS}/prices/current/{urllib.parse.quote(cid)}", ttl=300, cache_key=f"dl_price_{cid}")
    if _err(d):
        return d
    coin = (d.get("coins") or {}).get(cid)
    if not coin:
        return {"error": "no price on DefiLlama", "coin": cid}
    return {"ts": _now_iso(), "chain": chain, "address": address, **coin}


def token_first_price(chain, address):
    """The FIRST price DefiLlama ever recorded for a token — an independent
    'how old is this really' signal (token age is already a scoring factor;
    this is a second, oracle-derived source for it, harder to spoof than a
    DEX pair-creation timestamp). Returns {price, symbol, timestamp, first_seen_iso}."""
    cid = _coin_key(chain, address)
    d = _get(f"{COINS}/prices/first/{urllib.parse.quote(cid)}", ttl=86400, cache_key=f"dl_first_{cid}")
    if _err(d):
        return d
    coin = (d.get("coins") or {}).get(cid)
    if not coin:
        return {"error": "no first-price on DefiLlama", "coin": cid}
    ts = coin.get("timestamp")
    out = {"ts": _now_iso(), "chain": chain, "address": address, **coin}
    if ts:
        out["first_seen_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
        out["age_days"] = round((time.time() - ts) / 86400, 1)
    return out


def token_price_chart(chain, address, span_days=30):
    """Historical price series for a token (for sparklines / volatility)."""
    cid = _coin_key(chain, address)
    period = "1d"
    start = int(time.time() - span_days * 86400)
    url = f"{COINS}/chart/{urllib.parse.quote(cid)}?start={start}&span={span_days}&period={period}"
    d = _get(url, ttl=1800, cache_key=f"dl_chart_{cid}_{span_days}")
    if _err(d):
        return d
    coin = (d.get("coins") or {}).get(cid) or {}
    return {"ts": _now_iso(), "chain": chain, "address": address,
            "symbol": coin.get("symbol"), "prices": coin.get("prices") or []}


# ── TVL / protocols / chains (api.llama.fi) ──────────────────────────────────
def protocol(slug):
    """Full protocol record: TVL history, per-chain TVL, category, url, logo,
    audits, and (when present) treasury/token fields. `logo` is a real hosted
    icon URL — rich data + logo, straight from source."""
    d = _get(f"{API}/protocol/{urllib.parse.quote(slug)}", ttl=1800, cache_key=f"dl_proto_{slug}")
    if _err(d):
        return d
    return {
        "ts": _now_iso(), "slug": slug, "name": d.get("name"), "logo": d.get("logo"),
        "category": d.get("category"), "url": d.get("url"), "chains": d.get("chains"),
        "tvl": (d.get("currentChainTvls") or {}),
        "audits": d.get("audits"), "audit_links": d.get("audit_links"),
        "twitter": d.get("twitter"), "description": d.get("description"),
    }


def protocols_on_chain(chain="Base", top_n=20):
    """Top protocols on a chain by TVL, each with its real logo, category and
    24h/7d change — the 'chain ecosystem' view."""
    d = _get(f"{API}/protocols", ttl=1800, cache_key="dl_protocols_all")
    if _err(d):
        return d
    rows = []
    for p in d if isinstance(d, list) else []:
        ctvl = (p.get("chainTvls") or {}).get(chain)
        if not ctvl or ctvl <= 0:
            continue
        rows.append({
            "name": p.get("name"), "slug": p.get("slug"), "logo": p.get("logo"),
            "category": p.get("category"), "tvl_usd": ctvl,
            "change_1d": p.get("change_1d"), "change_7d": p.get("change_7d"),
        })
    rows.sort(key=lambda r: r["tvl_usd"] or 0, reverse=True)
    return {"ts": _now_iso(), "chain": chain, "count": len(rows), "protocols": rows[:top_n]}


def chain_overview(chain="Base"):
    """One chain's headline TVL + rank among all chains (the 'chain ecosystem'
    snapshot's numeric core)."""
    d = _get(f"{API}/v2/chains", ttl=900, cache_key="dl_chains")
    if _err(d):
        return d
    chains = sorted((c for c in d if isinstance(c, dict)), key=lambda c: c.get("tvl") or 0, reverse=True)
    for i, c in enumerate(chains):
        if str(c.get("name", "")).lower() == chain.lower():
            return {"ts": _now_iso(), "chain": c.get("name"), "tvl_usd": c.get("tvl"),
                    "rank": i + 1, "total_chains": len(chains),
                    "token_symbol": c.get("tokenSymbol"), "gecko_id": c.get("gecko_id")}
    return {"error": f"chain not found: {chain}"}


# ── Fees & revenue (api.llama.fi/overview) ───────────────────────────────────
def protocol_fees(slug):
    """A protocol's real earned fees/revenue — 'does this thing actually make
    money, or is it just TVL parked?' A strong legitimacy signal raw TVL misses.
    Returns 24h/7d/30d/1y/all-time fees + revenue where DefiLlama tracks them —
    all-time in particular is the one figure that can't be reconstructed from
    the shorter windows (a protocol can have thin recent fees but a large
    lifetime total, or vice versa for a newly-ramping one)."""
    d = _get(f"{API}/summary/fees/{urllib.parse.quote(slug)}?dataType=dailyFees",
             ttl=3600, cache_key=f"dl_fees_{slug}")
    if _err(d):
        return d
    rev = _get(f"{API}/summary/fees/{urllib.parse.quote(slug)}?dataType=dailyRevenue",
               ttl=3600, cache_key=f"dl_rev_{slug}")
    out = {"ts": _now_iso(), "slug": slug, "name": d.get("name"), "logo": d.get("logo"),
           "fees_24h": d.get("total24h"), "fees_7d": d.get("total7d"), "fees_30d": d.get("total30d"),
           "fees_1y": d.get("total1y"), "fees_all_time": d.get("totalAllTime")}
    if not _err(rev):
        out.update({"revenue_24h": rev.get("total24h"), "revenue_7d": rev.get("total7d"),
                    "revenue_30d": rev.get("total30d"), "revenue_1y": rev.get("total1y"),
                    "revenue_all_time": rev.get("totalAllTime")})
    return out


def chain_fees(chain="base"):
    """All fee-earning protocols on a chain, ranked — the chain's real economic
    activity, not just parked capital."""
    url = (f"{API}/overview/fees/{urllib.parse.quote(chain)}"
           "?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true")
    d = _get(url, ttl=3600, cache_key=f"dl_chainfees_{chain}")
    if _err(d):
        return d
    protos = [{"name": p.get("name"), "logo": p.get("logo"), "category": p.get("category"),
               "fees_24h": p.get("total24h"), "fees_7d": p.get("total7d")}
              for p in (d.get("protocols") or [])]
    protos.sort(key=lambda p: p["fees_24h"] or 0, reverse=True)
    return {"ts": _now_iso(), "chain": chain, "total_fees_24h": d.get("total24h"),
            "total_fees_7d": d.get("total7d"), "protocols": protos[:20]}


def dex_volumes(chain="base"):
    """DEX trading volume on a chain, by venue — real trading activity."""
    url = (f"{API}/overview/dexs/{urllib.parse.quote(chain)}"
           "?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true")
    d = _get(url, ttl=3600, cache_key=f"dl_dexs_{chain}")
    if _err(d):
        return d
    protos = [{"name": p.get("name"), "logo": p.get("logo"),
               "vol_24h": p.get("total24h"), "vol_7d": p.get("total7d")}
              for p in (d.get("protocols") or [])]
    protos.sort(key=lambda p: p["vol_24h"] or 0, reverse=True)
    return {"ts": _now_iso(), "chain": chain, "total_vol_24h": d.get("total24h"),
            "dexs": protos[:20]}


# ── Yields (yields.llama.fi) ─────────────────────────────────────────────────
def yield_pools(chain=None, project=None, symbol=None, min_tvl=10000, limit=25):
    """Yield pools filtered by chain/project/symbol, ranked by TVL. Each pool:
    apy, apyBase, apyReward, tvlUsd, ilRisk, exposure — enough to tell a real
    yield venue from a trap (huge APY + tiny TVL + single-sided = red flag)."""
    d = _get(f"{YIELDS}/pools", ttl=1800, cache_key="dl_pools")
    if _err(d):
        return d
    rows = []
    for p in (d.get("data") or []):
        if chain and str(p.get("chain", "")).lower() != chain.lower():
            continue
        if project and project.lower() not in str(p.get("project", "")).lower():
            continue
        if symbol and symbol.lower() not in str(p.get("symbol", "")).lower():
            continue
        if (p.get("tvlUsd") or 0) < min_tvl:
            continue
        rows.append({
            "pool": p.get("pool"), "chain": p.get("chain"), "project": p.get("project"),
            "symbol": p.get("symbol"), "tvl_usd": p.get("tvlUsd"), "apy": p.get("apy"),
            "apy_base": p.get("apyBase"), "apy_reward": p.get("apyReward"),
            "il_risk": p.get("ilRisk"), "exposure": p.get("exposure"),
            "stablecoin": p.get("stablecoin"),
        })
    rows.sort(key=lambda r: r["tvl_usd"] or 0, reverse=True)
    return {"ts": _now_iso(), "count": len(rows), "pools": rows[:limit]}


# ── Stablecoins (stablecoins.llama.fi) ───────────────────────────────────────
def stablecoins(min_mcap=1e8, limit=25):
    """Stablecoins by circulating supply, with peg price — a de-pegging
    stablecoin is a live systemic threat signal."""
    d = _get(f"{STABLE}/stablecoins?includePrices=true", ttl=1800, cache_key="dl_stables")
    if _err(d):
        return d
    rows = []
    for s in (d.get("peggedAssets") or []):
        circ = ((s.get("circulating") or {}).get("peggedUSD")) or 0
        if circ < min_mcap:
            continue
        price = s.get("price")
        depeg = None
        if isinstance(price, (int, float)):
            depeg = round(abs(price - 1.0), 4)
        rows.append({"name": s.get("name"), "symbol": s.get("symbol"),
                     "circulating_usd": circ, "price": price, "depeg": depeg,
                     "peg_type": s.get("pegType"), "mechanism": s.get("pegMechanism")})
    rows.sort(key=lambda r: r["circulating_usd"] or 0, reverse=True)
    return {"ts": _now_iso(), "count": len(rows), "stablecoins": rows[:limit]}


# ── Bridges (bridges.llama.fi) — feeds threat work ───────────────────────────
def bridges(limit=25):
    """All tracked bridges with recent daily volume. Bridge exploits are one of
    the top attack categories (see security_sweep's ATTACK_PATTERNS); this is
    the flow data that category was missing a source for.

    Plain /bridges (list only) stays free; `includeChains=true` pulls the
    per-bridge chain breakdown, which DefiLlama now gates behind its Pro API
    (this call was observed 402ing in production with that param — see
    worker/src/lib/defillama.ts::bridges() for the parallel fix). Dropping it
    keeps this offering deliverable; `chains` is simply absent now.

    Real gap this closes (2026-07-26, direct user report: the live offering
    was shipping a bare "HTTP 402" as its entire $0.01 deliverable): the plain
    list endpoint above has ALSO started failing in production, on top of the
    known includeChains gate. Falls back to a real, always-free signal —
    recent bridge-category incidents from the same keyless hack feed
    security_sweep.py already uses — so "is bridge risk elevated right now"
    still gets a genuine answer instead of a raw upstream error string. Never
    raises (matches this module's law); the caller decides whether a
    still-error result should skip billing (see acp_fulfill.py's _bridges)."""
    d = _get(f"{BRIDGES}/bridges", ttl=1800, cache_key="dl_bridges")
    if not _err(d):
        rows = [{"id": b.get("id"), "name": b.get("displayName") or b.get("name"),
                 "chains": b.get("chains"), "last_daily_volume": b.get("lastDailyVolume"),
                 "weekly_volume": b.get("weeklyVolume")}
                for b in (d.get("bridges") or [])]
        rows.sort(key=lambda r: r["last_daily_volume"] or 0, reverse=True)
        return {"ts": _now_iso(), "count": len(rows), "bridges": rows[:limit]}

    feed = get_hack_feed(limit=50)
    bridge_incidents = [h for h in feed if "bridge" in str(h.get("technique") or "").lower()
                         or "bridge" in str(h.get("name") or "").lower()][:limit] \
        if isinstance(feed, list) else []
    if not bridge_incidents:
        return {"error": d.get("error", "bridge data unavailable"), "url": d.get("url")}
    return {"ts": _now_iso(), "count": len(bridge_incidents),
            "data_source": "bridge-exploit incident feed (bridge volume list unavailable this cycle)",
            "recent_bridge_incidents": bridge_incidents,
            "note": "Live bridge-volume ranking unavailable this cycle; showing recent bridge-category "
                    "exploit incidents instead as the nearer-term threat signal."}


def bridge_volume(chain="Base"):
    """Daily bridge in/out volume for a chain — a spike or a drain is a real
    capital-flow signal worth flagging."""
    d = _get(f"{BRIDGES}/bridgevolume/{urllib.parse.quote(chain)}", ttl=1800,
             cache_key=f"dl_bridgevol_{chain}")
    if _err(d):
        return d
    series = d if isinstance(d, list) else []
    latest = series[-1] if series else {}
    return {"ts": _now_iso(), "chain": chain,
            "latest_deposit_usd": latest.get("depositUSD"),
            "latest_withdraw_usd": latest.get("withdrawUSD"),
            "days": len(series)}


# ── Unlocks / emissions (api.llama.fi) ───────────────────────────────────────
def unlocks(slug):
    """Token unlock / emission schedule for a protocol — an imminent large
    unlock is a concrete dump-risk an investigator must flag. Returns the next
    upcoming unlock event and the total still-locked share where DefiLlama has
    it. Degrades honestly when a token isn't tracked.

    Real gap this closes (2026-07-26, direct user report: the live offering
    was shipping a bare "HTTP 402" as its entire $0.01 deliverable): DefiLlama
    moved this exact endpoint behind its $300/mo Pro API tier — confirmed via
    web search, not assumed — so it now 402s unconditionally on the free tier.
    Falls back to a circulating-vs-total-supply gap pulled from the protocol's
    own CoinGecko listing (via the gecko_id DefiLlama's own /protocol/{slug}
    already carries, no new provider) — a coarser but real and always-free
    future-dilution signal, honestly labeled as an estimate rather than an
    exact unlock date. Never raises (matches this module's law); the caller
    decides whether a still-error result should skip billing."""
    d = _get(f"{API}/emission/{urllib.parse.quote(slug)}", ttl=21600, cache_key=f"dl_emission_{slug}")
    if not _err(d):
        # Shape varies; surface the fields that exist without asserting a schema.
        events = d.get("events") or d.get("unlocks") or []
        now = time.time()
        upcoming = None
        best_ts = None
        # Scan every event and keep the EARLIEST future one — `events` isn't
        # guaranteed sorted (some payloads are newest-first), so stopping at
        # the first future item can surface a later unlock than the next.
        for e in events:
            ts = e.get("timestamp") or e.get("date")
            if isinstance(ts, (int, float)) and ts > now and (best_ts is None or ts < best_ts):
                best_ts = ts
                upcoming = {"timestamp": ts,
                            "in_days": round((ts - now) / 86400, 1),
                            "description": e.get("description") or e.get("category"),
                            "amount": e.get("noOfTokens") or e.get("amount")}
        return {"ts": _now_iso(), "slug": slug, "name": d.get("name"),
                "next_unlock": upcoming, "tracked_events": len(events)}

    proto = _get(f"{API}/protocol/{urllib.parse.quote(slug)}", ttl=1800, cache_key=f"dl_proto_{slug}")
    gecko_id = proto.get("gecko_id") if isinstance(proto, dict) else None
    if not gecko_id:
        return {"error": d.get("error", "unlock data unavailable"), "url": d.get("url")}
    cg = _get(f"https://api.coingecko.com/api/v3/coins/{urllib.parse.quote(gecko_id)}"
              f"?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false",
              ttl=3600, cache_key=f"cg_coin_{gecko_id}")
    m = (cg.get("market_data") or {}) if isinstance(cg, dict) else {}
    total = m.get("total_supply")
    circ = m.get("circulating_supply")
    if not (isinstance(total, (int, float)) and total > 0 and isinstance(circ, (int, float))):
        return {"error": d.get("error", "unlock data unavailable"), "url": d.get("url")}
    locked_pct = round((total - circ) / total * 100, 2)
    return {"ts": _now_iso(), "slug": slug, "name": proto.get("name"),
            "data_source": "supply-gap estimate (unlock calendar unavailable this cycle)",
            "circulating_supply": circ, "total_supply": total, "max_supply": m.get("max_supply"),
            "locked_supply_pct": locked_pct, "next_unlock": None, "tracked_events": 0,
            "note": "Exact next-unlock date unavailable this cycle; this is the gap between circulating "
                    "and total supply as a coarser future-dilution signal."}


# ── Treasury (api.llama.fi) ──────────────────────────────────────────────────
def treasury(slug):
    """A protocol's on-chain treasury holdings (own-token vs stables vs other) —
    a treasury that's ~all its own token is a fragility signal."""
    d = _get(f"{API}/treasury/{urllib.parse.quote(slug)}", ttl=21600, cache_key=f"dl_treasury_{slug}")
    if _err(d):
        return d
    tvls = d.get("currentChainTvls") or {}
    own = tvls.get("OwnTokens") or tvls.get("ownTokens") or 0
    # currentChainTvls mixes per-chain totals (e.g. "ethereum", which already
    # includes that chain's own tokens) with own-token breakdowns — an
    # aggregate "OwnTokens" plus per-chain "<chain>-OwnTokens". Summing every
    # numeric value double-counts the own-token bucket, inflating treasury_usd
    # and skewing own_token_share. Sum only the plain per-chain totals.
    total = sum(v for k, v in tvls.items()
                if isinstance(v, (int, float))
                and k not in ("OwnTokens", "ownTokens")
                and not k.endswith("-OwnTokens"))
    return {"ts": _now_iso(), "slug": slug, "name": d.get("name"),
            "treasury_usd": round(total, 2), "own_token_usd": round(own, 2),
            "own_token_share": round(own / total, 3) if total else None}


# ── Convenience: everything DefiLlama knows about one token, for investigate ──
def token_intel(chain, address, protocol_slug=None):
    """One call that assembles DefiLlama's full picture of a token for the
    investigation pipeline: current price + confidence, first-seen age, and
    (when a protocol slug is known) fees/revenue, unlocks, and treasury. Every
    sub-fetch degrades independently — a missing piece never sinks the rest."""
    out = {"ts": _now_iso(), "chain": chain, "address": address}
    price = token_price(chain, address)
    out["price"] = price if not _err(price) else None
    first = token_first_price(chain, address)
    out["first_price"] = first if not _err(first) else None
    if protocol_slug:
        for name, fn in (("fees", protocol_fees), ("unlocks", unlocks), ("treasury", treasury)):
            r = fn(protocol_slug)
            out[name] = r if not _err(r) else None
    return out
