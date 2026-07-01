# 🔌 V.A.P.E. MCP Server — standard Model Context Protocol

`mcp_servers/vape_mcp.py`

V.A.P.E. now speaks the **industry-standard Model Context Protocol** (MCP
`2024-11-05`), so any MCP host — Claude, Cursor, VS Code Copilot, or a custom
agent — can **discover and call V.A.P.E.'s real capabilities** with no bespoke glue.

## Why this way

- **Zero new dependencies.** MCP is JSON-RPC 2.0 over stdio; the server speaks it
  directly with pure stdlib. Nothing to `pip install` — keeps VAPE compute-free
  and **Termux/Android-friendly** (stdio is the local transport).
- **Real code, real data.** Every tool calls existing VAPE functions
  (`agents.investigate`, `agents.token_scan`, `agents.data_fetchers`, the Memory
  retriever + SQLite index). No stubs, no fabricated numbers.
- **Read-only / keyless-first.** Nothing here signs, spends, or mutates chain
  state — safe to expose to any host.

## Tools exposed (`tools/list`)

| Tool | What it does |
|------|--------------|
| `investigate_token` | Deep on-chain investigation (GoPlus + DexScreener + Base RPC + hack feed) → 0-100 score + PROCEED/CAUTION/REJECT verdict |
| `scan_token_safety` | Fast honeypot/tax/owner-power + liquidity scan → verdict |
| `recent_hacks` | Recent DeFi exploits (DeFiLlama): dated, $ lost, chain, technique |
| `fear_greed` | Current crypto Fear & Greed index |
| `memory_search` | Query Central Memory (SQLite-indexed) by text/category/days |
| `memory_stats` | Counts by category, severity, high-confidence |

## Resources exposed (`resources/list`)

| URI | Contents |
|-----|----------|
| `vape://reputation` | Reputation & verifiable-activity snapshot |
| `vape://intel-index` | Linkable index of reports/broadcasts/investigations/tools |

## Run it

```bash
# stdio server (what an MCP host launches)
python mcp_servers/vape_mcp.py

# in-process smoke test (no host needed)
python mcp_servers/vape_mcp.py --selftest
```

## Register in an MCP host (stdio)

```json
{
  "mcpServers": {
    "vape-detective": {
      "command": "python",
      "args": ["/abs/path/to/V.A.P.E/mcp_servers/vape_mcp.py"]
    }
  }
}
```

The host then sees six discoverable tools and two resources — the LLM picks and
calls them automatically.

## Relationship to the old MCP layer

`skillforge/mcp.py` (VAPE's original "Modular Connector Protocol" wrappers for
GitHub/social/tool-registry) still runs as-is. This server is the **standard**
MCP surface layered on top — it does not replace the harvest wrappers, it makes
VAPE's investigation + memory capabilities interoperable with the wider ecosystem.

## Queryable memory (companion)

`skillforge/memory/index_db.py` projects the append-only JSONL memory into a
**stdlib-SQLite** index (with FTS5 full-text when available). The JSONL files
remain the source of truth / audit trail; the DB is a derived, rebuildable
projection so agents can ask real questions:

```bash
python -m skillforge.memory.index_db build
python -m skillforge.memory.index_db query "honeypot base" --category finding --days 30
python -m skillforge.memory.index_db stats
```

`memory.db` is **not** committed (gitignored) — it is rebuilt from JSONL each
cycle by the bounty-cycle workflow, and on demand by the MCP `memory_search` tool.
