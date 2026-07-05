# Skill: Writing a New VAPE Agent Script (Python)

**Tier:** coding · **Status:** active

## When to use
Any time a new autonomous capability is needed — a new data source to watch, a
new kind of report to generate, a new scheduled check. Every existing agent
(`agents/investigate.py`, `agents/broadcast.py`, `agents/scout.py`,
`agents/run.py`) follows this same shape; a new one should too, so the whole
`agents/` directory stays predictable to read and to extend.

## Procedure (reproducible, grounded in this repo's real agents)

1. **Start from the real-data-only rule, not from a mock.** Every agent in
   this repo calls real, live APIs (GoPlus, DexScreener, DefiLlama, Base RPC,
   alternative.me, CoinGecko) and writes down exactly what came back — never
   a fabricated number, never a placeholder verdict. If a data source is
   unreachable, the agent says so explicitly (`"— No DEX pair data (illiquid
   / not listed)."` in `investigate.py`) rather than inventing a plausible-
   looking value. This is the single most important convention in this
   codebase — read `agents/investigate.py`'s module docstring before writing
   anything.

2. **Make the module importable both as a script and as `agents.<name>`.**
   Every agent starts with:
   ```python
   ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
   if ROOT not in sys.path:
       sys.path.insert(0, ROOT)
   ```
   This lets it run as `python agents/foo.py` (local dev) or
   `python -m agents.foo` (CI, `from agents.foo import x` elsewhere) without
   import errors either way. Copy this block verbatim — don't reinvent it.

3. **Pull real data through `agents/data_fetchers.py` where it already
   exists.** `build_market_context()` already aggregates TVL, fees, hacks,
   Fear & Greed, global market, Virtuals price, and anomaly flags — a new
   agent that needs any of that should call it, not re-fetch from scratch.
   Only add a new fetcher function there if the data genuinely isn't covered
   yet.

4. **Write the report with a shared formatter, not ad-hoc emoji.** Import
   `letterhead_md` and `verdict_stamp` from `agents/report_format.py` for any
   markdown output — see that module's docstring for why (a security dossier
   reads as a security dossier, not a chat message, and every report shares
   one visual identity).

5. **Persist to Memory, not just to a file.** If the agent produces a
   finding, lesson, or reusable pattern, append it to the shared Memory
   system (`skillforge/memory/retriever.py`'s `append_to_memory()`) with the
   right category — `finding` for a discovery, `lesson` for a build outcome,
   `build_log` for an instructional pattern (see
   `skillforge/memory/BUILD_LEDGER.md`). A report that only exists as a
   file on disk can't be searched by a future agent; one appended to Memory
   can.

6. **Give it a CLI entry point with `argparse`**, not a bare `if __name__`
   block with hardcoded args — every existing agent takes flags (
   `agents/investigate.py --address 0x...`, `agents/broadcast.py
   --window-hours 6`) so it's runnable both from a GitHub Actions workflow
   and by hand for debugging.

## Quality gates
- `python3 -m py_compile agents/<new>.py` and `python3 -c "import
  agents.<new>"` must both pass before it's considered done — a syntax error
  or a broken import at the top of the file fails silently in a scheduled
  workflow otherwise.
- No hardcoded API keys — read from `os.getenv(...)` with a graceful
  degradation path if the key is absent (see how `ETHERSCAN_API_KEY` is
  handled in `investigate.py`'s contract-verification step: skipped with a
  note, not a crash).
- If it writes a file into `intel/` or `reports/`, it must also be picked up
  by `agents/build_intel_index.py` (the site's `data/intel-index.json`
  generator) or it'll never surface on the live site — check that indexer's
  glob patterns match your new file's naming convention.

## Known limitations
- This pattern is for *deterministic, keyless-where-possible* agents. An
  agent that genuinely needs an LLM (like `agents/run.py`'s cycle analysis)
  still follows steps 2–6, but its "real data" is itself a real LLM response
  to a real prompt over real market data, not deterministic computation —
  the "no fabrication" rule still applies to the prompt design (see
  `agents/run.py`'s explicit "Do not use emoji" and "SIGNAL: HIGH/LOW"
  discipline in its system prompt) even though the output text isn't
  deterministic.

_Written for skillforge/memory/build_log.jsonl's coding-education track —
see skillforge/memory/BUILD_LEDGER.md._
