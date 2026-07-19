# V.A.P.E. — Architecture Roadmap: More Agents, More LLMs

Strategy for deepening ACP integration and expanding the agent/LLM framework —
while holding the line: **maximum capability, lowest possible compute, real data only.**

> Status: [OK] live · [WIP] in progress · [TBD] proposed

---

## 1. Deeper ACP Integration (GitHub + VAPE → revenue)

### The bridge ([OK] shipped)
`agents/acp_fulfill.py` maps **ACP offerings → verified real-data tools**, producing a
submit-ready deliverable. This connects the GitHub-built tool tier directly to ACP escrow income.

### Rail decision: ACP **CLI**, not the raw SDK
VAPE already operates on the **ACP CLI** (signer provisioned, 28 offerings live, monitor
catching jobs). We deliberately do **not** `pip install virtuals-acp` + put `ACP_WALLET_KEY`
in `.env`: that would duplicate the rail and reintroduce raw private-key handling. The CLI
stores the P256 signer in a file/keychain backend and signs via its own secure path. The
bridge produces *deliverables*; the CLI does all *signing/submitting*. Keys never touch the
repo or `.env`. (The SDK stays an option only if a future flow the CLI can't do appears.)

**20 of 28 offerings auto-fulfill with zero manual work** — `agents/acp_fulfill.py`'s
`HANDLERS` dict (ported field-for-field to `worker/src/handlers.ts`/`dataHandlers.ts` for
the x402 side) covers all of them:

| Offering | $ | Auto-fulfilled by | Status |
|---|---|---|---|
| token_safety_check | 0.02 | `token_scan.py` (GoPlus+DexScreener) | [OK] auto, x402 |
| liquidity_check | 0.02 | `token_scan.py` (liquidity) | [OK] auto, x402 |
| rug_pull_alert | 0.03 | `token_scan.py` (owner/mint/honeypot) | [OK] auto, x402 |
| exploit_check | 0.01 | `data_fetchers.get_contract_source` | [OK] auto, x402 (needs Etherscan key on runner) |
| market_intel | 0.07 | `build_market_context()` | [OK] auto, x402 |
| dossier_check | 0.10 | `investigate.quick_assess` (score + meme-factory + hack corr + web-reputation search) + declared-socials scrape + frontier-LLM quick source read | [OK] auto, x402 |
| bounty_deep_dive | 50.00 | `agents/deep_dive_audit.py` — real Slither + Halmos symbolic testing (`agents/scaffold_foundry_target.py`) + frontier-model source review, dispatched async via `deep-dive-bounty.yml` (x402 pays first, GH Actions job runs, report lands in `intel/audits/poc-reports/` within 24h) | [OK] auto (async), x402 |
| community_intel_broadcast | 0.10 | `intel/broadcasts/` + `market_data.sh` | [OK] auto, ACP-only |
| 13 DefiLlama market-data tools (token_intel, chain_overview, yields, stablecoins, bridges, etc.) | 0.01 each | `agents/defillama.py` / `worker/src/lib/defillama.ts` | [OK] auto, x402 |
| deep_contract_audit | 1.00 | SKILLFORGE static tier (slither/aderyn/mythril) | [TBD] manual — needs the runner/tool tier, not yet an auto-handler |
| forensics_deep | 2.00 | wallet_trace + contract_recon | [TBD] manual — wallet_trace itself is now [OK] Alchemy-backed and live-verified (PR #145); an auto-handler for this offering still isn't wired |
| wallet_recon | 0.03 | base_rpc / wallet_trace | [TBD] manual, same gap as forensics_deep |
| whale_watch / tx_decode / bulk_safety_bundle / partner_referral | 0.10 / 0.05 / 0.50 / 0.01 | mapped, monitor handler | [TBD] manual |

### Data flow (the loop that earns)
```
ACP job.created ─► monitor triage ─► set-budget (offering price)
                                          │
ACP job.funded  ─► reasoning handler ─► acp_fulfill.fulfill(offering, requirement)
                                          │   (runs real-data tool)
                                   acp provider submit  ◄── deliverable
                                          │
                                   escrow ─► VAPE wallet (USDC, Base)
                                          │
                                   log ─► intel/scans + intel/catalog (audit trail)
```

### Next ACP steps
1. [OK] shipped — **`scripts/acp-monitor/auto_fulfill.py`** imports `acp_fulfill.fulfill`/
   `HANDLERS` directly: the monitor calls it for all 21 auto-offerings, only escalating to
   a human/manual path for the remaining 8. Most jobs settle with **zero LLM cost** (pure
   tool output) — `dossier_check`/`community_intel_broadcast` are the only auto-offerings
   that spend an LLM call at all.
2. [TBD] proposed — **Self-listing refresh from GitHub**: a workflow that regenerates
   offering descriptions from the live tool registry (`skillforge/memory/tools-registry.json`)
   so offerings never drift from real capability.
3. [TBD] proposed — **Dedup + caching**: check for a recent same-target scan before
   re-running one; serve the cached deliverable (faster SLA, lower cost, higher margin).
   No `scans.jsonl`-style cache exists yet — every job runs the real tool fresh.
4. [TBD] proposed — **Reputation loop**: after each completed job, append outcome to
   `lessons.jsonl`; surface success-rate on the dashboard to attract more buyers.
5. **Client side (hire-out)** — for deep_contract_audit jobs needing heavy compute, VAPE
   can *delegate* via `acp browse` → `client create-job` to a specialist agent when that's
   cheaper than running echidna/mythril itself. Spend-to-earn arbitrage.

---

## 2. More Agents (the GitHub multi-agent roster)

Current real agents (`agents/`): VAPE (detective), HACK (red-team), plus self-improve/PR
machinery. Proposed additions — each a focused persona with a system prompt + tool binding,
all running in the **existing free GitHub Actions** (no new infra):

| Agent | Role | Backing tools (already built) | Compute |
|---|---|---|---|
| **SCOUT** [OK] | Bounty-radar triage — ranks DeFiLlama hack/incident leads by numeric fit score (`agents/scout.py`); Immunefi/Sherlock have no stable public API so those stay static seed data until one exists (Code4rena wound down in May 2026, Immunefi absorbed its programs — its seed entries are historical only). Every cycle gets a "Strategic Briefing" (why the top opportunities matter, what VAPE capability each exercises, one next action) on top of the numeric table — insight is also ACTED on, not just narrated: `_act_on_incidents()` delegates to `agents/security_sweep.py`'s verified address-resolution pipeline to trigger a real `agents/investigate.py` investigation whenever an incident's address checks out, on any chain investigate.py supports (not just Base — large leads like Kelp/Balancer V2/Matcha also qualify regardless of age; see `ATTACK_RESPONSE_HIGH_VALUE_USD_M`), shown in the digest's "Actions Taken This Cycle" section | `intel/bounty-radar/*`, DeFiLlama hacks feed, the frontier model via `agents/llm.py`'s `FRONTIER_ORDER` (every cycle, not gated on new entries), `agents/security_sweep.py`'s incident-forensics pipeline | hourly (`.github/workflows/scout.yml`) |
| **LEDGER** [TBD] | Wallet/fund-flow forensics — chain-of-custody graphs | wallet_trace (Alchemy-backed), base_rpc | on-demand |
| **ORACLE** [OK] | Market-anomaly watcher — TVL outflow / depeg / gas-spike / fresh-exploit / extreme-F&G alerts, published to `intel/broadcasts/` (`agents/broadcast.py`) | `data_fetchers.build_market_context()`'s rule-based `anomaly_flags` | every 6h (`.github/workflows/broadcast.yml`), fixed numeric thresholds |
| **CURATOR** [OK] | SKILLFORGE — two real halves: `synthesize.py` distills harvested intel into markdown playbooks; `skillforge_build.py` proposes AND builds real multi-file tools grounded in tool-registry gaps + Memory findings/lessons, opening a PR for review — both go through `agents/llm.py`'s `FRONTIER_ORDER` (Grok 4.1 Fast first, free fallbacks after) | harvest/Memory + `FRONTIER_ORDER` + `builder.py`'s `generate_project()` | daily PR (synthesize) / 2x-daily PR (build) |
| **WARDEN** [TBD] | ACP job QA — validates deliverables before submit (schema + sanity) | acp_fulfill output | per-job, schema/sanity check |
| **DATA AGENT** [OK] | VAPE's own paying customer — recruited by every real investigation (`agents/investigate.py::investigate()`) to hire 1 random $0.01 x402 market-data offering against the token under review, using its own funded wallet (`DATA_AGENT_PRIVATE_KEY`); tagged `X-VAPE-Client: data-agent` for deterministic CDP/VAPOR alternation instead of the worker's usual coin flip; results fold into the report's "Data Agent Intel" section | `agents/data_agent.py`, worker's `/data/*` x402 routes (`worker/src/dataHandlers.ts`) | per-investigation, capped 48 paid hires/day (2/hour) + a 30m minimum interval |

**Design rule:** each agent is **rule-based first, a frontier-model call only when real
reasoning is required.** SCOUT ranks by numeric fit score and gets a frontier-model strategic
briefing every cycle (coverage over conserving that credit, by explicit direction), then acts
on real incidents across any chain investigate.py supports via security_sweep.py's verified
pipeline (not just Base); ORACLE flags by fixed numeric thresholds, no model call at all;
CURATOR's tool proposals are now also grounded in SCOUT's real bounty-radar opportunities,
not only registry gaps.

**Orchestration:** keep the current pattern — independent GitHub workflows on staggered
crons + the persistent ACP monitor on the host. No central scheduler needed; each agent
commits to `intel/` (its audit trail) and they coordinate through shared files, not a bus.

---

## 3. More Free Open-Source LLMs (resilience + capability) [OK] shipped

This section's original framing ("today VAPE uses Groq alone, single point of failure")
predates the actual build below — kept only as the historical rationale for why the
multi-provider chain (and later the frontier tier) exists at all. Reality now: a paid
frontier model is the primary route for every reasoning-heavy call, with the full
free chain below as the fallback for every one of them, and the sole path for anything
run with zero keys configured — see the "Ethos update" note further down.

### Free providers — all wired in `agents/llm.py`
| Provider | Free tier | Models | Best for |
|---|---|---|---|
| **Groq** [OK] | 14.4k req/day, 30k TPM | Llama 3.1/4, Qwen3, DeepSeek-R1-Distill | speed champion — real-time reports |
| **Cerebras** [OK] | **1M tokens/day**, no CC | Llama 4 Scout, Qwen3 32B, DeepSeek-R1 | daily-volume champion — bulk synthesis |
| **OpenRouter** [OK] | 20+ free models, one key | DeepSeek-R1, Llama 3.3 70B, Qwen3 Coder | fallback marketplace, model variety |
| **GitHub Models** [OK] | free w/ GitHub account | Llama, DeepSeek (Azure OAI endpoint) | already in our CI env — natural fit |
| **Together AI** [OK] | free endpoints | Llama-3.3-70B-Turbo-Free, DeepSeek-R1-Distill-70B | bigger models when 8B isn't enough |
| **Gemini** [OK] | free tier, mind rate limits | Gemini 2.5 | powers the DefiLlama panel's AI review + web-search intel feed |
| **xAI (Grok 4.1 Fast)** [OK] | one-time $25 signup credit, not recurring | Grok 4.1 Fast | the actual frontier-tier primary — see Ethos update below |

All seven are real env-keyed options in `.env.example`; a provider is silently skipped if
its key is unset, so this table is "what's wired," not "what you personally have keyed."
| **Mistral** [TBD] | Experiment tier (~1B tok/mo) | open-weight Mistral | EU option, large quota |

### Implementation ([OK] shipped — `agents/llm.py`)
- **`agents/llm.py`**: one `ask(system, user, *, tier)` with an **OpenAI-compatible**
  client (stdlib `urllib` — no LiteLLM/openai dep) and an ordered provider list
  (Groq → Cerebras → OpenRouter → GitHub Models → Together). On rate-limit/error, falls
  through to the next. All keys from env/Secrets; a provider is simply skipped if its key
  is unset. `run.py`'s `ask_llm()` now routes through this layer with a legacy-Groq fallback.
- **Why not LiteLLM/Ollama here:** VAPE's 24/7 runtime is the **ephemeral GitHub runner**
  (no GPU, no persistent daemon) — Ollama can't run there. LiteLLM would add a dependency for
  what 80 lines of stdlib already does. Ollama/LiteLLM remain great for the **local/Android**
  path; the env-keyed providers cover the CI path. Same OpenAI-compatible shape both ways.
- **Model tiering:** `fast` (Groq 8B) for hourly reports; `deep` (Cerebras/Together 70B)
  for daily synthesis + deep audits; `bulk` (Cerebras 1M/day) for large harvest passes.
- **Why it's still ~free:** spreading load across daily-volume (Cerebras) + speed (Groq)
  free tiers means we rarely hit a ceiling — and never pay.
- **Data-privacy note:** prefer providers that don't train on prompts for any
  sensitive forensics; Groq/Cerebras/Together are inference-only on free tier.
  Flag Google AI Studio / Mistral Experiment as "may train" — use only for public intel.
- **Ethos update (2026-07):** VAPE is deliberately moving off "stay free at all costs"
  for the calls that matter most. `FRONTIER_ORDER` (Grok first, then
  Groq/Gemini/the free chain) is now the actual PRIMARY route — not an emergency
  fallback — for every reasoning-heavy call site: the periodic sweep narratives
  (`base/macro/security/sentiment/virtuals_sweep.py`), the flagship bounty report
  (`run.py`), SKILLFORGE's self-directed build proposals + code generation, redteam's
  judge calls, SCOUT's every-cycle strategic briefing, and every real investigation's
  expert-assessment layer (`investigate.py::_expert_assessment`). Still
  free-fallback-safe (every one of these degrades gracefully with zero keys), but the
  bar for "is this worth paying for" is now "does it need real reasoning," not
  "can it be free." Real budget/privacy constraint: xAI's free tier is a one-time $25
  signup credit, not a recurring free quota like Groq's — the $150/month recurring
  option requires opting into API-input data-sharing for model training, which is
  intentionally left OFF (conflicts with the data-privacy note above for anything
  touching real forensics). By explicit direction (2026-07-13), coverage now wins over
  conserving that credit: `agents/scout.py::_strategic_briefing` runs every cycle rather
  than only on new entries, and insight gets acted on, not just narrated —
  `_act_on_incidents()` triggers a real investigation whenever an incident's address
  verifies, on any chain investigate.py supports.
- **Opt-in candidate providers (not on the default `FRONTIER_ORDER` path):**
  `agents/llm.py` also carries three explicitly opt-in-only LLM candidates,
  each falling back to the normal chain above when unconfigured/erroring —
  a self-hosted GPU fine-tune (`ask_candidate()`, `VAPE_CANDIDATE_URL`), a
  Vertex-AI supervised-tuned Gemini model with real repo-digest grounding
  (`ask_vertex_candidate()`, `VAPE_VERTEX_ACCESS_TOKEN` via WIF, wired into
  `skillforge/synthesize.py`/the sweep narratives/investigations' expert
  assessment), and Oracle Cloud's hosted xAI Grok 4.3 — a second real
  frontier-model host, 1M-token context, reasoning-focused
  (`ask_oci_grok()`, `OCI_GENAI_API_KEY`, a plain Bearer secret from OCI's
  Generative AI service). None of these three are in `PROVIDERS`/
  `FRONTIER_ORDER` by default — each is a separate, evaluated rollout
  decision per call site, matching the eval-before-real-traffic rule in
  `data/finetune/DATASET_CARD.md`.

### GitHub Models — the natural unlock
CI already runs in GitHub. **GitHub Models** gives free OpenAI-compatible inference tied to
the same `GITHUB_TOKEN`/PAT we use — **no new secret, no new account.** Strong candidate as
the CI-side default with Groq as the low-latency path. [TBD] evaluate first.

---

## 4. Sequenced rollout (lowest effort → highest leverage)
1. [OK] ACP fulfillment bridge (`acp_fulfill.py`) — done, 20 of 28 offerings auto-fulfill.
2. [OK] Bridge wired into `scripts/acp-monitor/auto_fulfill.py` — settles with zero LLM cost
   for every offering except `dossier_check`/`community_intel_broadcast`.
3. [OK] `agents/llm.py` multi-provider fallback (Groq/Cerebras/OpenRouter/GitHub Models/
   Together), plus a frontier tier (xAI/Gemini) on top for reasoning-heavy calls.
4. [OK] SCOUT shipped (rule-based + every-cycle strategic briefing + real, cross-chain incident-forensics action, hourly). [OK] ORACLE shipped (fixed numeric thresholds, no model call, 6-hourly broadcasts).
5. [OK] wallet_trace switched to Alchemy (VAPE_TRACE_ALCHEMY_API), live-verified against the
   real Transfers API (PR #145). [TBD] still unlocks: a real auto-handler for `forensics_deep`
   ($2)/`wallet_recon` ($0.03), and the LEDGER agent — the tool works, nothing calls it
   automatically yet.
6. [OK] x402 payment worker live on Base mainnet, 20 routes, real KV job ledger + live feed,
   settled through a real 50/50 VAPOR/CDP hybrid facilitator split.
7. [TBD] Reputation loop on the dashboard → more inbound ACP jobs.

Every step reuses the free GitHub runner + existing keyless tools. No new infrastructure,
no recurring cost, real data throughout.
