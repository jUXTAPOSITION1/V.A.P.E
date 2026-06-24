# V.A.P.E. Architecture

> Status legend: ✅ implemented & running · 🟡 partial/scaffolded · ⚪ planned

V.A.P.E. is an autonomous on-chain security & intelligence operation. It runs as
**two cooperating runtimes** plus a **self-improving skill ecosystem**, all on free
tiers (Groq + GitHub Actions + open-source tooling).

## High-level flow

```
                          ┌──────────────────────────────────────────┐
                          │            DATA SOURCES (real)           │
                          │  Base RPC · Etherscan V2 · DexScreener   │
                          │  GoPlus · CoinGecko · DeFiLlama · CVEs   │
                          │  Immunefi/Code4rena · X/@based_vape      │
                          └───────────────┬──────────────────────────┘
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        │                                 │                                 │
┌───────▼────────┐              ┌─────────▼─────────┐             ┌─────────▼─────────┐
│  PYTHON ENGINE │              │   NODE AGENT      │             │    SKILLFORGE     │
│  (CI, hourly)  │              │ (local, periodic) │             │ (GitHub Actions)  │
│  agents/*.py   │              │   src/*.js        │             │  skillforge/*     │
│                │              │                   │             │                   │
│ ✅ run.py       │              │ 🟡 vape.js loop   │             │ ✅ harvest hourly │
│ ✅ vape/hack    │              │ 🟡 analyzer       │             │ ✅ toolcheck 6x/d │
│ ✅ Groq LLM     │              │ 🟡 scanner        │             │ ✅ synthesize→PR  │
│ ✅ slither      │              │ 🟡 fetcher        │             │ ✅ 13 sec tools   │
│ 🟡 acp/wallet   │              │ 🟡 acp/protocol   │             │ ✅ memory base    │
└───────┬────────┘              └─────────┬─────────┘             └─────────┬─────────┘
        │                                 │                                 │
        └─────────────────┬───────────────┴─────────────────┬───────────────┘
                          │                                 │
                 ┌────────▼────────┐               ┌────────▼─────────┐
                 │   intel/  (✅)   │               │  ACP MONITOR (✅) │
                 │ reports/audits/ │               │ events→triage→   │
                 │ broadcasts/     │               │ negotiate/fund/  │
                 │ bounty-radar/   │               │ complete jobs    │
                 └────────┬────────┘               └────────┬─────────┘
                          │                                 │
                 ┌────────▼────────┐               ┌────────▼─────────┐
                 │ GitHub Pages /  │               │ Virtuals ACP     │
                 │ HF Space (UI)🟡 │               │ USDC escrow $$$ ✅│
                 └─────────────────┘               └──────────────────┘
```

## Components

### 1. Python engine — `agents/` ✅ (the CI workhorse)
Runs hourly in GitHub Actions (`.github/workflows/bounty-cycle.yml`).
- **`run.py`** — single-pass orchestrator. `ask_llm()` (Groq `llama-3.1-8b-instant`,
  3-retry rate-limit backoff) + `run_slither()` (30s timeout). Dual mode via
  `--review-repo` → bounty reports vs. self-review reports.
- **`main.py`** — `VAPE` (investigator) + `HACK` (red-team auditor) over fetched bounties.
- **`vape.py` / `hack.py`** — persona engines with `vape_system.md` / `hack_system.md` prompts.
- **`tools.py`** — `fetch_bounties()`, `log_report()`.
- **`acp.py` / `wallet.py`** 🟡 — ACP reporting + wallet scaffolding (signing via ACP CLI).
- **`redteam.py` / `self_improve.py` / `create_pr.py` / `self_pr.py`** — AI red-team + self-improvement → opens PRs.

### 2. Node agent — `src/` 🟡 (continuous-investigation lifecycle)
Local/long-running runtime (`package.json`, ESM, `main: src/agents/vape.js`).
- **`agents/vape.js`** — `VAPEAgent` class: `initialize()`, `startInvestigation()`
  (`setInterval` cycles), `runInvestigationCycle()` → calls the modules below.
- **`blockchain/analyzer.js`** — `analyzeRecentActivity()` over Base RPC.
- **`security/scanner.js`** — `scanForThreats()`.
- **`data-fetchers/fetcher.js`** — `getMarketMetrics()`.
- **`acp/protocol.js`** — `reportFindings()` + alerting.
- **`config/logger.js`** — pino logging.
- Read-only provider today (no signing). Not wired into CI (CI uses the Python engine).

### 3. SKILLFORGE — `skillforge/` ✅ (self-improving skill+tool ecosystem)
Zero-local-compute skill growth via GitHub Actions. See `skillforge/MANIFEST.md`.
- **harvest** (hourly) — real CVE + tool-release intel, no LLM.
- **toolcheck** (6×/day) — installs & verifies 13 security tools on runners, no LLM.
- **synthesize** (daily) — Groq distills harvested data → opens a PR.
- **Tool tiers:** static (slither/aderyn/mythril) · fuzzing (echidna/foundry) ·
  ai-redteam (garak/promptfoo/deepteam) · recon (token_safety/contract_recon/wallet_trace/base_rpc/market_data).
- **Memory:** append-only `memory/` (tools-registry.json, findings/skills/lessons.jsonl, INDEX.md).
- **Skills:** playbooks in `skillforge/skills/` (sc-static-analysis, ai-agent-redteam, onchain-recon-forensics).

### 4. intel/ pipeline ✅ (the audit trail)
Timestamped real-data outputs committed continuously: `reports/`, `audits/poc-reports/`,
`broadcasts/`, `bounty-radar/`, `engagements/`, `catalog/`. Synced to the HF Space via
`sync-to-hub.yml`.

### 5. ACP job monitor ✅ (autonomous revenue)
Catches incoming ACP jobs and negotiates → funds → completes at near-zero compute.
3 layers: persistent `acp events listen` daemon (zero LLM) → drain+triage loop (zero LLM)
→ reasoning handler that fires only on a real funded job. 14 live offerings; USDC escrow on Base.
*(Operational layer; runs on the host alongside the repo.)*

### 6. UI — `app.py` / `docs/` 🟡
Gradio app (`app.py`, `requirements.txt: gradio`) for the HF Space; `docs/index.html`
is the GitHub Pages "Bounty Command Center" status page. Currently minimal/status-level.

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
