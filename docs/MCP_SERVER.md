# V.A.P.E. MCP Server — standard Model Context Protocol

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

## VAPE as an MCP *host* (consuming the ecosystem)

Beyond serving its own tools, VAPE can now **spawn and consume any MCP server** —
official reference servers and community search/scrape servers — via a pure-stdlib
host client.

- **`skillforge/mcp_client.py`** — the host. Spawns a server over stdio, does the
  JSON-RPC handshake, lists/calls tools, tears it down. Servers are launched
  **lazily per call** (no daemons = no idle compute). PATH is auto-augmented so
  `npx`/`uvx` resolve even under cron/CI.
- **`mcp_servers/registry.json`** — declares every server: command, args, required
  env keys, keyless flag, and verified package source. Keyed servers activate the
  instant their env var is set — no code change.

```bash
python -m skillforge.mcp_client list                    # registry + live/keyed/needs-runtime
python -m skillforge.mcp_client tools git               # discover a server's tools
python -m skillforge.mcp_client call filesystem list_allowed_directories '{}'
```

### Registered servers

| Server | Source | Status without keys |
|--------|--------|---------------------|
| `vape` | in-repo | **live** (VAPE's own tools) |
| `filesystem` | npm `@modelcontextprotocol/server-filesystem` | **live** (sandboxed to intel/skillforge/reports) |
| `memory` | npm `@modelcontextprotocol/server-memory` | **live** (knowledge-graph) |
| `sequential-thinking` | npm `@modelcontextprotocol/server-sequential-thinking` | **live** |
| `fetch` | pypi `mcp-server-fetch` (uvx) | **live** (needs `uv`) |
| `git` | pypi `mcp-server-git` (uvx) | **live** (needs `uv`) |
| `sqlite` | pypi `mcp-server-sqlite` (uvx) | **live** (needs `uv`) |
| `brave-search` | npm `@modelcontextprotocol/server-brave-search` | needs `BRAVE_API_KEY` |
| `tavily` | npm `tavily-mcp` | needs `TAVILY_API_KEY` |
| `firecrawl` | npm `firecrawl-mcp` | needs `FIRECRAWL_API_KEY` |
| `apify` | npm `@apify/actors-mcp-server` | needs `APIFY_TOKEN` |
| `brightdata` | npm `@brightdata/mcp` | needs `BRIGHTDATA_API_TOKEN` |
| `github` | npm `@modelcontextprotocol/server-github` | needs `GITHUB_TOKEN` |

The `uvx` runtime (`uv`) is a single static binary: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

## Unified research router

**`skillforge/research.py`** gives VAPE one search/scrape API that uses the **best
available provider** and **falls back to keyless**:

- **search**: Tavily → Brave → keyless (SearXNG/DDG, best-effort).
- **scrape**: Firecrawl → Bright Data → Apify → keyless MCP `fetch`.

```bash
python -m skillforge.research providers                 # what's active right now
python -m skillforge.research search "base defi exploit bounty" --max 5
python -m skillforge.research scrape https://docs.base.org/
```

These are also exposed as MCP tools on VAPE's own server (`research_search`,
`research_scrape`, `mcp_servers`), so any host or VAPE agent can call them. Add a
provider key and the same call silently upgrades from keyless to Tavily/Firecrawl.

> Note: keyless public search is unreliable from datacenter/CI IPs (they get
> blocked) — that is exactly why the keyed providers exist. Keyless **scrape** of
> known URLs works well via the MCP `fetch` server.

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
