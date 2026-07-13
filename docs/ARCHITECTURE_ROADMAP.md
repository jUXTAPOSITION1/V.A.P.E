# V.A.P.E. — Architecture Roadmap: ACP Revenue, More Agents, More LLMs

Strategy for deepening ACP integration and expanding the agent/LLM framework —
while holding the line: **maximum capability, lowest possible compute, real data only.**

> Status: [OK] live · [WIP] in progress · [TBD] proposed

---

## 1. Deeper ACP Integration (GitHub + VAPE → revenue)

### The bridge ([OK] shipped)
`agents/acp_fulfill.py` maps **ACP offerings → verified real-data tools**, producing a
submit-ready deliverable. This connects the GitHub-built tool tier directly to ACP escrow income.

### Rail decision: ACP **CLI**, not the raw SDK
VAPE already operates on the **ACP CLI** (signer provisioned, 14 offerings live, monitor
catching jobs). We deliberately do **not** `pip install virtuals-acp` + put `ACP_WALLET_KEY`
in `.env`: that would duplicate the rail and reintroduce raw private-key handling. The CLI
stores the P256 signer in a file/keychain backend and signs via its own secure path. The
bridge produces *deliverables*; the CLI does all *signing/submitting*. Keys never touch the
repo or `.env`. (The SDK stays an option only if a future flow the CLI can't do appears.)

| Offering | $ | Auto-fulfilled by | Status |
|---|---|---|---|
| token_safety_check | 0.02 | `token_scan.py` (GoPlus+DexScreener) | [OK] auto |
| liquidity_check | 0.02 | `token_scan.py` (liquidity) | [OK] auto |
| rug_pull_alert | 0.03 | `token_scan.py` (owner/mint/honeypot) | [OK] auto |
| exploit_check | 0.01 | `data_fetchers.get_contract_source` | [OK] auto (needs Etherscan key on runner) |
| market_intel | 0.07 | `build_market_context()` | [OK] auto |
| dossier_check | 0.10 | `investigate.quick_assess` (score + meme-factory + hack corr + web-reputation search) + declared-socials scrape + frontier-LLM quick source read | [OK] auto |
| deep_contract_audit | 1.00 | SKILLFORGE static tier (slither/aderyn/mythril) | [WIP] monitor handler |
| forensics_deep | 2.00 | wallet_trace + contract_recon | [WIP] wallet_trace now Alchemy-backed, pending live verification |
| wallet_recon | 0.03 | base_rpc / wallet_trace | [WIP] wallet_trace now Alchemy-backed, pending live verification |
| whale_watch / tx_decode / bulk_safety_bundle / community_intel_broadcast / partner_referral | — | mapped, monitor handler | [TBD] |

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

### Next ACP steps ([TBD] proposed, all low-compute)
1. **Wire `acp_fulfill` into the monitor handler** — the `vape-acp-handler` cron calls
   `fulfill()` for the 6 auto-offerings; only escalates to the LLM for deep_audit/forensics.
   → Most jobs settle with **zero LLM cost** (pure tool output).
2. **Self-listing refresh from GitHub** — a workflow that regenerates offering descriptions
   from the live tool registry (`skillforge/memory/tools-registry.json`) so offerings never
   drift from real capability.
3. **Dedup + caching** — check `intel/scans/scans.jsonl` before re-running a recent
   same-target scan; serve cached deliverable (faster SLA, lower cost, higher margin).
4. **Reputation loop** — after each completed job, append outcome to `lessons.jsonl`;
   surface success-rate on the dashboard to attract more buyers.
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
| **SCOUT** [OK] | Bounty-radar triage — ranks new DeFiLlama hack/incident leads by numeric fit score (`agents/scout.py`); Immunefi/Code4rena/Sherlock have no stable public API so those stay static seed data until one exists. When a cycle turns up something genuinely new, a Grok-authored "Strategic Briefing" (why it matters, what VAPE capability it exercises, one next action) is added on top of the numeric table | `intel/bounty-radar/*`, DeFiLlama hacks feed, Grok via `agents/llm.py`'s `FRONTIER_ORDER` (gated on new entries only, to stay inside its free/one-time API credit) | hourly (`.github/workflows/scout.yml`), LLM only on new-entry cycles |
| **LEDGER** [TBD] | Wallet/fund-flow forensics — chain-of-custody graphs | wallet_trace (Alchemy-backed), base_rpc | on-demand |
| **ORACLE** [OK] | Market-anomaly watcher — TVL outflow / depeg / gas-spike / fresh-exploit / extreme-F&G alerts, published to `intel/broadcasts/` (`agents/broadcast.py`) | `data_fetchers.build_market_context()`'s rule-based `anomaly_flags` | every 6h (`.github/workflows/broadcast.yml`), no LLM |
| **CURATOR** [OK] | SKILLFORGE — two real halves: `synthesize.py` distills harvested intel into markdown playbooks (Groq); `skillforge_build.py` proposes AND builds real multi-file tools grounded in tool-registry gaps + Memory findings/lessons, opening a PR for review | harvest/Memory + Groq + `builder.py`'s `generate_project()` | daily PR (synthesize) / weekly PR (build) |
| **WARDEN** [TBD] | ACP job QA — validates deliverables before submit (schema + sanity) | acp_fulfill output | per-job, no LLM |
| **DATA AGENT** [OK] | VAPE's own paying customer — recruited by every real investigation (`agents/investigate.py::investigate()`) to hire 2-4 random $0.01 x402 market-data offerings against the token under review, using its own funded wallet (`DATA_AGENT_PRIVATE_KEY`); results fold into the report's "Data Agent Intel" section | `agents/data_agent.py`, worker's `/data/*` x402 routes (`worker/src/dataHandlers.ts`) | per-investigation, capped 15 paid hires/day, no LLM |

**Design rule:** each agent is **rule-based first, LLM only when reasoning is required.**
SCOUT ranks by numeric fit score and only calls Grok for a strategic briefing when a
cycle turns up something genuinely new (most hourly runs don't); ORACLE flags by
thresholds (no LLM); CURATOR's tool proposals are now also grounded in SCOUT's real
bounty-radar opportunities, not only registry gaps. This keeps the roster nearly free.

**Orchestration:** keep the current pattern — independent GitHub workflows on staggered
crons + the persistent ACP monitor on the host. No central scheduler needed; each agent
commits to `intel/` (its audit trail) and they coordinate through shared files, not a bus.

---

## 3. More Free Open-Source LLMs (resilience + capability)

Today VAPE uses **Groq (Llama 3.1 8B)** for synthesis + reports. Single-provider = single
point of failure (rate limits, outages). Add an **OpenAI-compatible multi-provider fallback
chain** — all free tier, all open-source models, swap by base-URL + key.

### Recommended free providers (researched, 2026)
| Provider | Free tier | Models | Best for |
|---|---|---|---|
| **Groq** (have it) | 14.4k req/day, 30k TPM | Llama 3.1/4, Qwen3, DeepSeek-R1-Distill | speed champion — real-time reports |
| **Cerebras** [TBD] | **1M tokens/day**, no CC | Llama 4 Scout, Qwen3 32B, DeepSeek-R1 | daily-volume champion — bulk synthesis |
| **OpenRouter** [TBD] | 20+ free models, one key | DeepSeek-R1, Llama 3.3 70B, Qwen3 Coder | fallback marketplace, model variety |
| **GitHub Models** [TBD] | free w/ GitHub account | Llama, DeepSeek (Azure OAI endpoint) | already in our CI env — natural fit |
| **Together AI** [TBD] | free endpoints | Llama-3.3-70B-Turbo-Free, DeepSeek-R1-Distill-70B | bigger models when 8B isn't enough |
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
  for the calls that matter most. `FRONTIER_ORDER` (Grok first, key 1 then key 2, then
  Groq/Gemini/the free chain) is now the actual PRIMARY route — not an emergency
  fallback — for every reasoning-heavy call site: the periodic sweep narratives
  (`base/macro/security/sentiment/virtuals_sweep.py`), the flagship bounty report
  (`run.py`), SKILLFORGE's self-directed build proposals + code generation, redteam's
  judge calls, SCOUT's gated strategic briefing, and every real investigation's new
  Grok expert-assessment layer (`investigate.py::_grok_expert_assessment`). Still
  free-fallback-safe (every one of these degrades gracefully with zero keys), but the
  bar for "is this worth paying for" is now "does it need real reasoning," not
  "can it be free." Real budget/privacy constraint: xAI's free tier is a one-time $25
  signup credit, not a recurring free quota like Groq's — the $150/month recurring
  option requires opting into API-input data-sharing for model training, which is
  intentionally left OFF (conflicts with the data-privacy note above for anything
  touching real forensics). Gate new high-frequency call sites the way
  `agents/scout.py::_grok_briefing` does (only call when something genuinely new
  happened) unless the call site is inherently low-frequency already.

### GitHub Models — the natural unlock
CI already runs in GitHub. **GitHub Models** gives free OpenAI-compatible inference tied to
the same `GITHUB_TOKEN`/PAT we use — **no new secret, no new account.** Strong candidate as
the CI-side default with Groq as the low-latency path. [TBD] evaluate first.

---

## 4. Sequenced rollout (lowest effort → highest leverage)
1. [OK] ACP fulfillment bridge (`acp_fulfill.py`) — done.
2. [TBD] Wire bridge into the monitor handler (6 offerings settle with no LLM).
3. [TBD] `agents/llm.py` multi-provider fallback (Groq + Cerebras + GitHub Models).
4. [OK] SCOUT shipped (rule-based + gated Grok briefing, hourly). [OK] ORACLE shipped (rule-based, no LLM, 6-hourly broadcasts).
5. [TBD] wallet_trace switched to Alchemy (VAPE_TRACE_ALCHEMY_API), pending a live verification run → unlocks forensics_deep ($2) + LEDGER agent.
6. [TBD] Reputation loop on the dashboard → more inbound ACP jobs.

Every step reuses the free GitHub runner + existing keyless tools. No new infrastructure,
no recurring cost, real data throughout.
