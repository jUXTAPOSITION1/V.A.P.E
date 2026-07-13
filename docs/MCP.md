# MCP Integration — Secure External Capabilities

`skillforge/mcp.py`

The MCP layer extends V.A.P.E. with safe, read-first access to external tools and data.
Results flow into Central Memory; Builder can later wrap or extend these capabilities.
Security is paramount: least privilege, input validation, rate limiting, full logging,
and human review gates on any write.

---

## Wrappers

### 1. `GitHubMCPWrapper` — repository intelligence

Read-heavy access to the repo, gated writes for self-improvement.

| Method | Access | Purpose |
|--------|--------|---------|
| `search_issues(repo, query, state, limit)` | read | find relevant issues |
| `read_file(repo, path, ref)` | read | let Builder inspect its own source |
| `create_pr(repo, title, body, head, base)` | **write (gated)** | Builder proposes improvements |

Writes are sanitized, audit-logged (`[WRITE]`), and rate-limited. Uses the GitHub REST
API with `GITHUB_TOKEN`; no key needed for public reads.

```python
from skillforge.mcp import GitHubMCPWrapper
gh = GitHubMCPWrapper()
issues = gh.search_issues("jUXTAPOSITION1/V.A.P.E", "builder", limit=5)
ok, readme = gh.read_file("jUXTAPOSITION1/V.A.P.E", "README.md")
```

### 2. `SocialMCPWrapper` — narrative & sentiment intelligence

Aggregated, anonymized public sentiment for the Base / Virtuals ecosystem. No posting,
no engagement, no individual-user tracking. Results cached for 1 hour and appended to
Memory as `social_event` entries.

```python
from skillforge.mcp import SocialMCPWrapper
social = SocialMCPWrapper()
summary = social.get_sentiment_summary(accounts=["@based_vape"], days_back=1)
social.append_social_event_to_memory({"title": "Daily sentiment", "content": "...", "tags": ["social"]})
```

### 3. `ToolRegistryMCPWrapper` — security-tool freshness

Fetches latest releases and CVE summaries so SKILLFORGE always tracks current tool
versions.

```python
from skillforge.mcp import ToolRegistryMCPWrapper
reg = ToolRegistryMCPWrapper()
releases = reg.fetch_tool_releases("crytic", "slither", limit=3)
```

---

## Orchestration

`run_mcp_harvest()` runs a single collection pass across all three wrappers and appends
a summary to Memory:

```bash
python skillforge/mcp.py --harvest
python skillforge/mcp.py --github-issues "builder"
python skillforge/mcp.py --social-sentiment
python skillforge/mcp.py --tool-releases crytic/slither
```

Directly in Python:

```python
from skillforge.mcp import run_mcp_harvest
result = run_mcp_harvest()   # harvests + appends to Memory
```

---

## Security model

| Control | Implementation |
|---------|----------------|
| **Least privilege** | read-only by default; writes are separate, gated methods |
| **Input validation** | all query params regex-sanitized and length-capped |
| **Rate limiting** | per-wrapper call windows (GitHub 60/min, Social 30/min) |
| **Logging** | every call + result logged under the `VAPE.MCP` logger; writes tagged `[WRITE]` |
| **Graceful errors** | timeouts, HTTP error handling, cache fallback |
| **No PII** | social data aggregated/anonymized only |
| **Human review gates** | high-impact writes (PRs) are explicit, logged, and opt-in |

---

## Interconnection

```
MCP wrappers ──▶ append_to_memory()  ──▶  Central Memory  ──▶  Builder / Detective
     ▲                                                              │
     └──────────────── Builder can wrap/extend MCP tools ◀──────────┘
```

- MCP results are stored in Memory for retrieval by any component.
- Memory is consulted before/after MCP calls to avoid redundant work.
- Builder can generate new wrappers around MCP tools (grounded in Memory).

---

## Roadmap

- Replace the MVP synthetic social summary with a live X API v2 / approved partner feed.
- Wire real NVD/CVE feeds into `fetch_cve_summary`.
- Add a dedicated `skillforge-mcp-harvest.yml` workflow (currently invoked via harvest /
  the full cycle).

---

*MCP is how V.A.P.E. safely reaches beyond its own repo — every external byte lands in
Memory, rate-limited, validated, and logged.*
