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
    """Base chain TVL + 24h/7d change + top protocols by TVL. Keyless."""
    chains = _get("https://api.llama.fi/v2/chains", ttl=900, cache_key="llama_chains")
    if isinstance(chains, dict) and chains.get("error"):
        return chains
    base = next((c for c in chains if str(c.get("name", "")).lower() == "base"), None)
    if not base:
        return {"error": "Base chain not found in DefiLlama"}
    out = {
        "ts": _now_iso(),
        "tvl_usd": base.get("tvl"),
        "tvl_24h_change_pct": base.get("change_1d"),
        "tvl_7d_change_pct": base.get("change_7d"),
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
        out["top_protocols"] = [
            {"name": p.get("name"), "base_tvl_usd": base_tvl(p),
             "change_1d": p.get("change_1d"), "change_7d": p.get("change_7d"),
             "category": p.get("category")}
            for p in base_protos[:top_n]
        ]
    return out


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
    """Spot prices for coin ids (comma-sep). Keyless."""
    q = urllib.parse.urlencode({"ids": ids, "vs_currencies": vs,
                                "include_24hr_change": "true"})
    return _get(f"https://api.coingecko.com/api/v3/simple/price?{q}",
                ttl=300, cache_key=f"cg_price_{ids}_{vs}")


def get_token_market_by_contract(contract, platform="base"):
    """Market data for a token by its Base contract address. Keyless."""
    d = _get(f"https://api.coingecko.com/api/v3/coins/{platform}/contract/{contract}",
             ttl=600, cache_key=f"cg_contract_{platform}_{contract}")
    if isinstance(d, dict) and d.get("market_data"):
        m = d["market_data"]
        return {"name": d.get("name"), "symbol": d.get("symbol"),
                "price_usd": (m.get("current_price") or {}).get("usd"),
                "market_cap_usd": (m.get("market_cap") or {}).get("usd"),
                "vol_24h_usd": (m.get("total_volume") or {}).get("usd"),
                "change_24h_pct": m.get("price_change_percentage_24h")}
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
def get_hack_feed(limit=8, chain=None):
    """Recent DeFi exploits/hacks from DeFiLlama. Keyless. The backbone of the
    security vertical: dated incidents, $ lost, chain, technique."""
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
def get_virtuals_snapshot():
    """VIRTUAL token market + Virtuals-Protocol TVL. The agent's home ecosystem."""
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
    proto = _get("https://api.llama.fi/protocol/virtual-protocol",
                 ttl=1800, cache_key="llama_virtuals")
    if isinstance(proto, dict) and not proto.get("error"):
        cur = proto.get("currentChainTvls") or {}
        if isinstance(cur, dict):
            out["protocol_tvl_usd"] = sum(x for x in cur.values() if isinstance(x, (int, float)))
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


def _anomaly_is_stale_repeat(key, value, state):
    """True if `key` was already flagged recently with a near-identical value
    (same stuck anomaly, not a new event worth re-surfacing)."""
    prev = state.get(key)
    if not prev:
        return False
    try:
        age_hours = (datetime.now(timezone.utc)
                     - datetime.strptime(prev["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                     ).total_seconds() / 3600
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
            age_hours = (datetime.now(timezone.utc)
                         - datetime.strptime(v["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                         ).total_seconds() / 3600
            if age_hours < ANOMALY_COOLDOWN_HOURS * 4:
                cutoff_state[k] = v
        except Exception:
            continue
    _save_anomaly_state(cutoff_state)
    return kept


# ── orchestrator: one grounded-context blob for the LLM ───────────────────────
def build_market_context():
    """Single call the agent uses to ground a full, multi-domain report.

    Covers every VAPE vertical: Base chain, DeFi security/exploits, crypto macro,
    the Virtuals ecosystem, on-chain forensics inputs, and market movers. Every
    sub-fetch degrades gracefully to {"error": ...} so a report always renders.
    """
    tvl = get_base_tvl_and_protocols()
    activity = get_chain_activity()
    eth = get_token_price("ethereum,bitcoin")
    stables = get_stablecoin_flows()
    hacks = get_hack_feed(limit=8)
    fng = get_fear_greed()
    glob = get_global_market()
    virtuals = get_virtuals_snapshot()
    base_fees = get_base_fees()
    movers = get_base_movers()

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
        "base_fees": base_fees,
        "chain_activity": activity,
        "prices": eth,
        "global_market": glob,
        "fear_greed": fng,
        "stablecoins": stables,
        "security_hacks": hacks,
        "virtuals": virtuals,
        "base_movers": movers,
        "anomaly_flags": anomalies or ["none detected by rule-based pass"],
    }


if __name__ == "__main__":
    import sys
    out = build_market_context()
    print(json.dumps(out, indent=2)[:4000])
    sys.exit(0)
