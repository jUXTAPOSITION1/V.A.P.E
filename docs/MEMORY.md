# 🧠 Central Memory — V.A.P.E.'s Long-Term Brain

`skillforge/memory/retriever.py`

Memory is the **shared intelligence layer** for the entire V.A.P.E. system. Every
component — the detective flows, Builder, MCP wrappers, and self-improvement — reads
from and writes to Memory, creating a compounding intelligence loop: each run makes the
next run smarter.

---

## Why it exists

Before Memory, every hourly cycle started cold. Now the detective grounds each analysis
in prior findings, Builder grounds code generation in past lessons, and MCP results
enrich the same shared corpus. Nothing learned is ever lost.

```
                 ┌─────────────────────────────┐
   Detective ───▶│                             │◀─── MCP (GitHub / Social / Tools)
   (run.py)      │        CENTRAL MEMORY        │
                 │  findings · lessons · skills │
   Builder  ────▶│      · social-events         │◀─── Self-Improvement
                 └─────────────────────────────┘
        every module SEARCHES before acting, APPENDS after acting
```

---

## Storage layout

| File | Category | Written by |
|------|----------|------------|
| `findings.jsonl` | `finding` | detective runs, MCP harvest, intel-cycle |
| `lessons.jsonl` | `lesson` | self-improve, toolcheck outcomes |
| `skills.jsonl` | `skill` | Builder-generated playbooks |
| `social-events.jsonl` | `social_event` | Social/X MCP wrapper |
| `tools-registry.json` | — | SKILLFORGE toolcheck (version-pinned tools) |
| `INDEX.md` | — | auto-generated human-readable summary |

All entry files are **append-only JSONL**. Entries are immutable once written.

---

## Schema

New canonical entry:

```json
{
  "id": "a1b2c3d4e5f6",
  "category": "finding",
  "title": "High TVL outflow from Morpho Blue on Base",
  "content": "$2.5M left Morpho/Base 14:00–14:30 UTC ...",
  "source": "agents/run.py",
  "tags": ["base", "tvl", "morpho", "anomaly"],
  "confidence": 0.9,
  "timestamp": "2026-07-01T14:35:00",
  "metadata": {"chain": "base", "amount_usd": 2500000}
}
```

### Backward compatibility

Legacy SKILLFORGE workflows wrote a different shape (`{ts, source, summary, ref}` for
findings and `{ts, action, outcome, note}` for lessons). The retriever **normalizes
legacy rows on read** (`_normalize_entry`), so the entire historical corpus stays
queryable without rewriting history or disturbing the live workflows.

---

## API

```python
from skillforge.memory.retriever import (
    search_memory, append_to_memory, get_memory_stats, init_memory
)
```

### `append_to_memory(category, title, content, source, tags, confidence, metadata)`

```python
append_to_memory(
    category="finding",
    title="Aave V3 utilization spike on Base",
    content="Utilization jumped 62%→91% in 40 min; liquidation risk elevated.",
    source="agents/run.py",
    tags=["base", "aave", "risk"],
    confidence=0.88,
)
```

Categories: `finding`, `lesson`, `skill`, `social_event`.

### `search_memory(query, category=None, tags=None, max_results=10, min_confidence=0.0, days_back=None)`

```python
recent = search_memory(
    query="base tvl anomaly",
    category="finding",
    min_confidence=0.8,
    days_back=7,
)
```

Keyword relevance is combined with confidence for ranking. Filters: category, tags,
minimum confidence, and time window.

### `get_memory_stats()`

Returns totals by category, by source, and a confidence distribution.

---

## Security

- **Input sanitization** — secret patterns (API keys, tokens) stripped; long EVM
  addresses masked; content length-capped.
- **Append-only** — no deletion or mutation after write (integrity + auditability).
- **Full logging** — every read/write is logged under the `VAPE.Memory` logger.
- **Structured only** — every entry carries category, timestamp, source, confidence.

---

## Integration points

| Module | Uses Memory to… |
|--------|-----------------|
| `agents/run.py` | ground each bounty cycle in prior intel, then append the analysis |
| `agents/builder.py` | ground code generation in lessons; auto-append generated skills |
| `agents/integration.py` | coordinate search→act→append across all flows |
| `skillforge/mcp.py` | append social sentiment + external harvest results |
| `skillforge/toolcheck.py` | record tool verification outcomes as lessons |

---

*Memory is the backbone of V.A.P.E.'s compounding intelligence. Every pattern found,
every threat traced, every lesson learned is recorded and available to all future runs.*
