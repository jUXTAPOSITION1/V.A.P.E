# V.A.P.E. Architecture

> Status legend: [OK] implemented & running · [WIP] partial/scaffolded · [TBD] planned

V.A.P.E. is an autonomous on-chain security & intelligence operation. It runs as
**several cooperating runtimes** — a CI intelligence engine, a self-improving skill
ecosystem, two independent real-money commerce rails, and a standard tool-serving
interface — entirely on GitHub Actions, Cloudflare's free tier, and open-source
tooling. Zero required cost to run; an optional paid frontier-model upgrade for the
calls that benefit most from it, and real USDC settling on Base mainnet for every
paid engagement, human or agent.

## High-level flow

```
                          ┌──────────────────────────────────────────┐
                          │            DATA SOURCES (real)            │
                          │  Base RPC · Etherscan V2 · DexScreener    │
                          │  GoPlus · CoinGecko · DeFiLlama · CVEs    │
                          │  Immunefi/Sherlock · X/@based_vape        │
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
                 │ engagements/    │               │                  │
                 └────────┬────────┘               └────────┬─────────┘
                          │                                 │
                 ┌────────▼────────┐               ┌────────▼─────────┐
                 │  GitHub Pages   │               │  USDC escrow on  │
                 │  (docs/) — UI   │               │  Base — payment  │
                 │  + worker/x402  │               │                  │
                 └─────────────────┘               └──────────────────┘
```

A fourth, orthogonal piece — `mcp_servers/vape_mcp.py` — exposes VAPE's own real
tools (investigation, wallet forensics, DefiLlama intel, bounty radar, Memory) over
the standard Model Context Protocol so any MCP host (Claude, Cursor, a custom agent)
can call them directly; see component 6 below.

### How VAPE gets paid — two independent, real-money rails

31 live offerings total (`data/reputation.json`'s `capabilities.offerings_live`): 27 are
x402-payable (instant, no account needed), 4 need a real ACP job (manual/
SKILLFORGE-tool-tier work no synchronous HTTP route can do in a few seconds). Each
rail settles into its own wallet — x402 revenue into `PAY_TO_ADDRESS`
(`worker/wrangler.toml`, the same wallet holding VAPE's self-registered ERC-8004
identity NFT), ACP escrow into VAPE's separate ACP wallet (`docs/ACP_PROTOCOL.md`)
— neither is a demo; the x402 side runs on **Base mainnet** via Coinbase Developer
Platform's hosted facilitator, real USDC, real settlement transactions.

```
┌─────────────────────────────┐        ┌──────────────────────────────────────┐
│         ACP RAIL            │        │              x402 RAIL                │
│  Virtuals Protocol escrow   │        │      worker/ (Cloudflare, Hono)       │
│                             │        │                                        │
│ job.created ──► set-budget  │        │  buyer/DATA AGENT signs EIP-3009      │
│      │        (VAPE)        │        │  authorization ──► GET /scan|/data/*  │
│      ▼                      │        │      │                                │
│ job.funded ──► real tool    │        │      ▼                                │
│      │      runs (SKILLFORGE│        │  @x402/hono middleware verifies with  │
│      │      tier / manual)  │        │  CDP's hosted facilitator, runs the    │
│      ▼                      │        │  real handler (handlers.ts/           │
│  submit ──► client          │        │  dataHandlers.ts — TS port of         │
│  deliverable    completes   │        │  acp_fulfill.py/defillama.py), THEN    │
│      │                      │        │  settles on-chain                     │
│      ▼                      │        │      │                                │
│  escrow released to VAPE    │        │      ▼                                │
│  (4 ACP-only offerings:     │        │  onAfterSettle logs real payer/tx_hash │
│  wallet_recon, whale_watch, │        │  to KV (lib/jobLog.ts) ──► live feed   │
│  forensics_deep,            │        │  (docs/assets/x402feed.js), tx linked  │
│  partner_referral)          │        │  straight to Basescan                  │
└─────────────────────────────┘        └──────────────────────────────────────┘
              │                                          │                                          │
              ▼                                          ▼
   USDC settles on Base mainnet into          USDC settles on Base mainnet into
   VAPE's ACP wallet (docs/ACP_PROTOCOL.md)   PAY_TO_ADDRESS, 0x8aAB9a6d...Ce15
                                                          ▲
                                                          │
     DATA AGENT (agents/data_agent.py) closes the loop from the OTHER side:
     every real investigate.py run recruits its own dedicated, funded wallet
     (a separate wallet from PAY_TO_ADDRESS — DATA AGENT is the payer here,
     not the payee) to hire 1 of the x402 offerings above against the token
     under review — real USDC leaves DATA AGENT's wallet through the exact
     same rail an external human buyer would use, capped at 48 hires/day
     (2/hour).
```

The 27 x402 routes: 6 priced security checks (`exploit_check` … `dossier_check`,
$0.01-$0.10) + `bounty_deep_dive` ($1, async — pays, then dispatches either
`.github/workflows/deep-dive-bounty.yml` (an on-chain address target — real
Slither run + Halmos symbolic testing + Mythril symbolic-execution scan +
Aderyn static AST analysis + frontier-model source review) or
`.github/workflows/external-bounty-audit.yml` (a GitHub owner/repo target,
e.g. Move/Sui or any bounty program's own source repo — `agents/external_audit.py`),
returning immediately either way since neither can finish inside a Worker's
request window) + 5 more offerings closing the earlier ACP/x402 parity gap
(`deep_contract_audit`, `tx_decode`, `community_intel_broadcast`,
`bulk_safety_bundle`, and the new synchronous `website_review`) + 15 DefiLlama/
market-data micro-tools ($0.01-$0.25 each — `token_intel`, `chain_overview`,
`yields`, `stablecoins`, `bridges`, `wallet_pnl_deepdive`,
`prediction_market_odds`, etc. — `derivatives` was retired 2026-07-14 when
DefiLlama paywalled its overview/derivatives endpoint with no free equivalent).
Advertised for discovery
via the x402 Bazaar extension and a claimed listing on
[402index.io](https://402index.io) (`/.well-known/402index-verify.txt` proves domain
ownership). A handful of free, unpaid Alchemy-backed routes (`/portfolio`, `/nfts`,
`/network-status`, `/prices`, `/cost-basis`) back the site's wallet profile and
metrics strip instead of hitting public RPC directly — Cloudflare's Cache API means
every visitor shares one cached upstream call instead of paying for one each.

Component-level status detail (see the legend above) lives in the table
below, not inside the diagram — a diagram should show structure, a table
should show status, so neither has to be hand-re-aligned every time a
component's state changes.

| Component | Status | Notes |
|---|---|---|
| `agents/run.py` | [OK] | Hourly bounty-cycle orchestration |
| `agents/investigate.py` | [OK] | Deep-investigation engine, real recon+scoring, cross-chain |
| `agents/scout.py` | [OK] | Bounty-radar triage (real bounty/incident track separation + VAPE-fit classification) + strategic briefing + real, cross-chain incident-forensics action |
| `agents/bounty_ops.py` | [OK] | Bounty Ops: Grok-4.3 checklists + progress tracking for VAPE-fit live bounty programs |
| `agents/security_sweep.py` | [OK] | Incident-forensics pipeline (any chain `EVM_CHAINS` supports, high-value leads act regardless of age) |
| `agents/engagements.py` | [OK] | Real per-lead engagement status (never a fabricated outreach/signup) |
| `agents/defillama.py` | [OK] | Full DefiLlama API surface: TVL, yields, fees, stablecoins, bridges, token intel |
| `agents/codex_data.py` / `worker/src/lib/codex.ts` | [OK] | Codex.io GraphQL client (Python + TS port) — trending tokens, holders, wallet PnL. Live on-site via the worker's free `/virtuals-snapshot` + `/trending-base` routes (Virtuals Protocol panel + Trending on Base list); wallet PnL still needs the paid deep-dive offering wired. Launchpad tracking is subscription-only on Codex's side, not yet wired |
| `agents/data_agent.py` | [OK] | DATA AGENT — VAPE's own paying customer, real x402 hires per investigation |
| LLM tier | [OK] | Frontier model + multi-provider free fallback chain, see `agents/llm.py` |
| `mcp_servers/vape_mcp.py` | [OK] | Standard MCP server, 17 real tools — see component 6 |
| `skillforge/tools/static/slither.sh` | [OK] | Static analysis wrapper |
| `agents/acp_fulfill.py` | [OK] | ACP job fulfillment bridge — real deliverables from token_scan/data_fetchers/investigate |
| `worker/` (x402) | [OK] | 27 real, mainnet-settled routes (Cloudflare + Hono) — see component 4 |
| Live offerings | [OK] | 31 total: 27 x402-payable, 4 ACP-only — see component 4 |
| `skillforge/harvest.py` | [OK] | Hourly CVE/tool harvest |
| `skillforge/toolcheck.py` | [OK] | 6x/day tool smoke-test |
| `skillforge/synthesize.py` | [OK] | Daily skill distillation → PR |
| Security tool tiers | [OK] | 16 tools registered across static/symbolic/fuzzing/ai-redteam/recon |
| `skillforge/memory/` | [OK] | Shared append-only memory base |

## Components

### 1. Python engine — `agents/` [OK] (the CI workhorse)
`run.py`'s bounty-hunt + self-review passes run hourly (`.github/workflows/bounty-cycle.yml`);
`investigate.py`'s auto-target deep dive — the site's Featured Investigation spotlight —
runs on its own faster cadence, every 30 minutes (`.github/workflows/featured-investigation.yml`),
decoupled so a fresher investigation cadence doesn't multiply the cost of the rest of
the hourly cycle.
- **`run.py`** — single-pass orchestrator. `ask_llm()` (Groq `llama-3.1-8b-instant`,
  3-retry rate-limit backoff) + `run_slither()` (30s timeout). Dual mode via
  `--review-repo` → bounty reports vs. self-review reports. (The original `main.py`/
  `vape.py`/`hack.py`/`tools.py` persona-engine layer this once called into no longer
  exists — `run.py` + `investigate.py` are the real current path; `vape_system.md`/
  `hack_system.md` now feed the persona prompt directly.)
- **`acp_fulfill.py`** [OK] — ACP job fulfillment bridge: given an offering name +
  requirement, runs the real tool (`token_scan`/`data_fetchers`/`investigate`) and returns
  a structured deliverable. Wallet signing happens via the separate ACP CLI, not a repo file.
- **`investigate.py`** [OK] — deep-investigation engine, CertiK-style scoring (risk is the default,
  not the exception — see README's table for the full check list). Every real verdict is
  permanent in `intel/investigations/ledger.json`; auto mode never re-investigates an address
  already on record, `--address` always forces a re-check (hired job / deliberate deep-dive).
  `fail-list.md`/`caution-list.md`/`pass-list.md` regenerate from the ledger every run.
- **`review_ledger.py`** [OK] — self-review: re-checks the oldest-reviewed addresses per list
  against fresh data (pass/caution weekly, fail monthly, `review-ledger.yml`), logs a real
  finding when a past verdict drifts. This is VAPE auditing its own track record, not just
  producing new ones.
- **`critic.py`** [OK] — same-cycle structural self-check, run inside `investigate()`
  immediately after `score()`. Where `review_ledger.py` is retrospective (did the REAL WORLD
  change under an old verdict?), the critic is immediate (does THIS investigation's own
  reasons/positive_signals/verdict/score actually agree with the raw evidence and with
  `score()`'s own declared invariants — verdict/score bands, the legitimacy cap, honeypot/
  verified/renounced claims grounded against the raw GoPlus/verification data?). Rule-based
  only, never mutates the verdict — a real contradiction is logged to
  `skillforge/memory/lessons.jsonl` and surfaced in the report's "Critic Self-Audit" section
  for `self_improve.py`/a human to triage.
- **`token_scan.py`** [OK] — free Hunt console + paid x402 quick-check, same keyless checks as
  `investigate.py` minus the ones needing an optional Etherscan key. Ported field-for-field to
  `worker/src/scan.ts` and `docs/assets/app.js`, kept honest by `scan-parity.yml`.
- **`scout.py`** [OK] — bounty-radar triage. Every opportunity is classified into a real
  `track` — `"incident"` (historical DeFiLlama hacks, a forensics lead — see the Threat Ledger)
  or `"bounty"` (a real live program) — and every bounty-track entry additionally gets
  `vapeFit`/`vapeFitReason` (does its real scope match Solidity/EVM `deep_dive_audit.py` or
  Move/Sui `external_audit.py` — excluding web/mobile-only scope and post-incident
  recovery/negotiation "bounties") and its own `bountyFitScore` (fit + reward + chain + freshness,
  deliberately NOT the incident formula's raw-dollar-size weighting — this was the fix for a real
  bug where a $58M post-incident recovery offer was outranking a $250k real smart-contract review
  program). A capped, honest liveness recheck (`_recheck_liveness()`) HTTP-pings stale bounty URLs
  so static seed data doesn't silently rot forever. Also runs the frontier-model strategic
  briefing every cycle, and a real action step (`_act_on_incidents()`) that delegates to
  `security_sweep.py`'s address-resolution pipeline on any chain `investigate.py` supports — not
  just Base, and large leads (Kelp/Balancer V2/Matcha-scale) qualify regardless of age
  (`ATTACK_RESPONSE_HIGH_VALUE_USD_M`). Hourly via `scout.yml`.
- **`bounty_ops.py`** [OK] — Bounty Ops: selects the top VAPE-fit live bounty programs from
  `scout.py`'s classification and, for each one VAPE actively tracks, generates/refreshes a real
  Grok-4.3 checklist (what to do, which of VAPE's two real tools to run, what to check against
  `skillforge/memory/security_standards.json`'s real taxonomy) with a recurring, append-only
  progress log — a checklist item's done-state is never reset by a later run. Cross-references
  VAPE's own real audit output (`intel/audits/poc-reports/`, `hack-sweep-reports/`,
  `external-bounties/`) by filename token overlap so a program links straight to VAPE's own
  report the moment one exists. Output: `intel/bounty-radar/bounty-ops/<slug>.json` + `INDEX.md`.
  Renders on the site as the Bounty Command Center's "Bounty Ops — VAPE-Fit, Live" panel
  (`docs/assets/app.js::bounties()`), searchable client-side, separate from the Threat Ledger's
  historical-incident feed. Runs after SCOUT hourly, via `scout.yml`.
- **`engagements.py`** [OK] — revives `intel/engagements/`, replacing pre-repo fabricated seed
  data (a templated audit stub, cold-outreach emails to real hack victims — see
  `intel/archive/legacy-seed-engagements/README.md`) with a real per-lead status derived from
  `skillforge/memory/attack_response_state.json`: a resolved incident cites the real
  address/verdict/report; static seed-platform leads (Immunefi/Cantina/Sherlock/etc.) are
  honestly recorded as "tracked only, no automated engagement path" rather than a fictional
  signup. Idempotent log, always-current `intel/engagements/STATUS.md`. Runs after SCOUT hourly.
- **`defillama.py`** [OK] — the full DefiLlama API surface (TVL, protocols, fees/revenue, yield
  pools, stablecoins, bridges, token price/age intel) in one keyless module, feeding
  `investigate.py`'s scoring, the worker's `/defillama/*` x402 endpoints, and the site's DefiLlama
  panel.
- **`data_agent.py`** [OK] — DATA AGENT, VAPE's own paying customer: recruited mid-investigation
  to hire 1 of VAPE's own $0.01 x402 market-data offerings against the token under review,
  using its own funded wallet (`DATA_AGENT_PRIVATE_KEY`) and the real x402 payment rail, tagged
  `X-VAPE-Client: data-agent` for deterministic CDP/VAPOR alternation instead of the worker's
  usual coin flip — capped at 48 hires/day (2/hour) and gated to at most once every 30m
  regardless of how often investigate.py itself runs, results fold into the report's
  "Data Agent Intel" section.
- **`intel_common.py` / `security_sweep.py` / `base_sweep.py` / `sentiment_sweep.py` /
  `virtuals_sweep.py` / `macro_sweep.py` / `mainnet_patch_check.py` / `bug_bounty_intel.py`**
  [OK] — revives the intel/reports/{security,base,sentiment,virtuals,macro,mainnet-patch-check,
  bug-bounty-intel}-*.md sweeps, which used to run as ad hoc Claude Code sessions (never
  committed code) until they all silently stopped 2026-07-01 with zero trace in git history.
  Same design rule as `scout.py`: the headline verdict/score is computed deterministically
  from real data (`data_fetchers.py` + `skillforge/research.py`'s live web search), the LLM
  only narrates what the real data means. Scheduled via `intel-sweeps.yml` — security/base/
  virtuals 4x/day, sentiment 2x/day, macro daily, the two follow-up checks weekly.
  `security_sweep.py` also writes `data/attack-feed.json` (real, dated incidents over a
  rolling 56-day/8-week window from the same hacks feed, powering the site's homepage
  ticker + "Threat Ledger" section — see `docs/assets/attackfeed.js`). Each incident carries
  its own real `source_url` when DeFiLlama's raw feed actually has one (the original
  disclosure/article — `agents/data_fetchers.py::_incident_source_url()`, checked
  defensively, never fabricated), separate from VAPE's own `analysis_report` link below —
  the Threat Ledger links both independently when present. And, for any new
  Base-chain incident it can resolve a real on-chain address for via web search, runs
  `investigate.py`'s actual forensics pipeline against it (`attempt_incident_forensics()`)
  — never a fabricated address, honestly skipped when one can't be found.
  `investigate.py::hack_correlation()` was also fixed to genuinely cross-reference a
  target's risk traits against real incidents in the same feed (citing the specific
  matching incident by name/date/amount) instead of returning generic canned text
  regardless of what the real data showed.
  `security_sweep.py::learn_from_incidents()` closes the loop from "reports/investigates"
  to "learns": every incident within the same 14-day actionable window is run through a
  deterministic keyword classifier (`ATTACK_PATTERNS`) mapping its real `technique` string
  to a known vulnerability class, a concrete prevention measure, and — honestly — whether
  `investigate.py`'s `score()` already has a named check for it or whether this is an
  admitted coverage gap. Where forensics resolved a real Base address, it also backtests
  VAPE's own scoring model against the actual verdict (`PROCEED`/`CAUTION`/`REJECT`) on
  that contract — a `PROCEED` verdict on something that then got exploited is logged as a
  real model miss, not smoothed over. Every lesson is logged once (idempotent via
  `attack_lessons_state.json`) to `skillforge/memory/findings.jsonl`, surfaced in the
  report's "Lessons Learned" section and per-incident in `data/attack-feed.json`/the
  Threat Ledger UI. Nothing here is LLM-guessed — see this module's design law above.
- **`hack_agent.py`** [OK] — writes a real, standalone threat analysis for every incident
  in `data/attack-feed.json`'s window, not just the rule-based lesson tag above. Grounded
  only in that same feed's real fields plus one live web search for public writeups —
  never invents a detail. Written by OCI-hosted xAI Grok 4.3 first (`agents/llm.py::
  ask_oci_grok()`), falling back through `FRONTIER_ORDER` like every other analyst call
  if OCI isn't configured or errors. Idempotent (`skillforge/memory/threat_analysis_state.
  json`); patches each incident's `analysis_report` path back onto `data/attack-feed.json`
  every run (which `security_sweep.py` regenerates fresh each cycle with no knowledge of
  this field), so `docs/assets/attackfeed.js` can render a real per-incident "Full
  analysis" link, not just the feed-wide source-report link. Own schedule
  (`threat-analysis.yml`, 6-hourly) and module, independent of the sweep pipeline.
- **`hack_sweep.py`** [OK] — VAPE's daily proactive vulnerability hunt: escalates a
  small number of CAUTION-verdict entries already in `investigate.py`'s own ledger (real
  addresses from the free hourly auto-cycle) to `deep_dive_audit.py`'s full heavy tool
  suite (Slither/Halmos/Mythril/Aderyn + OCI Grok 4.3 frontier reasoning) — the same
  pipeline paying x402/ACP buyers get for the $1 `bounty_deep_dive` offering, run here
  free against VAPE's own initiative (`engagement="sweep"`, reports land in
  `intel/audits/hack-sweep-reports/`, clearly labeled as non-paid). Own dedup state
  (`skillforge/memory/hack_sweep_state.json`) and daily schedule (`hack-sweep.yml`).
- **`external_audit.py`** [OK] — VAPE's reusable pipeline for a real external bug-bounty
  engagement against any target repo (any language/chain, not just VAPE's own Base/EVM
  investigations) — built for the first real engagement, Momentum's `mmt-v3-core` CLMM
  (Move/Sui) via HackenProof. Fetches real source (keyless, `raw.githubusercontent.com` +
  the public git/trees API), detects language, and runs a rigorous frontier-LLM (OCI Grok
  4.3) line-by-line review with a language-appropriate system prompt (a dedicated
  Move-specific one distinguishing what Move's resource-safety model already guarantees
  from what it doesn't). Deliberately does not invoke Slither/Mythril/Aderyn/Halmos —
  those are Solidity-specific and need either a live on-chain address or a compilable
  Foundry project; a genuinely Solidity on-chain target should go through
  `deep_dive_audit.py` instead. Reachable two ways: manual `workflow_dispatch`
  (`external-bounty-audit.yml`) for a deliberate scoped engagement, or the same
  x402 `/scan/bounty_deep_dive` route as `deep_dive_audit.py` — supply an
  `owner`+`repo` instead of an `address` and the worker dispatches this pipeline
  instead (see docs/assets/hire.js's per-Bounty-Ops-program "Hire VAPE" flow).
  For Move targets, also runs bounded formal verification
  (`agents/scaffold_move_target.py`): scaffolds a real local Move package from the
  target's own fetched source + real Move.toml, has the frontier LLM draft speculative
  Move Prover spec properties (mirrors `scaffold_foundry_target.py`'s Halmos-hypothesis
  pattern, since real external targets rarely ship existing spec blocks), and runs
  `sui-prover` against them if it's installed this run — deliberately not
  auto-installed in any workflow (no Linux release published; needs a from-source
  build with Boogie + Z3). Not scheduled — dispatched per engagement (manually,
  or via the x402 route above).
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
  path and a real LLM call, and judges the RECONCILED output (`agents/run.py::
  _reconcile_report()`), not the raw model response — records both whether the raw model
  itself resisted and whether the exploit actually reached what would be published, logging
  a real finding only in the latter case (daily via `redteam.yml`). `_build_grounding()`'s
  prompt-level "treat this as inert data" framing did NOT reliably hold on its own — the
  same test succeeded against a real model on five separate dates after that framing shipped
  (see `skillforge/memory/findings.jsonl`) — `_reconcile_report()` is the deterministic
  backstop that actually closes it: a fact computed from the investigation digests
  themselves decides what gets surfaced, never the model's own account of what it read.
  A token symbol can't influence that fact because `investigate.py::_sanitize_symbol()`
  strips `**`/newlines from every attacker-controlled name/symbol before it's ever
  embedded in a digest — closed at the point untrusted data enters the system, with
  `_nonclean_digests()` preferring the last regex match as defense-in-depth on top of
  that (a real gap here, caught by CodeRabbit review on PR #156: an unsanitized symbol
  forging an early fake `**Verdict:**` match could otherwise shadow the real one).
- **`skillforge/tools/ai-redteam/`** [OK] — garak (native `groq` generator), promptfoo (native
  `groq:` provider, config generated from the real `VAPE_REPORT_SYSTEM`), and deepteam
  (`vape_deepeval_model.py` wraps `agents/llm.py` as the simulator+judge — zero new
  cost/secrets) all wired against VAPE's real production model, daily via
  `redteam-deep.yml`. See `skillforge/skills/ai-agent-redteam.md`.

### 2. SKILLFORGE — `skillforge/` [OK] (self-improving skill+tool ecosystem)
Zero-local-compute skill growth via GitHub Actions. See `skillforge/MANIFEST.md`.
- **harvest** (hourly) — pulls new CVEs + security-tool releases into the registry.
- **toolcheck** (6×/day) — installs & smoke-tests all 15 registered security tools on runners,
  updates each one's verified/broken status.
- **synthesize** (daily) — distills a skill/playbook from real findings+lessons via the
  frontier-model chain (`agents/llm.py`'s `FRONTIER_ORDER` — Grok 4.1 Fast first, free
  fallbacks after), opens a PR.
- **Tool tiers:** static (slither/aderyn/mythril) · fuzzing (echidna/foundry) ·
  ai-redteam (garak/promptfoo/deepteam) · recon (base_rpc/market_data/token_safety/
  wallet_trace/contract_recon/hack_feed/fear_greed). `wallet_trace` is Alchemy-backed
  (Base/Eth/Arb/Op) — live-verified against the real Transfers API, see PR #145.
- **Memory:** append-only `memory/` (tools-registry.json, findings/skills/lessons.jsonl, INDEX.md).
- **`memory/graph.py`** [OK] — a deployer/token relationship graph built from the real
  `intel/investigations/ledger.json` (every investigated address's GoPlus-reported
  `creator_address`), zero new data collection, hand-rolled adjacency dicts (no new
  dependency — matches this repo's stdlib-only convention). Generalizes
  `investigate.py`'s `_deployer_repeat_offender()` (which only checks whether ONE prior
  token from the same deployer already tripped CAUTION/REJECT) into a full queryable
  cluster: every token from a deployer, worst-verdict-first, independent of their
  individual verdicts — feeds a distinct "mass-token-factory" scoring signal in `score()`
  and a "Deployer Network" report section. The live ledger already contains a real
  7-token cluster (a brand-impersonation campaign), so this surfaces a genuine pattern,
  not a hypothetical one.
- **Skills:** playbooks in `skillforge/skills/` (sc-static-analysis, ai-agent-redteam, onchain-recon-forensics).

### 3. intel/ pipeline [OK] (the audit trail)
Timestamped real-data outputs committed continuously: `reports/`, `audits/poc-reports/`,
`broadcasts/`, `bounty-radar/`, `engagements/`, `catalog/`. Synced to the HF Space via
`sync-to-hub.yml`.

**Working-tree hygiene:** the repo is the operational store ("GitHub as the brain"),
which stays fast only if the loose-file count stays bounded. `scripts/archive_reports.py`
(weekly `archive-reports.yml`) folds aged report output into one compressed tarball per
(category, month) under `intel/archive/`, keeping a queryable `index.json` manifest
(title/date/threat/summary/sha256 per report) — nothing deleted, everything byte-recoverable,
just moved out of the live tree once past its retention window (short for internal cycle
churn like `repo_review_*`, longer for dashboard-indexed `bounty_report_*`/`intel/reports/*`).
The workflow rebuilds `data/intel-index.json` immediately after archiving so the committed
index never links a report that just moved to cold storage; the dashboard only ever surfaces
the most-recent handful, so it's unaffected. `scripts/repo_stats.py` prints a weekly repo-size /
file-count / memory-log-growth summary so scaling decisions stay driven by real numbers.
The SQLite memory projection (`skillforge/memory/index_db.py`, `data/memory.db`, gitignored
and rebuildable) is the read-side complement: append-only JSONL stays the source of truth,
the DB is a derived queryable index so agents can ask real questions instead of scanning flat files.

### 4. Commerce — ACP job monitor + x402 payment worker [OK] (autonomous revenue)
31 live offerings across two independent, real-money rails — see the payment-rails
diagram above for the full flow. Each settles into its own wallet (x402 revenue
into `PAY_TO_ADDRESS`, ACP escrow into VAPE's separate ACP wallet); neither is a
demo.

**ACP job monitor** (`scripts/acp-*`) catches incoming ACP jobs and negotiates →
funds → completes at near-zero compute. 3 layers: persistent `acp events listen`
daemon (zero LLM) → drain+triage loop (zero LLM) → reasoning handler that fires only
on a real funded job. Escrow-backed on Base, `docs/ACP_PROTOCOL.md` is the full
reference. *(Operational layer; runs on the host alongside the repo.)* Only 4
offerings remain ACP-only (`wallet_recon`, `whale_watch`, `forensics_deep`,
`partner_referral`) — manual or SKILLFORGE-tool-tier work no synchronous HTTP route
can complete in seconds. `tx_decode`, `community_intel_broadcast`,
`bulk_safety_bundle`, and `deep_contract_audit` used to be ACP-only too, until the
x402/ACP parity work gave each a real x402 route (see component 4's x402 list below).

**x402 payment worker** (`worker/`, Cloudflare Workers + Hono, TypeScript) gates 27
routes with `@x402/hono` middleware against **Base mainnet** — real EIP-3009 signed
authorizations, real on-chain settlement, not a testnet demo. Every request is
routed through a real 50/50 hybrid split between VAPOR (our own facilitator,
`x402.duckdns.org`) and Coinbase Developer Platform's hosted facilitator
(`api.cdp.coinbase.com`, JWT-authenticated — see `worker/src/lib/cdpAuth.ts`) —
which one is primary is picked randomly per request, falling back to the other
on any infrastructure failure (`worker/src/lib/facilitatorClient.ts`), so an
outage on either side never takes real revenue down with it, and both
facilitators get genuine, ongoing settlement volume rather than one being a
cold failover path. Two tagged carve-outs to the coin flip (`X-VAPE-Client`
header): a human paying in-browser through the site's wallet-connect flow
always gets CDP as primary (Basescan's "x402 payment" labels are tied to
CDP's known relayer addresses, not anything on-chain-derived); `agents/
data_agent.py`'s own hires get a deterministic, KV-persisted CDP/VAPOR
alternation instead (`worker/src/lib/dataAgentAlternator.ts`), since its
fixed low-volume cadence could otherwise string together a long unlucky run
on one side. Every other route keeps the plain random split. The real
achieved ratio (not just the intended one — a fallback can still occur) is
tracked per job in `worker/src/lib/jobLog.ts` and surfaced via `GET
/x402/stats`'s `by_facilitator` totals. `worker/src/handlers.ts` and `dataHandlers.ts` are
faithful TypeScript ports of `agents/acp_fulfill.py` and `agents/defillama.py` (kept
honest by `scan-parity.yml`'s cross-language diff check), so a $0.01 x402 call and a
free ACP job never disagree. Every real settlement is logged to a Cloudflare KV job
ledger (`worker/src/lib/jobLog.ts`) with the actual payer address and on-chain tx
hash — surfaced on the site's live feed, linked straight to Basescan, not just VAPE's
own word. Advertised via the x402 Bazaar discovery extension and a claimed
[402index.io](https://402index.io) listing — since CDP's facilitator never emits
the header that's supposed to confirm Bazaar indexing succeeded
([x402-foundation/x402#2112](https://github.com/x402-foundation/x402/issues/2112),
still open), `GET /admin/bazaar-status` + `agents/cdp_bazaar_check.py`
(`cdp-bazaar-check.yml`, weekly) check CDP's own discovery catalog directly
instead of trusting a signal CDP doesn't send. The `bounty_deep_dive` route ($1) is the
one async exception: pays via x402, then dispatches either
`.github/workflows/deep-dive-bounty.yml` (`agents/deep_dive_audit.py`, address
target) or `.github/workflows/external-bounty-audit.yml` (`agents/external_audit.py`,
owner/repo target) and returns immediately, since a real Slither run + Halmos
symbolic testing + Mythril symbolic-execution scan + Aderyn static AST analysis +
frontier-model source review can't complete inside a Worker's request window.
Symbolic testing
(`agents/scaffold_foundry_target.py`) scaffolds the target's own verified
source into a throwaway Foundry project, drafts a handful of Halmos `check_*`
properties with the frontier LLM (explicitly labeled hypotheses, never
findings), and runs Halmos for real against them — a second, independent
analysis layer alongside Slither's static pass. Mythril (`myth analyze -a
<address> --rpc <host:port>`) adds a third, independent pass, analyzing the
target's actual deployed bytecode on-chain by address via the target chain's
real public RPC. Aderyn adds a fourth pass, reusing that same scaffolded
Foundry project for a second, independent static AST analysis. Each tool is
skipped cleanly (never a hard dependency) if it isn't on the runner's PATH
this cycle.

**`agents/data_agent.py`** [OK] closes the loop from the buy side: every real
`investigate.py` run recruits DATA AGENT's own funded wallet
(`DATA_AGENT_PRIVATE_KEY`) to hire 1 of the x402 offerings above against the token
under review, using the official x402 Python SDK — real USDC leaves DATA AGENT's
wallet through the exact same rail an external human buyer would use, proving the
payment loop end-to-end on every investigation, not only when someone happens to buy
something. Capped at 48 hires/day (2/hour), and gated to at most once every 30m
(`skillforge/memory/data_agent_quota.json`'s `last_ts`) — decoupled from
`investigate.py`'s own cadence (every 30m via `featured-investigation.yml`) so more
frequent investigations don't translate into more frequent spend.

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

### 6. MCP Server — `mcp_servers/vape_mcp.py` [OK]
Standard Model Context Protocol (`2024-11-05`, JSON-RPC 2.0 over stdio, pure stdlib —
no SDK to install) exposing 17 of VAPE's real tools to any MCP host (Claude, Cursor,
a custom agent): `investigate_token`, `scan_token_safety`, `wallet_trace` (shells out
to the real Alchemy-backed `wallet_trace.sh` rather than re-implementing it),
`contract_source`, `recent_hacks`, `fear_greed`, `global_market`, four
`defillama_*` tools, `bounty_radar`, `memory_search`/`memory_stats`,
`research_search`/`research_scrape`, and `mcp_servers` (VAPE as an MCP *host*,
consuming community search/scrape servers via `skillforge/mcp_client.py`). Two
resources (`vape://reputation`, `vape://intel-index`). See `docs/MCP_SERVER.md`.

## Data-flow summary
Real sources → engines analyze → findings written to `intel/` (audit trail) and
SKILLFORGE memory (learning) → surfaced via UI/broadcasts → monetized via ACP jobs.
Every loop is grounded in **real data only** — no simulated or hypothetical output.

## Runtime map
| Runtime | Trigger | Compute | State |
|---|---|---|---|
| Python engine | GH Actions hourly | free runner | reports/ commits |
| SKILLFORGE | GH Actions (hourly/6x/daily) | free runner | skillforge/memory |
| ACP monitor | persistent daemon | ~zero idle | acp-monitor/state.json |
| MCP server | spawned per-call by host | ~zero idle | stateless (reads live repo data) |

### 7. Quality gates & the model path [OK]/[WIP]
- **`tests/` + `tests.yml`** [OK] — a hermetic, network-free pytest suite pins VAPE's
  deterministic core (`investigate.score()`, threat-level computation, the attack-pattern
  classifier, the archiver round-trip, the safe fmt helpers), gated on every Python-touching
  PR alongside pyflakes over `agents/`+`scripts/`. This is the safety net the self-improvement
  loop needs before it can trust a self-proposed change to scoring or classification.
- **`scripts/build_finetune_dataset.py`** [WIP] — "an LLM of VAPE's own", grounded and
  reproducible: turns VAPE's real operating history — published investigations
  (`intel/investigations/`), sweep reports (`intel/reports/`), its own logged operational
  lessons (`skillforge/memory/lessons.jsonl`), and two optional network-fetched sources
  (`scripts/build_external_corpus.py`'s real NVD CVE + Code4rena audit findings, and
  `scripts/build_pr_history_dataset.py`'s mining of VAPE's own bot-authored PR history) —
  into a chat-format instruction-tuning corpus (`data/finetune/`), where the INPUT is the
  observable recon/data or real task VAPE actually had, and the OUTPUT is the verdict/score/
  trend/code deterministically or independently produced (never an LLM's narrative prose,
  which is deliberately excluded) — so a small-to-mid open-weight model (LoRA/QLoRA) can be
  taught to reason and write code like VAPE across every domain it covers, not to re-distill
  another model's guesses. It does NOT replace `score()` or any sweep's `compute_*_score()`
  (rule-based stays the source of truth); a fine-tuned candidate is graded against the
  frontier tier with the existing promptfoo/deepteam harness (`training/eval_candidate.py`)
  before any real traffic. The corpus grows for free as VAPE keeps operating — see
  `data/finetune/DATASET_CARD.md`. Training itself runs on a user-provisioned GPU box
  registered as a self-hosted GitHub Actions runner (`training/setup_runner.sh` +
  `.github/workflows/train-vape-model.yml`) — QLoRA on Gemma via `training/train_lora.py`,
  with a parallel Vertex AI supervised-tuning path also available
  (`scripts/convert_dataset_vertex.py`) as a hedge against GPU quota/capacity risk.

## Current vs. future
**Now:** autonomous hourly LLM+slither reports, SKILLFORGE 15-tool verification, real
cross-chain incident-forensics action (not just Base, large leads act regardless of age),
a real per-lead engagement record, a full DefiLlama intelligence layer, a standard MCP
server exposing 17 real tools to any host, intel audit trail, ACP job monetization,
self-review PRs, deterministic-core test gate, working-tree archiving + repo-health
monitoring, and a reproducible fine-tune corpus spanning VAPE's own investigation/sweep/
lesson/PR history plus real third-party CVE and audit-contest ground truth.
**Next:** richer UI, external-target auditing (beyond self-repo), persistent
cross-run agent memory, full ACP deliverable automation, and a first LoRA/Vertex fine-tune
graded against the frontier tier before it serves any real "fast"-tier traffic.
