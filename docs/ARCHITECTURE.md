# V.A.P.E. Architecture

> Status legend: [OK] implemented & running · [WIP] partial/scaffolded · [TBD] planned

V.A.P.E. is an autonomous on-chain security & intelligence operation. It runs as
**two cooperating runtimes** plus a **self-improving skill ecosystem**, all on free
tiers (Groq + GitHub Actions + open-source tooling).

## High-level flow

```
                          ┌──────────────────────────────────────────┐
                          │            DATA SOURCES (real)            │
                          │  Base RPC · Etherscan V2 · DexScreener    │
                          │  GoPlus · CoinGecko · DeFiLlama · CVEs    │
                          │  Immunefi/Code4rena · X/@based_vape       │
                          └───────────────┬───────────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
┌───────▼────────┐              ┌─────────▼─────────┐             ┌─────────▼─────────┐
│  PYTHON ENGINE │              │    SKILLFORGE      │             │    ACP MONITOR    │
│  (CI, hourly)  │              │ (GitHub Actions)   │             │  (job lifecycle)  │
│  agents/*.py   │              │  skillforge/*      │             │  scripts/acp-*    │
└───────┬────────┘              └─────────┬──────────┘             └─────────┬─────────┘
        │                                 │                                 │
        └─────────────────┬───────────────┴─────────────────┬───────────────┘
                          │                                 │
                 ┌────────▼────────┐               ┌────────▼─────────┐
                 │      intel/     │               │  Virtuals ACP    │
                 │ reports/audits/ │               │ events→triage→   │
                 │ broadcasts/     │               │ negotiate/fund/  │
                 │ bounty-radar/   │               │ complete jobs    │
                 └────────┬────────┘               └────────┬─────────┘
                          │                                 │
                 ┌────────▼────────┐               ┌────────▼─────────┐
                 │  GitHub Pages   │               │  USDC escrow on  │
                 │  (docs/) — UI   │               │  Base — payment  │
                 └─────────────────┘               └──────────────────┘
```

Component-level status detail (see the legend above) lives in the table
below, not inside the diagram — a diagram should show structure, a table
should show status, so neither has to be hand-re-aligned every time a
component's state changes.

| Component | Status | Notes |
|---|---|---|
| `agents/run.py` | [OK] | Hourly bounty-cycle orchestration |
| `agents/investigate.py` | [OK] | Deep-investigation engine, real recon+scoring |
| Groq LLM tier | [OK] | Frontier-model fallback chain, see `agents/llm.py` |
| `skillforge/tools/static/slither.sh` | [OK] | Static analysis wrapper |
| `agents/acp_fulfill.py` / wallet | [WIP] | ACP job fulfillment + wallet scaffolding |
| `skillforge/harvest.py` | [OK] | Hourly CVE/tool harvest |
| `skillforge/toolcheck.py` | [OK] | 6x/day tool smoke-test |
| `skillforge/synthesize.py` | [OK] | Daily skill distillation → PR |
| Security tool tiers | [OK] | 13 tools registered across static/fuzzing/ai-redteam/recon |
| `skillforge/memory/` | [OK] | Shared append-only memory base |

## Components

### 1. Python engine — `agents/` [OK] (the CI workhorse)
Runs hourly in GitHub Actions (`.github/workflows/bounty-cycle.yml`).
- **`run.py`** — single-pass orchestrator. `ask_llm()` (Groq `llama-3.1-8b-instant`,
  3-retry rate-limit backoff) + `run_slither()` (30s timeout). Dual mode via
  `--review-repo` → bounty reports vs. self-review reports.
- **`main.py`** — `VAPE` (investigator) + `HACK` (red-team auditor) over fetched bounties.
- **`vape.py` / `hack.py`** — persona engines with `vape_system.md` / `hack_system.md` prompts.
- **`tools.py`** — `fetch_bounties()`, `log_report()`.
- **`acp_fulfill.py` / `wallet.py`** [WIP] — ACP job fulfillment + wallet scaffolding (signing via ACP CLI).
- **`investigate.py`** [OK] — deep-investigation engine, CertiK-style scoring (risk is the default,
  not the exception — see README's table for the full check list). Every real verdict is
  permanent in `intel/investigations/ledger.json`; auto mode never re-investigates an address
  already on record, `--address` always forces a re-check (hired job / deliberate deep-dive).
  `fail-list.md`/`caution-list.md`/`pass-list.md` regenerate from the ledger every run.
- **`review_ledger.py`** [OK] — self-review: re-checks the oldest-reviewed addresses per list
  against fresh data (pass/caution weekly, fail monthly, `review-ledger.yml`), logs a real
  finding when a past verdict drifts. This is VAPE auditing its own track record, not just
  producing new ones.
- **`token_scan.py`** [OK] — free Hunt console + paid x402 quick-check, same keyless checks as
  `investigate.py` minus the ones needing an optional Etherscan key. Ported field-for-field to
  `worker/src/scan.ts` and `docs/assets/app.js`, kept honest by `scan-parity.yml`.
- **`scout.py`** [OK] — bounty-radar triage, rule-based fit scoring (no LLM), hourly via `scout.yml`.
- **`self_improve.py`** [OK] — finds one real, evidence-backed issue, priority order: (1)
  unaddressed CRITICAL/HIGH findings from the AI red-team tools below — closes the loop
  from "VAPE discovers it's vulnerable" to "VAPE proposes to fix itself" — then (2) pyflakes
  bugs, then (3) tool-registry gaps (never an open-ended LLM guess). Has `builder.py`
  propose a fix grounded in the actual target file, opens a real PR via `skillforge/mcp.py`'s
  `GitHubMCPWrapper` for human review (never auto-merges), and logs a "lesson" to
  `skillforge/memory/lessons.jsonl` every cycle — the missing link that now feeds
  self-improvement's own real work into the same Memory `skillforge/synthesize.py` distills
  from. `skillforge/memory/self_improve_state.json` tracks which findings already got a PR
  so the same one isn't re-targeted forever.
- **`build_request.py`** [OK] — the concrete "VAPE can build tools/apps/anything needed"
  capability: label a GitHub issue `vape-build` (real-time via `build-request.yml`'s
  `issues: labeled` trigger, not polled) and `builder.py`'s new `generate_project()`
  attempts a real multi-file implementation (parses `### FILE: path` blocks, rejects path
  traversal/absolute paths, caps file count/size). Files land in an isolated
  `build-requests/issue-<N>-<slug>/` directory via a PR — never applied to the real codebase
  automatically. Same two gates as `self_improve.py`: Builder's security validation, then
  human PR review.
- **`redteam.py`** [OK] — real prompt-injection test against VAPE's own report pipeline: crafts
  a malicious token symbol, runs it through the real `investigate.py -> run.py` grounding
  path and a real LLM call, judges the actual output, and logs a real finding if it's
  hijacked (daily via `redteam.yml`). See `agents/run.py::_build_grounding()` for the
  untrusted-data framing this test verifies.
- **`skillforge/tools/ai-redteam/`** [OK] — garak (native `groq` generator), promptfoo (native
  `groq:` provider, config generated from the real `VAPE_REPORT_SYSTEM`), and deepteam
  (`vape_deepeval_model.py` wraps `agents/llm.py` as the simulator+judge — zero new
  cost/secrets) all wired against VAPE's real production model, daily via
  `redteam-deep.yml`. See `skillforge/skills/ai-agent-redteam.md`.

### 2. SKILLFORGE — `skillforge/` [OK] (self-improving skill+tool ecosystem)
Zero-local-compute skill growth via GitHub Actions. See `skillforge/MANIFEST.md`.
- **harvest** (hourly) — real CVE + tool-release intel, no LLM.
- **toolcheck** (6×/day) — installs & verifies 13 security tools on runners, no LLM.
- **synthesize** (daily) — Groq distills harvested data → opens a PR.
- **Tool tiers:** static (slither/aderyn/mythril) · fuzzing (echidna/foundry) ·
  ai-redteam (garak/promptfoo/deepteam) · recon (token_safety/contract_recon/wallet_trace/base_rpc/market_data).
- **Memory:** append-only `memory/` (tools-registry.json, findings/skills/lessons.jsonl, INDEX.md).
- **Skills:** playbooks in `skillforge/skills/` (sc-static-analysis, ai-agent-redteam, onchain-recon-forensics).

### 3. intel/ pipeline [OK] (the audit trail)
Timestamped real-data outputs committed continuously: `reports/`, `audits/poc-reports/`,
`broadcasts/`, `bounty-radar/`, `engagements/`, `catalog/`. Synced to the HF Space via
`sync-to-hub.yml`.

### 4. ACP job monitor [OK] (autonomous revenue)
Catches incoming ACP jobs and negotiates → funds → completes at near-zero compute.
3 layers: persistent `acp events listen` daemon (zero LLM) → drain+triage loop (zero LLM)
→ reasoning handler that fires only on a real funded job. 14 live offerings; USDC escrow on Base.
*(Operational layer; runs on the host alongside the repo.)*

### 5. UI — `app.py` / `docs/` [OK]
Gradio app (`app.py`, `requirements.txt: gradio`) for the HF Space; `docs/index.html` is
VAPE's public site — narrative case-file pages over the same real data (investigations,
reputation, TVL, Intel Explorer), wallet connect + a wallet profile — portfolio, 24h P&L,
an Alchemy+CoinGecko-backed cost-basis estimate, and case history
(`docs/assets/wallet.js`/`profile.js`) — and hiring surfaces for both payment rails: an
x402 pay-per-call panel backed by `worker/` (Cloudflare Worker/Deno Deploy, see
`docs/DEPLOYMENT.md` section E) and an ACP panel surfacing the real job lifecycle in
`docs/ACP_PROTOCOL.md`.
Still zero-build — `docs/assets/*.js` are plain files, no bundler.

## Data-flow summary
Real sources → engines analyze → findings written to `intel/` (audit trail) and
SKILLFORGE memory (learning) → surfaced via UI/broadcasts → monetized via ACP jobs.
Every loop is grounded in **real data only** — no simulated or hypothetical output.

## Runtime map
| Runtime | Trigger | Compute | State |
|---|---|---|---|
| Python engine | GH Actions hourly | free runner | reports/ commits |
| SKILLFORGE | GH Actions (hourly/6x/daily) | free runner | skillforge/memory |
| Node agent | local `npm start` | local | in-memory + intel/ |
| ACP monitor | persistent daemon | ~zero idle | acp-monitor/state.json |

## Current vs. future
**Now:** autonomous hourly LLM+slither reports, SKILLFORGE 13-tool verification, intel
audit trail, ACP job monetization, self-review PRs.
**Next:** wire Node fetchers to grounded targets, richer UI, external-target auditing
(beyond self-repo), persistent cross-run agent memory, full ACP deliverable automation.
