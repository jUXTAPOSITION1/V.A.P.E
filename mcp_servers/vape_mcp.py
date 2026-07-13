#!/usr/bin/env python3
"""
V.A.P.E. MCP Server — expose the detective's REAL capabilities over the
Model Context Protocol so any MCP host (Claude, Cursor, VS Code, custom agents)
can discover and call them with no bespoke glue.

Design choices that match VAPE's model:
  - ZERO new dependencies. Pure stdlib. MCP is JSON-RPC 2.0 over stdio; we speak
    it directly (newline-delimited JSON on stdin/stdout). No SDK to install,
    which keeps it Termux/Android-friendly and compute-free to ship.
  - Calls REAL VAPE code (agents.investigate, token_scan, data_fetchers,
    agents.defillama, memory retriever + SQLite index) directly in-process.
    The one exception is wallet_trace, which shells out to
    skillforge/tools/recon/wallet_trace.sh (the real, Alchemy-backed,
    live-verified tool — see PR #145) rather than re-implementing it, so this
    server can never drift from what skillforge/toolcheck.py already verifies
    against the live API. No stubs, no fabricated data anywhere.
  - Read-only / keyless-first. Nothing here signs, spends, or mutates chain
    state. Every tool is safe to expose to any host.

Protocol: MCP 2024-11-05. Implements initialize, tools/list, tools/call,
resources/list, resources/read, ping. Transport: stdio.

Run standalone:  python mcp_servers/vape_mcp.py
Register in an MCP host (stdio) with command=python, args=[this path].
Smoke test:      python mcp_servers/vape_mcp.py --selftest
"""
import os
import sys
import json
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "vape-detective", "version": "1.1.0"}

# ── lazy real-capability imports (kept lazy so a missing optional dep can't
#    break server startup / tools/list discovery) ────────────────────────────
def _investigate(**kw):
    from agents.investigate import investigate
    addr = kw.get("address")
    chain = str(kw.get("chain", "8453"))
    if not addr:
        return {"error": "address required"}
    return investigate(addr, chain, hint="mcp", force=True)


def _token_scan(**kw):
    from agents.token_scan import scan
    addr = kw.get("address")
    if not addr:
        return {"error": "address required"}
    return scan(addr, int(kw.get("chain", 8453)))


def _hack_feed(**kw):
    from agents.data_fetchers import get_hack_feed
    return get_hack_feed(limit=int(kw.get("limit", 8)), chain=kw.get("chain"))


def _fear_greed(**kw):
    from agents.data_fetchers import get_fear_greed
    return get_fear_greed()


def _memory_search(**kw):
    """Prefer the SQLite index (queryable); fall back to the JSONL retriever."""
    q = kw.get("query", "")
    category = kw.get("category")
    days = kw.get("days")
    limit = int(kw.get("limit", 10))
    try:
        from skillforge.memory.index_db import query as db_query
        return {"results": db_query(q, category=category, days=days, limit=limit),
                "backend": "sqlite"}
    except Exception:
        from skillforge.memory.retriever import search_memory
        return {"results": search_memory(q, category=category, max_results=limit),
                "backend": "jsonl"}


def _memory_stats(**kw):
    from skillforge.memory.index_db import stats
    return stats()


def _research_search(**kw):
    from skillforge.research import search
    return search(kw.get('query', ''), int(kw.get('max_results', 5)))


def _research_scrape(**kw):
    from skillforge.research import scrape
    url = kw.get('url')
    if not url:
        return {'error': 'url required'}
    return scrape(url)


def _mcp_servers(**kw):
    from skillforge.mcp_client import status_all
    return {'servers': status_all()}


def _wallet_trace(**kw):
    """Real wallet/address forensics — shells out to the real, Alchemy-backed
    skillforge/tools/recon/wallet_trace.sh rather than re-implementing it
    (see the tool's own module docstring for why: Etherscan V2's account
    endpoints gate Base behind a paid tier; Alchemy's Transfers API does not).
    """
    import subprocess
    addr = kw.get("address")
    if not addr:
        return {"error": "address required"}
    mode = kw.get("mode", "txs")
    if mode not in ("txs", "erc20", "first"):
        return {"error": "mode must be one of: txs, erc20, first"}
    chain = str(kw.get("chain", "8453"))
    limit = str(kw.get("limit", 10))
    script = os.path.join(ROOT, "skillforge", "tools", "recon", "wallet_trace.sh")
    try:
        proc = subprocess.run(["bash", script, mode, chain, addr, limit],
                              capture_output=True, text=True, timeout=20)
    except Exception as e:
        return {"error": str(e)}
    raw = (proc.stdout or proc.stderr or "").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"error": "unparseable tool output", "raw": raw[:500]}


def _contract_source(**kw):
    from agents.data_fetchers import get_contract_source
    addr = kw.get("address")
    if not addr:
        return {"error": "address required"}
    return get_contract_source(addr, int(kw.get("chain", 8453)))


def _global_market(**kw):
    from agents.data_fetchers import get_global_market
    return get_global_market()


def _defillama_token_intel(**kw):
    from agents.defillama import token_intel
    chain, addr = kw.get("chain"), kw.get("address")
    if not chain or not addr:
        return {"error": "chain and address required"}
    return token_intel(chain, addr, kw.get("protocol_slug"))


def _defillama_chain_overview(**kw):
    from agents.defillama import chain_overview
    return chain_overview(kw.get("chain", "Base"))


def _defillama_protocols_on_chain(**kw):
    from agents.defillama import protocols_on_chain
    return protocols_on_chain(kw.get("chain", "Base"), int(kw.get("top_n", 20)))


def _defillama_yield_pools(**kw):
    from agents.defillama import yield_pools
    return yield_pools(kw.get("chain"), kw.get("project"), kw.get("symbol"),
                       float(kw.get("min_tvl", 10000)), int(kw.get("limit", 25)))


def _bounty_radar(**kw):
    """Real, currently-tracked bug-bounty/incident-lead opportunities
    (intel/bounty-radar/opportunities.json), ranked by the same numeric fit
    score agents/scout.py's hourly digest uses. Never LLM-scored."""
    path = os.path.join(ROOT, "intel", "bounty-radar", "opportunities.json")
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        return {"error": str(e)}
    min_fit = int(kw.get("min_fit", 50))
    limit = int(kw.get("limit", 15))
    rows = sorted((o for o in data if (o.get("fitScore") or 0) >= min_fit),
                  key=lambda o: o.get("fitScore", 0), reverse=True)
    return {"count": len(rows), "opportunities": rows[:limit]}


# ── tool registry: name -> (handler, description, input schema) ──────────────
TOOLS = {
    "investigate_token": (
        _investigate,
        "Run a V.A.P.E. deep on-chain investigation on a Base token/contract "
        "(GoPlus + DexScreener + Base RPC + hack-feed) -> 0-100 safety score and "
        "PROCEED/CAUTION/REJECT verdict with evidence. Read-only.",
        {"type": "object", "properties": {
            "address": {"type": "string", "description": "0x token/contract address"},
            "chain": {"type": "string", "description": "chain id, default 8453 (Base)"}},
         "required": ["address"]},
    ),
    "scan_token_safety": (
        _token_scan,
        "Fast token safety scan (GoPlus honeypot/tax/owner powers + DexScreener "
        "liquidity) returning a verdict. Read-only, keyless.",
        {"type": "object", "properties": {
            "address": {"type": "string"}, "chain": {"type": "string"}},
         "required": ["address"]},
    ),
    "recent_hacks": (
        _hack_feed,
        "Recent DeFi exploits/hacks from the DeFiLlama feed (dated, $ lost, chain, "
        "technique). Keyless.",
        {"type": "object", "properties": {
            "limit": {"type": "integer"}, "chain": {"type": "string"}}},
    ),
    "fear_greed": (
        _fear_greed,
        "Current crypto Fear & Greed index (market mood). Keyless.",
        {"type": "object", "properties": {}},
    ),
    "memory_search": (
        _memory_search,
        "Query V.A.P.E. Central Memory (SQLite-indexed findings/lessons/skills). "
        "Supports free text, category, and days-back filters.",
        {"type": "object", "properties": {
            "query": {"type": "string"},
            "category": {"type": "string", "description": "finding|lesson|skill"},
            "days": {"type": "integer"}, "limit": {"type": "integer"}}},
    ),
    "memory_stats": (
        _memory_stats,
        "Counts across V.A.P.E. Central Memory (by category, severity, high-confidence).",
        {"type": "object", "properties": {}},
    ),
    "research_search": (
        _research_search,
        "Web search via the best available provider (Tavily/Brave when keyed, "
        "keyless fallback otherwise) for bounties, protocols, CVEs, incidents.",
        {"type": "object", "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer"}}, "required": ["query"]},
    ),
    "research_scrape": (
        _research_scrape,
        "Scrape a page to clean text/markdown via the best available provider "
        "(Firecrawl/BrightData/Apify when keyed, keyless MCP fetch otherwise).",
        {"type": "object", "properties": {"url": {"type": "string"}},
         "required": ["url"]},
    ),
    "mcp_servers": (
        _mcp_servers,
        "List the MCP servers VAPE can host (reference + community search/scrape) "
        "and whether each is live, key-gated, or needs a runtime.",
        {"type": "object", "properties": {}},
    ),
    "wallet_trace": (
        _wallet_trace,
        "Wallet/address forensics via Alchemy's Transfers API: recent transfers "
        "(any asset or ERC-20 only) or first-seen transfer (funding source). "
        "Base/Ethereum/Arbitrum/Optimism. Needs VAPE_TRACE_ALCHEMY_API.",
        {"type": "object", "properties": {
            "address": {"type": "string"},
            "mode": {"type": "string", "description": "txs|erc20|first, default txs"},
            "chain": {"type": "string", "description": "chain id, default 8453 (Base)"},
            "limit": {"type": "integer"}},
         "required": ["address"]},
    ),
    "contract_source": (
        _contract_source,
        "Contract verification status + source/ABI metadata via Etherscan V2 "
        "(free tier). Needs ETHERSCAN_API_KEY.",
        {"type": "object", "properties": {
            "address": {"type": "string"}, "chain": {"type": "integer"}},
         "required": ["address"]},
    ),
    "global_market": (
        _global_market,
        "Global crypto market snapshot: BTC/ETH dominance, 24h market-cap change. Keyless.",
        {"type": "object", "properties": {}},
    ),
    "defillama_token_intel": (
        _defillama_token_intel,
        "DefiLlama's full picture of a token: current + first-seen price, and "
        "(with a protocol slug) fees/revenue, unlocks, and treasury. Keyless.",
        {"type": "object", "properties": {
            "chain": {"type": "string"}, "address": {"type": "string"},
            "protocol_slug": {"type": "string"}}, "required": ["chain", "address"]},
    ),
    "defillama_chain_overview": (
        _defillama_chain_overview,
        "A chain's headline TVL + rank among all tracked chains (DefiLlama). Keyless.",
        {"type": "object", "properties": {"chain": {"type": "string"}}},
    ),
    "defillama_protocols_on_chain": (
        _defillama_protocols_on_chain,
        "Top protocols on a chain by TVL, with category and 24h/7d change. Keyless.",
        {"type": "object", "properties": {
            "chain": {"type": "string"}, "top_n": {"type": "integer"}}},
    ),
    "defillama_yield_pools": (
        _defillama_yield_pools,
        "Yield pools filtered by chain/project/symbol, ranked by TVL, with "
        "APY/IL-risk/exposure — enough to spot a yield trap. Keyless.",
        {"type": "object", "properties": {
            "chain": {"type": "string"}, "project": {"type": "string"},
            "symbol": {"type": "string"}, "min_tvl": {"type": "number"},
            "limit": {"type": "integer"}}},
    ),
    "bounty_radar": (
        _bounty_radar,
        "Real, currently-tracked bug-bounty/incident-lead opportunities "
        "(Immunefi/Sherlock/DeFiLlama hacks), ranked by VAPE's own "
        "numeric fit score. Never LLM-scored.",
        {"type": "object", "properties": {
            "min_fit": {"type": "integer", "description": "default 50"},
            "limit": {"type": "integer", "description": "default 15"}}},
    ),
}

# ── resources: read-only URIs the host can pull ─────────────────────────────
def _res_reputation():
    with open(os.path.join(ROOT, "data", "reputation.json")) as f:
        return f.read()


def _res_intel_index():
    with open(os.path.join(ROOT, "data", "intel-index.json")) as f:
        return f.read()


RESOURCES = {
    "vape://reputation": ("Reputation & verifiable activity snapshot",
                          "application/json", _res_reputation),
    "vape://intel-index": ("Linkable index of reports/broadcasts/investigations/tools",
                           "application/json", _res_intel_index),
}


# ── JSON-RPC plumbing ───────────────────────────────────────────────────────
def _result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def handle(req):
    method = req.get("method")
    id_ = req.get("id")
    params = req.get("params") or {}

    if method == "initialize":
        return _result(id_, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}, "resources": {}},
            "serverInfo": SERVER_INFO,
        })
    if method in ("notifications/initialized", "initialized"):
        return None  # notification, no response
    if method == "ping":
        return _result(id_, {})

    if method == "tools/list":
        return _result(id_, {"tools": [
            {"name": n, "description": d, "inputSchema": s}
            for n, (_, d, s) in TOOLS.items()]})

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        entry = TOOLS.get(name)
        if not entry:
            return _error(id_, -32602, f"unknown tool: {name}")
        try:
            out = entry[0](**args)
            text = json.dumps(out, indent=2, default=str)
            return _result(id_, {"content": [{"type": "text", "text": text}],
                                 "isError": bool(isinstance(out, dict) and out.get("error"))})
        except Exception as e:
            return _result(id_, {"content": [{"type": "text",
                        "text": json.dumps({"error": str(e)})}], "isError": True})

    if method == "resources/list":
        return _result(id_, {"resources": [
            {"uri": u, "name": name, "mimeType": mime}
            for u, (name, mime, _) in RESOURCES.items()]})

    if method == "resources/read":
        uri = params.get("uri")
        entry = RESOURCES.get(uri)
        if not entry:
            return _error(id_, -32602, f"unknown resource: {uri}")
        try:
            return _result(id_, {"contents": [
                {"uri": uri, "mimeType": entry[1], "text": entry[2]()}]})
        except Exception as e:
            return _error(id_, -32603, str(e))

    return _error(id_, -32601, f"method not found: {method}")


def serve():
    """stdio loop: read newline-delimited JSON-RPC, write responses."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            resp = handle(req)
        except Exception:
            resp = _error(req.get("id"), -32603, traceback.format_exc().splitlines()[-1])
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


def selftest():
    """In-process exercise of the protocol without a host."""
    seq = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list"},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "memory_stats", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
         "params": {"name": "fear_greed", "arguments": {}}},
        {"jsonrpc": "2.0", "id": 6, "method": "tools/call",
         "params": {"name": "bounty_radar", "arguments": {"limit": 3}}},
    ]
    for r in seq:
        resp = handle(r)
        tag = r.get("method")
        if tag == "tools/list":
            names = [t["name"] for t in resp["result"]["tools"]]
            print(f"tools/list -> {names}")
        elif tag == "resources/list":
            uris = [x["uri"] for x in resp["result"]["resources"]]
            print(f"resources/list -> {uris}")
        elif tag == "initialize":
            print(f"initialize -> protocol {resp['result']['protocolVersion']}")
        else:
            body = resp["result"]["content"][0]["text"] if "result" in resp else resp
            print(f"{r['params']['name']} -> {str(body)[:120]}")
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        serve()
