"""
V.A.P.E. real-data fetchers — keyless public sources, file-cached, compute-free.

Every function returns a plain dict/list (JSON-safe) for feeding into ask_llm().
All network failures degrade gracefully to {"error": ...} so a report still renders.
A small on-disk TTL cache (data/cache/) respects rate limits and avoids redundant
calls across hourly CI runs.

Sources (all free; key OPTIONAL only for BaseScan account endpoints):
  - DefiLlama    TVL / chains / protocols / stablecoins / yields   (no key)
  - Base JSON-RPC eth_blockNumber / gasPrice / block activity      (no key)
  - CoinGecko    simple price / token market data                  (no key)
  - BaseScan     contract source / account txs / token transfers   (key optional)
"""
import json
import os
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ── config ────────────────────────────────────────────────────────────────────
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cache")
DEFAULT_TTL = 600          # 10 min — market data doesn't need finer granularity hourly
RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
BASESCAN_KEY = os.getenv("ETHERSCAN_API_KEY", "")   # Etherscan V2 multichain key (chainid 8453)
ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"
UA = {"User-Agent": "VAPE-PrivateEye/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)"}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── tiny file cache ───────────────────────────────────────────────────────────
def _cache_path(key):
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:120]
    return os.path.join(CACHE_DIR, safe + ".json")


def _cache_get(key, ttl):
    p = _cache_path(key)
    try:
        if os.path.exists(p) and (time.time() - os.path.getmtime(p)) < ttl:
            with open(p) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _cache_put(key, value):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(_cache_path(key), "w") as f:
            json.dump(value, f)
    except Exception:
        pass
    return value


# ── http helpers (stdlib only — no extra deps) ────────────────────────────────
def _get(url, ttl=DEFAULT_TTL, cache_key=None, timeout=12):
    key = cache_key or url
    cached = _cache_get(key, ttl)
    if cached is not None:
        return cached
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return _cache_put(key, data)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


def _post_rpc(method, params, timeout=12):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    try:
        req = urllib.request.Request(RPC_URL, data=payload,
                                     headers={**UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


# ── 1. DefiLlama: TVL / flows / anomaly signal ────────────────────────────────
def get_base_tvl_and_protocols(top_n=10):
    """Base chain TVL + 24h/7d change + top protocols by TVL, plus the
    derived signals a raw protocol list can't show on its own: each top
    protocol's real share of total Base TVL, a category breakdown across
    EVERY real Base protocol (not just the top_n slice, so "where the money
    actually is" isn't skewed by the cutoff), and a concentration-risk read
    off the top-3 share. All computed from fields DefiLlama's own
    /protocols response already carries — no new fetch. Keyless."""
    chains = _get("https://api.llama.fi/v2/chains", ttl=900, cache_key="llama_chains")
    if isinstance(chains, dict) and chains.get("error"):
        return chains
    base = next((c for c in chains if str(c.get("name", "")).lower() == "base"), None)
    if not base:
        return {"error": "Base chain not found in DefiLlama"}
    tvl_usd = base.get("tvl")
    change_1d, change_7d = base.get("change_1d"), base.get("change_7d")
    tvl_change_source = "llama_chains"
    if change_1d is None or change_7d is None:
        # /v2/chains has stopped populating change_1d/change_7d for Base —
        # fall back to the historical chain-TVL series (still reliable,
        # clean daily points) and derive the same deltas ourselves.
        fb_1d, fb_7d = _base_historical_tvl_deltas()
        change_1d = change_1d if change_1d is not None else fb_1d
        change_7d = change_7d if change_7d is not None else fb_7d
        tvl_change_source = "historical_fallback"
    out = {
        "ts": _now_iso(),
        "tvl_usd": tvl_usd,
        "tvl_24h_change_pct": change_1d,
        "tvl_7d_change_pct": change_7d,
        "tvl_change_source": tvl_change_source,
    }
    protos = _get("https://api.llama.fi/protocols", ttl=1800, cache_key="llama_protocols")
    if isinstance(protos, list):
        def base_tvl(p):
            ct = p.get("chainTvls") or {}
            v = ct.get("Base") if isinstance(ct, dict) else None
            return v if isinstance(v, (int, float)) else 0
        # real DeFi protocols deployed on Base (exclude CEX/bridge custody entries)
        base_protos = [p for p in protos
                       if "Base" in (p.get("chains") or [])
                       and (p.get("category") or "") not in ("CEX",)
                       and base_tvl(p) > 0]
        base_protos.sort(key=base_tvl, reverse=True)

        def share_pct(v):
            return round(v / tvl_usd * 100, 2) if isinstance(tvl_usd, (int, float)) and tvl_usd else None

        top = base_protos[:top_n]
        out["top_protocols"] = [
            {"name": p.get("name"), "base_tvl_usd": base_tvl(p),
             "share_of_base_pct": share_pct(base_tvl(p)),
             "change_1d": p.get("change_1d"), "change_7d": p.get("change_7d"),
             "change_1m": p.get("change_1m"), "category": p.get("category")}
            for p in top
        ]

        # Category breakdown over ALL real Base protocols (not just top_n) —
        # a top_n-only view would misrepresent "where the money is" once
        # smaller protocols in an under-represented category are cut off.
        cat_totals = {}
        for p in base_protos:
            cat = p.get("category") or "Other"
            cat_totals[cat] = cat_totals.get(cat, 0) + base_tvl(p)
        if isinstance(tvl_usd, (int, float)) and tvl_usd:
            out["category_breakdown_pct"] = {
                cat: round(v / tvl_usd * 100, 2)
                for cat, v in sorted(cat_totals.items(), key=lambda kv: kv[1], reverse=True)
            }

        # Concentration risk — top-3 share of total TVL. Thresholds match
        # this codebase's existing rule-based severity framing elsewhere
        # (score()'s penalty tiers), not an arbitrary new scale.
        top3_share = sum(share_pct(base_tvl(p)) or 0 for p in top[:3])
        if top3_share >= 60:
            level = "HIGH"
        elif top3_share >= 40:
            level = "MEDIUM"
        else:
            level = "LOW"
        out["concentration_risk"] = f"{level} — top 3 protocols hold {top3_share:.1f}% of Base TVL"

        # Real 24h movers among the top_n set only (a protocol outside the
        # top_n has no business being called a "top gainer/loser" here).
        movers = [p for p in top if isinstance(p.get("change_1d"), (int, float))]
        gainers = sorted((p for p in movers if p["change_1d"] > 0), key=lambda p: p["change_1d"], reverse=True)
        losers = sorted((p for p in movers if p["change_1d"] < 0), key=lambda p: p["change_1d"])
        out["top_gainers_24h"] = [{"name": p["name"], "change_1d": p["change_1d"]} for p in gainers[:3]]
        out["top_losers_24h"] = [{"name": p["name"], "change_1d": p["change_1d"]} for p in losers[:3]]
    return out


def _base_historical_tvl_deltas():
    """Fallback 1d/7d TVL % change for Base, derived from DefiLlama's
    historical chain-TVL series (a separate endpoint from /v2/chains, still
    returning clean daily points as of Aug 2026 even though /v2/chains'
    own change_1d/change_7d fields have gone null for Base). Same
    closest-point-to-target-timestamp technique already used for the
    Virtuals TVL trend in get_virtuals_snapshot(). Returns (None, None) on
    any failure so the caller can leave the field blank rather than crash."""
    hist = _get("https://api.llama.fi/v2/historicalChainTvl/Base",
                ttl=1800, cache_key="llama_base_hist_tvl")
    if not isinstance(hist, list) or len(hist) < 2:
        return None, None
    try:
        latest = hist[-1]
        latest_tvl = latest.get("tvl")
        now_s = latest.get("date") or 0
        day_ago_tvl = min(hist[:-1], key=lambda h: abs((h.get("date") or 0) - (now_s - 24 * 3600))).get("tvl")
        week_ago_tvl = min(hist, key=lambda h: abs((h.get("date") or 0) - (now_s - 7 * 24 * 3600))).get("tvl")
        return _pct_change(day_ago_tvl, latest_tvl), _pct_change(week_ago_tvl, latest_tvl)
    except (IndexError, TypeError, ValueError, AttributeError):
        return None, None


def get_base_dex_volume():
    """Real Base DEX trading volume (24h/7d) — the actual-activity counterpart
    to TVL (parked capital can sit idle; volume is money actually moving).
    Keyless. Deliberately its own small fetch here rather than importing
    agents/defillama.py's near-identical dex_volumes() — that module imports
    _get/_now_iso FROM this one, so the reverse import would be circular."""
    url = "https://api.llama.fi/overview/dexs/base?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
    d = _get(url, ttl=3600, cache_key="dl_dexs_base")
    if isinstance(d, dict) and d.get("error"):
        return d
    return {"ts": _now_iso(), "vol_24h_usd": d.get("total24h"), "vol_7d_usd": d.get("total7d")}


def get_protocol_tvl(slug="aerodrome"):
    """Single protocol TVL history/summary. Keyless."""
    return _get(f"https://api.llama.fi/protocol/{urllib.parse.quote(slug)}",
                ttl=1800, cache_key=f"llama_proto_{slug}")


def get_stablecoin_flows():
    """Stablecoin circulating supply (flow signal). Keyless."""
    d = _get("https://stablecoins.llama.fi/stablecoins?includePrices=true",
             ttl=1800, cache_key="llama_stables")
    if isinstance(d, dict) and d.get("peggedAssets"):
        top = sorted(d["peggedAssets"], key=lambda s: (s.get("circulating") or {}).get("peggedUSD", 0),
                     reverse=True)[:8]
        return {"ts": _now_iso(),
                "top_stablecoins": [{"symbol": s.get("symbol"), "name": s.get("name"),
                                     "circulating_usd": (s.get("circulating") or {}).get("peggedUSD")}
                                    for s in top]}
    return d


# ── 2. Base JSON-RPC: live chain activity ─────────────────────────────────────
def get_chain_activity():
    """Latest block number + gas price (live network pulse). Keyless. No cache (cheap+fresh)."""
    bn = _post_rpc("eth_blockNumber", [])
    gp = _post_rpc("eth_gasPrice", [])
    out = {"ts": _now_iso()}
    try:
        out["latest_block"] = int(bn["result"], 16)
    except Exception:
        out["latest_block_error"] = bn.get("error", bn)
    try:
        out["gas_price_gwei"] = round(int(gp["result"], 16) / 1e9, 4)
    except Exception:
        out["gas_price_error"] = gp.get("error", gp)
    return out


def get_recent_block_activity(block="latest", full_txs=False):
    """Block contents — tx count (and txs if full_txs). Keyless."""
    r = _post_rpc("eth_getBlockByNumber", [block, full_txs])
    if r.get("error") or not r.get("result"):
        return {"error": r.get("error", "no block")}
    blk = r["result"]
    return {"ts": _now_iso(),
            "number": int(blk.get("number", "0x0"), 16),
            "tx_count": len(blk.get("transactions", [])),
            "gas_used": int(blk.get("gasUsed", "0x0"), 16),
            "timestamp": int(blk.get("timestamp", "0x0"), 16),
            "transactions": blk.get("transactions") if full_txs else None}


# ── 3. CoinGecko: price / token market data ───────────────────────────────────
def get_token_price(ids="ethereum", vs="usd"):
    """Spot prices for coin ids (comma-sep). Keyless.

    Real gap this closes: on a CoinGecko failure/rate-limit this used to
    return {} silently (either a genuine empty JSON body, or an {"error":
    ...} dict a caller that only reads coin-id keys would never notice) —
    confirmed live in a paid market_intel deliverable that shipped an empty
    "prices" object. Falls back to DefiLlama's coins.llama.fi (a second,
    independent free price oracle already used elsewhere in this codebase)
    rather than silently returning nothing."""
    q = urllib.parse.urlencode({"ids": ids, "vs_currencies": vs,
                                "include_24hr_change": "true"})
    d = _get(f"https://api.coingecko.com/api/v3/simple/price?{q}",
             ttl=300, cache_key=f"cg_price_{ids}_{vs}")
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    have_all = isinstance(d, dict) and not d.get("error") and all(
        isinstance(d.get(i), dict) and d[i].get(vs) is not None for i in id_list
    )
    if have_all:
        return d
    fallback = _get_defillama_coin_prices(id_list)
    if not isinstance(d, dict) or d.get("error"):
        return fallback
    # Partial CoinGecko result — fill only the missing ids from the fallback
    # rather than discarding whatever CoinGecko did return.
    merged = dict(d)
    for i in id_list:
        if not (isinstance(merged.get(i), dict) and merged[i].get(vs) is not None) and i in fallback:
            merged[i] = fallback[i]
    return merged


def _get_defillama_coin_prices(coingecko_ids):
    """DefiLlama's coins.llama.fi price oracle, keyed by `coingecko:{id}` —
    same shape as CoinGecko's own simple/price response (just {usd: price}
    per id) so callers of get_token_price() don't need to special-case
    which source actually answered."""
    keys = ",".join(f"coingecko:{i}" for i in coingecko_ids)
    d = _get(f"https://coins.llama.fi/prices/current/{urllib.parse.quote(keys)}",
             ttl=300, cache_key=f"dl_price_{keys}")
    if not isinstance(d, dict) or d.get("error"):
        return {}
    coins = d.get("coins") or {}
    out = {}
    for i in coingecko_ids:
        c = coins.get(f"coingecko:{i}")
        if isinstance(c, dict) and c.get("price") is not None:
            out[i] = {"usd": c["price"]}
    return out


def get_token_market_by_contract(contract, platform="base"):
    """Market data for a token by its Base contract address. Keyless.

    Real gap this closes: this used to discard most of CoinGecko's own
    /coins/{platform}/contract/{address} response (a single already-paid-for
    call) down to just 4 price/volume fields, even though the SAME response
    also carries real supply/FDV/description/homepage/twitter data -- exactly
    the "tokenomics" and "what is this project" context a real report needs
    (confirmed missing in a live report, investigation-20260725-155143-
    0xB8d7710f.md, an ARENA/Avalanche investigation with zero tokenomics or
    project-narrative content despite CoinGecko tracking all of it). No new
    API call, no new key -- just stops throwing away data already fetched.
    """
    d = _get(f"https://api.coingecko.com/api/v3/coins/{platform}/contract/{contract}",
             ttl=600, cache_key=f"cg_contract_{platform}_{contract}")
    if isinstance(d, dict) and d.get("market_data"):
        m = d["market_data"]
        links = d.get("links") or {}
        homepages = [h for h in (links.get("homepage") or []) if h]
        # CoinGecko's own project description (English), HTML-stripped --
        # real, sourced text, never fabricated. Truncated to keep reports
        # readable, not to hide anything.
        desc_raw = (d.get("description") or {}).get("en") or ""
        desc = re.sub(r"<[^>]+>", " ", desc_raw)
        desc = re.sub(r"\s+", " ", desc).strip()
        return {"name": d.get("name"), "symbol": d.get("symbol"),
                # CoinGecko's own coin-id slug (e.g. "arena-2") -- the only
                # reliable way to build a real https://coingecko.com/en/coins/
                # page link; distinct from the "platform" id (e.g. "base")
                # passed into this function.
                "coingecko_id": d.get("id"),
                "price_usd": (m.get("current_price") or {}).get("usd"),
                "market_cap_usd": (m.get("market_cap") or {}).get("usd"),
                "vol_24h_usd": (m.get("total_volume") or {}).get("usd"),
                "change_24h_pct": m.get("price_change_percentage_24h"),
                "fdv_usd": (m.get("fully_diluted_valuation") or {}).get("usd"),
                "total_supply": m.get("total_supply"),
                "circulating_supply": m.get("circulating_supply"),
                "max_supply": m.get("max_supply"),
                "homepage": homepages[0] if homepages else None,
                "twitter": links.get("twitter_screen_name") or None,
                "description": desc[:600] if desc else None}
    return d


# ── 4. BaseScan / Etherscan V2: forensics (key OPTIONAL) ──────────────────────
def get_contract_source(address, chainid=8453):
    """Contract verification + source. Etherscan V2 free tier OK. Needs key."""
    if not BASESCAN_KEY:
        return {"error": "no_key", "note": "set ETHERSCAN_API_KEY for contract source"}
    q = urllib.parse.urlencode({"chainid": chainid, "module": "contract",
                                "action": "getsourcecode", "address": address,
                                "apikey": BASESCAN_KEY})
    d = _get(f"{ETHERSCAN_V2}?{q}", ttl=3600, cache_key=f"src_{chainid}_{address}")
    if isinstance(d, dict) and d.get("result"):
        r = d["result"][0] if isinstance(d["result"], list) else d["result"]
        return {"verified": bool(r.get("SourceCode")),
                "contract_name": r.get("ContractName"),
                "compiler": r.get("CompilerVersion"),
                "proxy": r.get("Proxy") == "1",
                "implementation": r.get("Implementation") or None,
                # Raw verified source (may be multi-file JSON-wrapped by Etherscan for
                # standard-json-input contracts) — additive field, existing callers only
                # ever .get() the fields above so this is safe. Used by
                # agents/deep_dive_audit.py to actually feed a frontier LLM the real
                # contract text instead of just metadata about it.
                "source_code": r.get("SourceCode") or None}
    return d


def get_account_txs(address, chainid=8453, limit=25):
    """Recent normal txs (forensics). Etherscan V2 account endpoints need PAID tier."""
    if not BASESCAN_KEY:
        return {"error": "no_key"}
    q = urllib.parse.urlencode({"chainid": chainid, "module": "account", "action": "txlist",
                                "address": address, "startblock": 0, "endblock": 99999999,
                                "page": 1, "offset": limit, "sort": "desc", "apikey": BASESCAN_KEY})
    d = _get(f"{ETHERSCAN_V2}?{q}", ttl=300, cache_key=f"txs_{chainid}_{address}")
    if isinstance(d, dict) and str(d.get("message", "")).upper() == "NOTOK":
        return {"error": "etherscan_notok", "note": "account txlist may require a paid plan",
                "raw": d.get("result")}
    return d


# ── 5. Security: DeFi exploit / hack feed (keyless) ───────────────────────────
def _incident_source_url(h):
    """Real per-incident source link (the original disclosure/news article
    DeFiLlama itself cites for this hack), NOT VAPE's own generated report —
    those are two different things and both are worth linking. Checked
    defensively across every plausible real key name DeFiLlama's raw hacks
    object might use (`source` is the one actually documented/observed;
    the rest are cheap, harmless fallbacks) rather than assumed off one
    guess — never fabricates a URL: a hack with none of these keys set
    (or a non-string/non-http value) simply gets no source link, same
    honest-degradation as every other optional field here."""
    for key in ("source", "sourceUrl", "sourceURL", "link", "url", "article"):
        v = h.get(key)
        if isinstance(v, str) and v.startswith("http"):
            return v
    return None


def get_hack_feed(limit=8, chain=None):
    """Recent DeFi exploits/hacks from DeFiLlama. Keyless. The backbone of the
    security vertical: dated incidents, $ lost, chain, technique, and (when
    DeFiLlama's own raw data actually includes one) a link to the original
    source article/disclosure for that specific incident."""
    d = _get("https://api.llama.fi/hacks", ttl=1800, cache_key="llama_hacks")
    if not isinstance(d, list):
        return {"error": "hacks feed unavailable", "raw": d}
    d = sorted(d, key=lambda x: x.get("date", 0), reverse=True)
    out = []
    for h in d:
        chains = h.get("chain") or []
        if chain and not any(str(chain).lower() == str(c).lower() for c in chains):
            continue
        try:
            ts = datetime.fromtimestamp(h.get("date", 0), tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            ts = "?"
        out.append({
            "date": ts,
            "name": h.get("name"),
            "amount_usd_m": round((h.get("amount") or 0) / 1e6, 3),
            "chains": chains,
            "technique": h.get("technique"),
            "source_url": _incident_source_url(h),
        })
        if len(out) >= limit:
            break
    return {"ts": _now_iso(), "count": len(out), "incidents": out}


# ── 6. Macro: Fear & Greed + global market breadth (keyless) ──────────────────
def get_fear_greed():
    """Crypto Fear & Greed index (0-100) + yesterday, for macro sentiment. Keyless."""
    d = _get("https://api.alternative.me/fng/?limit=2", ttl=1800, cache_key="fng")
    try:
        rows = d.get("data", [])
        now = rows[0]; prev = rows[1] if len(rows) > 1 else {}
        return {"ts": _now_iso(),
                "value": int(now.get("value")),
                "classification": now.get("value_classification"),
                "prev_value": int(prev.get("value")) if prev.get("value") else None,
                "prev_classification": prev.get("value_classification")}
    except Exception:
        return {"error": "fng unavailable", "raw": d}


def get_global_market():
    """Total mcap change, BTC/ETH dominance, volume. Keyless macro breadth."""
    d = _get("https://api.coingecko.com/api/v3/global", ttl=600, cache_key="cg_global")
    try:
        g = d["data"]
        return {"ts": _now_iso(),
                "total_mcap_usd": (g.get("total_market_cap") or {}).get("usd"),
                "total_vol_24h_usd": (g.get("total_volume") or {}).get("usd"),
                "mcap_change_24h_pct": round(g.get("market_cap_change_percentage_24h_usd", 0), 2),
                "btc_dominance_pct": round((g.get("market_cap_percentage") or {}).get("btc", 0), 2),
                "eth_dominance_pct": round((g.get("market_cap_percentage") or {}).get("eth", 0), 2),
                "active_cryptos": g.get("active_cryptocurrencies")}
    except Exception:
        return {"error": "global unavailable", "raw": d}


# ── 7. Virtuals Protocol ecosystem (keyless) ──────────────────────────────────
def _pct_change(old, new):
    if not isinstance(old, (int, float)) or not isinstance(new, (int, float)) or old == 0:
        return None
    return round((new - old) / abs(old) * 100, 2)


def get_virtuals_snapshot():
    """VIRTUAL token market + Virtuals-Protocol TVL — real trend data, not just
    a single day's price wiggle. A single 24h price change is noisy (any token
    can swing double digits on thin volume in a day); 7d/30d price trend and
    TVL trend are much harder to fake and reflect real, sustained ecosystem
    health rather than one day's sentiment."""
    q = urllib.parse.urlencode({"ids": "virtual-protocol", "vs_currencies": "usd",
                                "include_24hr_change": "true", "include_market_cap": "true",
                                "include_24hr_vol": "true"})
    px = _get(f"https://api.coingecko.com/api/v3/simple/price?{q}",
              ttl=300, cache_key="cg_virtual")
    v = (px or {}).get("virtual-protocol", {}) if isinstance(px, dict) else {}
    out = {"ts": _now_iso(),
           "virtual_price_usd": v.get("usd"),
           "virtual_mcap_usd": v.get("usd_market_cap"),
           "virtual_vol_24h_usd": v.get("usd_24h_vol"),
           "virtual_change_24h_pct": round(v["usd_24h_change"], 2) if v.get("usd_24h_change") is not None else None}

    # Volume/mcap ratio — a token trading at a healthy fraction of its market
    # cap daily has real, active markets; one trading at a tiny fraction is
    # illiquid regardless of what its price happens to be doing that day.
    out["volume_to_mcap_pct"] = (
        round(out["virtual_vol_24h_usd"] / out["virtual_mcap_usd"] * 100, 2)
        if isinstance(out.get("virtual_vol_24h_usd"), (int, float))
        and isinstance(out.get("virtual_mcap_usd"), (int, float))
        and out["virtual_mcap_usd"] > 0
        else None
    )

    # 7d/30d price trend — smooths out single-day noise. CoinGecko's
    # market_chart returns [ms_timestamp, price] pairs at roughly hourly
    # granularity across the requested window.
    chart = _get(
        "https://api.coingecko.com/api/v3/coins/virtual-protocol/market_chart"
        "?vs_currency=usd&days=30",
        ttl=3600, cache_key="cg_virtual_chart_30d")
    prices = (chart or {}).get("prices") if isinstance(chart, dict) else None
    if isinstance(prices, list) and len(prices) >= 2:
        try:
            latest = prices[-1][1]
            now_ms = prices[-1][0]
            week_ago_ms = now_ms - 7 * 24 * 3600 * 1000
            month_ago_price = prices[0][1]
            week_ago_price = min(prices, key=lambda p: abs(p[0] - week_ago_ms))[1]
            out["virtual_change_7d_pct"] = _pct_change(week_ago_price, latest)
            out["virtual_change_30d_pct"] = _pct_change(month_ago_price, latest)
        except (IndexError, TypeError, ValueError):
            pass

    proto = _get("https://api.llama.fi/protocol/virtual-protocol",
                 ttl=1800, cache_key="llama_virtuals")
    if isinstance(proto, dict) and not proto.get("error"):
        cur = proto.get("currentChainTvls") or {}
        if isinstance(cur, dict):
            out["protocol_tvl_usd"] = sum(x for x in cur.values() if isinstance(x, (int, float)))
        # Top-level `tvl` is DefiLlama's full historical series for this
        # protocol: [{"date": unix_seconds, "totalLiquidityUSD": number}, ...].
        # Real TVL trend (money actually staying in the ecosystem) is a much
        # sturdier fundamental signal than a single day's token price move.
        history = proto.get("tvl")
        if isinstance(history, list) and len(history) >= 2:
            try:
                latest_tvl = history[-1].get("totalLiquidityUSD")
                now_s = history[-1].get("date")
                week_ago_s = now_s - 7 * 24 * 3600
                month_ago_tvl = history[0].get("totalLiquidityUSD")
                week_ago_tvl = min(history, key=lambda h: abs((h.get("date") or 0) - week_ago_s)).get("totalLiquidityUSD")
                out["tvl_change_7d_pct"] = _pct_change(week_ago_tvl, latest_tvl)
                out["tvl_change_30d_pct"] = _pct_change(month_ago_tvl, latest_tvl)
            except (IndexError, TypeError, ValueError, AttributeError):
                pass
    return out


# ── 8. Base economic activity: fees / revenue (keyless) ───────────────────────
def get_base_fees():
    """Base chain 24h fees + top fee-generating protocols (real usage signal). Keyless."""
    d = _get("https://api.llama.fi/overview/fees/base?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
             ttl=1800, cache_key="llama_base_fees")
    if not isinstance(d, dict) or d.get("error"):
        return {"error": "base fees unavailable"}
    protos = d.get("protocols") or []
    top = sorted([p for p in protos if isinstance(p.get("total24h"), (int, float))],
                 key=lambda p: p.get("total24h", 0), reverse=True)[:6]
    return {"ts": _now_iso(),
            "total_fees_24h_usd": d.get("total24h"),
            "total_fees_7d_usd": d.get("total7d"),
            "change_24h_pct": d.get("change_1d"),
            "top_fee_protocols": [{"name": p.get("name"), "fees_24h_usd": p.get("total24h"),
                                   "category": p.get("category")} for p in top]}


# ── 9. Biggest 24h movers on Base (keyless, DexScreener) ──────────────────────
def get_evm_movers(network="base", limit=6):
    """Most active pools by 24h volume + biggest movers on any GeckoTerminal
    EVM network (keyless). Generalized from the old Base-only get_base_movers()
    so agents/investigate.py::auto_target() can rotate its candidate sourcing
    across chains instead of only ever looking at Base — see EVM_CHAINS in
    agents/investigate.py for the supported network slugs. `network` here is
    a GeckoTerminal network id (e.g. "base", "eth", "arbitrum"), not an EVM
    chain id. Degrades to an empty result on an unknown/unreachable slug,
    same as every other fetch in this module."""
    d = _get(f"https://api.geckoterminal.com/api/v2/networks/{network}/pools?page=1",
             ttl=600, cache_key=f"gt_{network}_pools")
    pools = d.get("data", []) if isinstance(d, dict) else []
    rows = []
    for p in pools:
        a = p.get("attributes", {}) if isinstance(p, dict) else {}
        vol = (a.get("volume_usd") or {}).get("h24")
        chg = (a.get("price_change_percentage") or {}).get("h24")
        try:
            vol = float(vol) if vol is not None else 0.0
        except Exception:
            vol = 0.0
        try:
            chg = float(chg) if chg is not None else None
        except Exception:
            chg = None
        rows.append({"name": a.get("name"), "price_usd": a.get("base_token_price_usd"),
                     "change_24h_pct": chg, "vol_24h_usd": round(vol),
                     "reserve_usd": a.get("reserve_in_usd")})
    # top by volume (venues), then flag biggest absolute movers among them
    by_vol = sorted(rows, key=lambda r: r["vol_24h_usd"], reverse=True)[:limit]
    movers = sorted([r for r in rows if isinstance(r["change_24h_pct"], (int, float))],
                    key=lambda r: abs(r["change_24h_pct"]), reverse=True)[:limit]
    return {"ts": _now_iso(), "network": network, "top_by_volume": by_vol, "biggest_movers": movers}


def get_base_movers(limit=6):
    """Back-compat wrapper — Base was the only network this ever covered
    before get_evm_movers() generalized it. Still used by
    build_market_context() for the site's Base-specific market section."""
    return get_evm_movers("base", limit)


# ── anomaly-flag cooldown: stop re-flagging the same stuck/stale mover ────────
# Real bug this fixes: a thin/illiquid pool can report an enormous 24h change
# (e.g. +99,000%) that barely moves cycle to cycle — not a fresh event, just a
# stale/degenerate ratio against a near-zero reference price. Without a
# cooldown, build_market_context()'s anomaly pass re-flags the exact same pool
# as "this cycle's" anomaly every single run (hourly), which is what made
# VAPE's own bounty reports read as stuck in a loop even though the flag
# itself wasn't wrong, just stale. State is committed (bounty-cycle.yml
# stages skillforge/memory/), so the cooldown survives across CI runs, not
# just within one process.
ANOMALY_STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   "skillforge", "memory", "anomaly_state.json")
ANOMALY_COOLDOWN_HOURS = 12
# "Barely changed" has to be judged relative to the value's own scale, not as
# a fixed point-difference — a pool stuck around +99,000% will naturally
# jitter by hundreds of points between polls without that being a new event,
# while a mover actually swinging from +30% to +45% is a real, small-scale
# change worth flagging. 5% relative drift (with a small absolute floor for
# tiny values) is "the same" anomaly; anything past that counts as new.
ANOMALY_REPEAT_RELATIVE_TOLERANCE = 0.05
ANOMALY_REPEAT_ABSOLUTE_FLOOR = 10


def _load_anomaly_state():
    try:
        with open(ANOMALY_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_anomaly_state(state):
    try:
        os.makedirs(os.path.dirname(ANOMALY_STATE_PATH), exist_ok=True)
        with open(ANOMALY_STATE_PATH, "w") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
    except Exception:
        pass


def _age_hours(ts_str):
    return (datetime.now(timezone.utc)
            - datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            ).total_seconds() / 3600


def _anomaly_is_stale_repeat(key, value, state):
    """True if `key` was already flagged recently with a near-identical value
    (same stuck anomaly, not a new event worth re-surfacing)."""
    prev = state.get(key)
    if not prev:
        return False
    try:
        age_hours = _age_hours(prev["ts"])
    except Exception:
        return False
    if age_hours >= ANOMALY_COOLDOWN_HOURS:
        return False  # cooldown expired — worth re-flagging even if unchanged
    try:
        prev_val = float(prev.get("value"))
        new_val = float(value)
        tolerance = max(ANOMALY_REPEAT_ABSOLUTE_FLOOR, abs(prev_val) * ANOMALY_REPEAT_RELATIVE_TOLERANCE)
        return abs(new_val - prev_val) <= tolerance
    except Exception:
        return False


def _filter_stale_mover_anomalies(mover_flags):
    """Given a list of (key, value, text) mover-anomaly candidates, drop the
    ones that are stale repeats and record the ones that survive. Returns the
    surviving text list. Isolated from the other anomaly categories (TVL/gas/
    hacks/F&G) since those weren't observed to have this stuck-value problem —
    only the mover feed showed the same pool re-flagged cycle after cycle."""
    state = _load_anomaly_state()
    now = _now_iso()
    kept = []
    for key, value, text in mover_flags:
        if _anomaly_is_stale_repeat(key, value, state):
            continue
        kept.append(text)
        state[key] = {"ts": now, "value": value}
    # prune entries older than a few cooldown windows so this file doesn't grow forever
    cutoff_state = {}
    for k, v in state.items():
        try:
            age_hours = _age_hours(v["ts"])
            if age_hours < ANOMALY_COOLDOWN_HOURS * 4:
                cutoff_state[k] = v
        except Exception:
            continue
    _save_anomaly_state(cutoff_state)
    return kept


def _market_overview_narrative(tvl, dex_vol, fng, glob_m):
    """Deterministic, template-built narrative from the real numbers already
    fetched — NOT an LLM call. market_intel is priced/positioned as a fast,
    cheap snapshot (see agents/acp_fulfill.py::_market_intel()); a frontier-
    model call would add real latency/cost for a sentence a template can
    build honestly from numbers already on hand. Every clause below reads
    directly off a real field — never invents a claim the data doesn't
    support, and omits a clause outright when its underlying field is
    missing rather than guessing."""
    parts = []
    tvl_usd, chg = tvl.get("tvl_usd"), tvl.get("tvl_24h_change_pct")
    if isinstance(tvl_usd, (int, float)):
        direction = "up" if isinstance(chg, (int, float)) and chg >= 0 else "down"
        chg_clause = f", {direction} {abs(chg):.1f}% over 24h" if isinstance(chg, (int, float)) else ""
        parts.append(f"Base TVL sits at ${tvl_usd:,.0f}{chg_clause}.")
    top = tvl.get("top_protocols") or []
    cats = tvl.get("category_breakdown_pct") or {}
    if top and cats:
        top_cat = max(cats, key=cats.get)
        leader = top[0]
        parts.append(
            f"{top_cat} leads the ecosystem at {cats[top_cat]:.1f}% of TVL, "
            f"with {leader['name']} alone holding {leader.get('share_of_base_pct') or 0:.1f}% of the chain's total."
        )
    if isinstance(dex_vol.get("vol_24h_usd"), (int, float)):
        parts.append(f"24h DEX volume on Base is ${dex_vol['vol_24h_usd']:,.0f}.")
    if isinstance(fng.get("value"), int):
        parts.append(f"Macro sentiment reads {fng['value']} ({fng.get('classification')}).")
    if isinstance(glob_m.get("mcap_change_24h_pct"), (int, float)):
        direction = "up" if glob_m["mcap_change_24h_pct"] >= 0 else "down"
        parts.append(f"Global crypto market cap is {direction} {abs(glob_m['mcap_change_24h_pct']):.1f}% over 24h.")
    return " ".join(parts) if parts else "Insufficient real data this cycle to summarize."


# ── orchestrator: one grounded-context blob for the LLM ───────────────────────
def build_market_context():
    """Single call the agent uses to ground a full, multi-domain report.

    Covers every VAPE vertical: Base chain, DeFi security/exploits, crypto macro,
    the Virtuals ecosystem, on-chain forensics inputs, and market movers. Every
    sub-fetch degrades gracefully to {"error": ...} so a report always renders.
    """
    tvl = get_base_tvl_and_protocols()
    dex_vol = get_base_dex_volume()
    activity = get_chain_activity()
    eth = get_token_price("ethereum,bitcoin")
    stables = get_stablecoin_flows()
    hacks = get_hack_feed(limit=8)
    fng = get_fear_greed()
    glob = get_global_market()
    virtuals = get_virtuals_snapshot()
    base_fees = get_base_fees()
    movers = get_base_movers()
    market_overview = _market_overview_narrative(tvl, dex_vol, fng, glob)

    # keyless rule-based anomaly heuristics (no LLM) across all domains
    anomalies = []
    try:
        if isinstance(tvl.get("tvl_24h_change_pct"), (int, float)) and tvl["tvl_24h_change_pct"] <= -10:
            anomalies.append(f"Base TVL down {tvl['tvl_24h_change_pct']:.1f}% in 24h — possible exploit/outflow")
        for p in tvl.get("top_protocols", []):
            c = p.get("change_1d")
            if isinstance(c, (int, float)) and c <= -20:
                anomalies.append(f"{p['name']} TVL {c:.1f}% in 24h — investigate")
        if isinstance(activity.get("gas_price_gwei"), (int, float)) and activity["gas_price_gwei"] > 5:
            anomalies.append(f"Elevated Base gas {activity['gas_price_gwei']} gwei — congestion/activity spike")
        # security: fresh exploit in last 48h
        for inc in (hacks.get("incidents") or [])[:3]:
            try:
                d = datetime.strptime(inc["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - d).days <= 2:
                    anomalies.append(f"RECENT EXPLOIT: {inc['name']} ${inc['amount_usd_m']}M on {inc['chains']} ({inc['technique']})")
            except Exception:
                pass
        # macro: extreme fear/greed
        if isinstance(fng.get("value"), int) and (fng["value"] <= 20 or fng["value"] >= 80):
            anomalies.append(f"Macro: F&G {fng['value']} ({fng['classification']}) — sentiment extreme")
        # movers: violent Base token moves — cooldown-filtered so a stuck/
        # stale extreme-% pool doesn't get re-flagged as "this cycle's"
        # anomaly every single run (see _filter_stale_mover_anomalies).
        mover_candidates = []
        for m in (movers.get("biggest_movers") or [])[:3]:
            ch = m.get("change_24h_pct")
            if isinstance(ch, (int, float)) and abs(ch) >= 25:
                key = f"mover:{m.get('name')}"
                text = f"Base mover: {m.get('name')} {ch:+.0f}% 24h (liq ${m.get('reserve_usd')}) — volatility/rug watch"
                mover_candidates.append((key, ch, text))
        anomalies.extend(_filter_stale_mover_anomalies(mover_candidates))
    except Exception:
        pass

    return {
        "generated_at": _now_iso(),
        "base_tvl": tvl,
        "base_dex_volume": dex_vol,
        "base_fees": base_fees,
        "chain_activity": activity,
        "prices": eth,
        "global_market": glob,
        "fear_greed": fng,
        "stablecoins": stables,
        "security_hacks": hacks,
        "virtuals": virtuals,
        "base_movers": movers,
        "market_overview": market_overview,
        "anomaly_flags": anomalies or ["none detected by rule-based pass"],
    }


if __name__ == "__main__":
    import sys
    out = build_market_context()
    print(json.dumps(out, indent=2)[:4000])
    sys.exit(0)
