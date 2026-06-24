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
                "implementation": r.get("Implementation") or None}
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


# ── orchestrator: one grounded-context blob for the LLM ───────────────────────
def build_market_context():
    """Single call the agent uses to ground a report. Returns dict + a flat summary string."""
    tvl = get_base_tvl_and_protocols()
    activity = get_chain_activity()
    eth = get_token_price("ethereum,bitcoin")
    stables = get_stablecoin_flows()

    # simple keyless anomaly heuristics (no LLM)
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
    except Exception:
        pass

    return {
        "generated_at": _now_iso(),
        "base_tvl": tvl,
        "chain_activity": activity,
        "prices": eth,
        "stablecoins": stables,
        "anomaly_flags": anomalies or ["none detected by rule-based pass"],
    }


if __name__ == "__main__":
    import sys
    out = build_market_context()
    print(json.dumps(out, indent=2)[:4000])
    sys.exit(0)
