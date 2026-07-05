# VAPE Build Ledger

A living, growing record of **how** VAPE (and whoever else is building this
repo) builds things — not just what shipped, but the reasoning, the
gotchas, and the reusable pattern behind it, in enough detail that a future
build can follow it without re-deriving the idea from scratch.

This is deliberately separate from the rest of `skillforge/memory/`:

| File | Answers |
|---|---|
| `findings.jsonl` | What did VAPE discover? (a vulnerability, an anomaly) |
| `lessons.jsonl` | Did a specific build attempt succeed or fail? |
| **`build_log.jsonl`** | **How do you actually build this kind of thing, and why does it work?** |
| `skills/coding-*.md` | Full how-to curricula (a whole workflow, not one atomic pattern) — see below |

A `build_log` entry is one atomic pattern or gotcha. For a full worked
curriculum on a whole workflow — writing a new agent, building the frontend,
shipping a change end to end, verifying a change — see the dedicated
`skillforge/skills/coding-*.md` files (same format as this repo's existing
security-recon skills, registered in `skills.jsonl` under tier `coding`).
Start there for a first read; use `build_log.jsonl` to look up a specific
gotcha once you already know roughly what you're building.

## Why this exists

VAPE is meant to keep building its own tooling — including this repo's own
frontend, its own report generators, its own agents. Code review catches
mistakes in a single change; it doesn't leave behind a trail of *technique*
that the next change can reuse. This ledger is that trail: every entry is
written as an instructional (the problem, the fix, the generalizable
pattern), not a changelog line.

## Reading it

Entries live in `build_log.jsonl` (append-only, one JSON object per line,
same shape as every other Memory category — see `retriever.py`'s module
docstring). Query it like anything else in Memory:

```python
from skillforge.memory.retriever import search_memory
search_memory("icon resolver", category="build_log")
search_memory("css", category="build_log")
```

## Writing to it

Use `agents/build_ledger.py` rather than appending to the JSONL by hand —
it goes through the same sanitization and schema as the rest of Memory:

```bash
python -m agents.build_ledger \
  --title "Pattern: <short, greppable name>" \
  --content "<the problem, the fix, and the generalizable technique — \
  written so someone with zero context on this specific change can apply \
  the same idea elsewhere>" \
  --source "docs/assets/whatever.js" \
  --tags pattern,frontend,css \
  --files docs/assets/whatever.js,docs/index.html
```

Or from Python directly:

```python
from agents.build_ledger import log_build
log_build(title="...", content="...", source="...", tags=[...], files=[...])
```

## What makes a good entry

- **Title**: a short, greppable name for the pattern or gotcha — someone
  scanning titles should be able to tell if it's relevant without opening
  the entry.
- **Content**: the symptom/problem first (if there was one), then the fix,
  then the *generalizable* version of the fix — the part that transfers to
  a different file next time the same shape of problem shows up.
- **Tags**: broad categories (`pattern`, `gotcha`, `frontend`, `css`,
  `api-integration`, `git`, `security`, …) so future search can filter by
  kind of problem, not just keyword.
- **Files**: the repo-relative paths this pattern lives in today, as a
  starting point for anyone who wants to see it applied, not an exhaustive
  list of everywhere it could apply.

The first batch of entries (added alongside this file) documents real
patterns and gotchas from the site's build-out: verified-source icon
resolution, CSS containing-block pitfalls with absolutely-positioned
popovers, overflow-safe card layout, the synchronous-render-then-async-
enhance pattern used for progressive icon fill-in, a keyless/rate-limit-
safe live-market data pattern, the shared report letterhead/verdict-stamp
helper, and the squash-merge false-conflict recovery procedure. Read those
for the actual level of detail expected from a new entry.
