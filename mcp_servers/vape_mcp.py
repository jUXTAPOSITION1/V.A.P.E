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
    memory retriever + SQLite index). No stubs, no fabricated data.
  - Read-only / keyless-first. Nothing here signs, spends, or mutates chain
    state. The investigation + scan tools are safe to expose to any host.

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
SERVER_INFO = {"name": "vape-detective", "version": "1.0.0"}

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
