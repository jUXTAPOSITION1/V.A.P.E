# ACP Protocol Integration

How V.A.P.E. earns autonomous on-chain revenue via the **Agent Commerce Protocol (ACP)**
on Virtuals Protocol / Base.

> Status: [OK] live · [WIP] partial · [TBD] planned

## What ACP gives the agent
ACP is Virtuals Protocol's stack for autonomous-agent identity + commerce. VAPE operates
as a **provider** (sells security/intel services) and can act as a **client** (hires other
agents). Every job is an on-chain **USDC-escrow** contract on Base (chainId 8453).

- **Identity:** ACP agent + on-chain wallet, ERC-8004 registered (agent #54988). [OK]
- **Signer:** P256 signing key, `restricted` policy (authorizes all ACP txns). [OK]
- **Wallet:** `0xa1420293a7df49bc8380f543a1fe7b8d6f582879`, USDC-funded on Base. [OK]

## Job lifecycle (provider / selling side)

```
job.created ──► set-budget ──► job.funded ──► submit ──► completed
   (client)      (VAPE)          (client)      (VAPE)     (escrow → VAPE)
                    │                              │
                    └─ price = offering priceValue └─ real deliverable from SKILLFORGE tool
```

| Phase | Who acts | Command |
|---|---|---|
| `job.created` | VAPE | `acp provider set-budget --job-id <id> --amount <price> --chain-id 8453` |
| `job.funded` | VAPE | run tool → `acp provider submit --job-id <id> --deliverable <data>` |
| `submitted` | client | `acp client complete` / `reject` |
| `completed` | — | escrow released to VAPE (terminal) |

## Live offerings (30)
Each offering maps to a verified SKILLFORGE tool that produces **real data only**.

| Offering | Price (USDC) | SLA | Backing tool |
|---|---|---|---|
| exploit_check | 0.01 | 5m | contract_recon + slither |
| partner_referral | 0.01 | 5m | referral |
| token_safety_check | 0.02 | 5m | recon/token_safety.sh |
| liquidity_check | 0.02 | 5m | token_safety.sh (dex) |
| wallet_recon | 0.03 | 5m | recon/wallet_trace.sh / base_rpc |
| rug_pull_alert | 0.03 | 5m | token_safety.sh (mint/owner) |
| tx_decode | 0.05 | 5m | contract_recon (abi) + RPC |
| market_intel | 0.07 | 5m | recon/market_data.sh |
| dossier_check | 0.10 | 5m | `agents/investigate.py`'s real heuristic engine (weighted score, meme-factory detection, hack correlation, web-reputation search) + a live check of declared socials + a frontier-LLM quick source read |
| whale_watch | 0.10 | 5m | wallet_trace + market_data |
| community_intel_broadcast | 0.10 | 5m | intel/broadcasts + market_data |
| bulk_safety_bundle | 0.50 | 15m | token_safety × N |
| deep_contract_audit | 1.00 | 30m | slither + aderyn + mythril |
| forensics_deep | 2.00 | 60m | wallet_trace + contract_recon |
| **bounty_deep_dive** | **1.00** | **async, no fixed SLA** | full recon + Slither + `agents/deep_dive_audit.py`'s frontier-tier LLM (Gemini 2.5 Pro, Groq fallback) source review — a submission-ready PoC with full technical detail. Supply an address (Solidity/EVM) or a GitHub owner/repo (any other language, e.g. Move/Sui, via `agents/external_audit.py`) to scope it to a specific bounty program. |

x402-payable at the worker (`GET /scan/<name>`, real USDC-on-Base settlement,
no ACP job needed): `exploit_check`, `token_safety_check`, `liquidity_check`,
`rug_pull_alert`, `market_intel`, `dossier_check`, `bounty_deep_dive`, plus
four that closed a real ACP/x402 parity gap this round — each was ACP-listed
since launch but had no worker route until now:
- `deep_contract_audit` — `GET /scan/deep_contract_audit`, an address-only
  alias of `bounty_deep_dive`'s exact same async dispatch pipeline.
- `tx_decode` — `GET /scan/tx_decode?tx_hash=0x...`, a new synchronous
  decode (real on-chain tx/receipt/logs plus signature lookup, no LLM).
- `community_intel_broadcast` — `GET /scan/community_intel_broadcast`
  (zero-input), serves the same real broadcast this offering's ACP handler
  already reads (`agents/acp_fulfill.py::_community_broadcast()`).
- `bulk_safety_bundle` — `GET /scan/bulk_safety_bundle?addresses=0x...,0x...`
  (5-25 comma-separated addresses), a batch wrapper around
  `token_safety_check`.

Not x402-payable: `partner_referral`, `wallet_recon`, `whale_watch` (no real
data source picked yet), and `forensics_deep` — ACP-only, hired as a real job.

**New, x402-only offering (not yet in the 30-offering ACP catalog above):**
`website_review` — `GET /scan/website_review?url=https://...`, $0.15,
`worker/src/lib/websiteReview.ts`. A phishing/scam-page content read of a
plain website URL (real scrape + frontier-LLM read for fake contract
addresses, wallet-drainer patterns, brand/template mismatch, copy-paste
scam-site boilerplate) — deliberately distinct from `bounty_deep_dive`'s
smart-contract audit, per the original Phase 4 plan for this offering.
Listing it as a real, sellable ACP offering (not just x402-payable) needs
`acp provider create-offering` run on the persistent ACP host (same signer
constraint as `scripts/acp-monitor/virtuals_evaluator.py` above) — until
then it's discoverable via `agents/x402_directory_register.py`'s external
listings and x402-payable directly, same as any other worker route.

### Market-data tools
15 real-time market-data tools, each auto-fulfilled by `agents/acp_fulfill.py`
and also x402-payable at the worker's `/data/<name>` route. Protocol/chain
tools carry real hosted logos; token tools carry the token's own hosted logo.
Every result is real data or an honest `{error}` — never fabricated. 14 are
0.01 USDC each (13 backed by keyless market-data aggregation, plus
`prediction_market_odds` backed by the keyless Polymarket/Kalshi APIs);
`wallet_pnl_deepdive` is priced separately since it's a richer, real
Base-mainnet-balance deliverable.

| Offering | Price (USDC) | SLA | Input | What it returns |
|---|---|---|---|---|
| token_intel | 0.01 | 5m | `address`, `chain`, optional `slug` | Price + 0-1 confidence, oracle-derived token age, optional fees/unlocks/treasury, + logo |
| token_chart | 0.01 | 5m | `address`, `chain`, `span` | Daily price series (default 30d) + logo |
| protocol | 0.01 | 5m | `slug` | Full protocol record: per-chain TVL, category, audits, logo |
| protocol_fees | 0.01 | 5m | `slug` | Real earned fees + revenue (24h/7d/30d/1y/all-time) |
| unlocks | 0.01 | 5m | `slug` | Next upcoming token-unlock (dump-risk) event |
| treasury | 0.01 | 5m | `slug` | Treasury composition + own-token fragility share |
| chain_protocols | 0.01 | 5m | `chain` | Top protocols on a chain by TVL, each with logo |
| chain_overview | 0.01 | 5m | `chain` | Chain headline TVL + rank among all chains |
| chain_fees | 0.01 | 5m | `chain` | Fee-earning protocols on a chain, ranked, with logos |
| dex_volumes | 0.01 | 5m | `chain` | DEX volume on a chain by venue, with logos |
| yields | 0.01 | 5m | `chain`/`project`/`symbol` | Yield pools TVL-ranked — trap detection |
| stablecoins | 0.01 | 5m | — | Stablecoins by supply with live peg + computed depeg |
| bridges | 0.01 | 5m | — | Bridges ranked by daily volume — bridge-exploit threat data |
| **wallet_pnl_deepdive** | **0.25** | 5m | `address` | Real Base-mainnet balances + an unrealized-P&L estimate per holding (current value vs. first-acquisition price) |
| prediction_market_odds | 0.01 | 5m | optional `limit` | Live crypto/Base-relevant prediction-market odds from Polymarket and Kalshi, ranked by volume |

## The autonomous monitor ([OK])
Jobs are caught and fulfilled at near-zero compute via a 3-layer monitor:
1. **Listener daemon** — `acp events listen` streams job events to a file. Zero LLM.
2. **Drain + triage** — classifies events, tracks per-job state, idempotent. Zero LLM.
3. **Reasoning handler** — fires only on a real funded job: reads the requirement, runs
   the mapped tool, submits a tailored deliverable, settles, logs to `intel/catalog/`.

This keeps cost ≈ 0 while idle; the model only wakes when escrow money is on the table.

## Client side (hiring other agents) [WIP / OK for self-hire]
VAPE can also delegate: `acp browse "<service>"` → `acp client create-job` → `fund` →
`complete`. Used to obtain specialist work (data, compute, content) when cheaper than
doing it in-house.

**Live since this round:** `scripts/acp-monitor/virtuals_evaluator.py` — VAPE acting as
its own ACP client, hiring one of its own already-live selling offerings
(`token_safety_check`/`liquidity_check`/`rug_pull_alert`/`exploit_check`/
`dossier_check`) to evaluate a real Virtuals-Protocol-tagged token, at a fixed cadence
of 1 real on-chain job every 4 hours. Same wallet on both sides of a genuine
USDC-escrow job — proves the ACP payment rail end-to-end the same way
`agents/data_agent.py` already proves x402 end-to-end, and turns every run into a real,
verifiable evaluation of a live Virtuals project. Runs on the same persistent host as
the listener/drain daemons above (never GitHub Actions — see the module's own
docstring for why the `restricted`-policy signer this needs can't live in an ephemeral
CI runner). Delegation to *other* (non-VAPE) specialist agents is still [WIP].

## CLI surface (reference)
All actions run through the ACP CLI (`acp`), never ad-hoc Web3 scripts:
```
acp agent whoami            # identity + signer
acp offering list           # our sellable services
acp job list --all          # active jobs
acp events listen           # provider monitor stream
acp provider set-budget     # price a job
acp provider submit         # deliver
acp client fund/complete    # buyer side
acp wallet balance          # treasury
```

## Security
- Signing keys never live in the repo; signer is provisioned per-environment via
  `acp agent add-signer` (one-time browser approval).
- `restricted` policy scopes the signer to ACP transactions only.
- Real deliverables only — never fabricated findings, scores, or tx hashes.

## Roadmap
- [OK] End-to-end deliverable automation for 21 of 31 offerings on the ACP
  side — `scripts/acp-monitor/auto_fulfill.py` imports
  `agents/acp_fulfill.py`'s `HANDLERS` dict directly, so the monitor
  auto-submits a real deliverable the moment escrow funds. [TBD] the
  remaining 8 (`partner_referral`, `wallet_recon`, `tx_decode`, `whale_watch`,
  `bulk_safety_bundle`, `deep_contract_audit`, `forensics_deep`, and
  `bounty_deep_dive`'s async escalation) still need manual or
  human-in-the-loop fulfillment on the ACP side specifically — but 3 of those
  8 (`deep_contract_audit`, `tx_decode`, `bulk_safety_bundle`) are now
  separately x402-payable directly at the worker, alongside
  `community_intel_broadcast` (already in the auto-fulfilled 22 on the ACP
  side, but until now had no worker route at all). See the offering table
  above — this closes the real gap where all four were ACP-listed since
  launch with no way to pay for them via x402.
- [TBD] Dynamic pricing from demand + dedup against `intel/catalog/`.
- [TBD] Client-side delegation for compute-heavy audits.
