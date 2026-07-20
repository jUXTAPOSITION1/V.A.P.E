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

### Market-data tools
15 real-time market-data tools, each auto-fulfilled by `agents/acp_fulfill.py`
and also x402-payable at the worker's `/data/<name>` route. Protocol/chain
tools carry real hosted logos; token tools carry the token's DexScreener logo.
Every result is real data or an honest `{error}` — never fabricated. 14 are
0.01 USDC each (13 backed by the keyless DefiLlama API, plus
`prediction_market_odds` backed by the keyless Polymarket/Kalshi APIs);
`wallet_pnl_deepdive` is priced separately since it's a richer, Alchemy +
CoinGecko-backed deliverable (Base mainnet only).

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
| **wallet_pnl_deepdive** | **0.25** | 5m | `address` | Real Base-mainnet balances (via Alchemy) + an unrealized-P&L estimate per holding (current value vs. first-acquisition price, via CoinGecko) |
| prediction_market_odds | 0.01 | 5m | optional `limit` | Live crypto/Base-relevant prediction-market odds from Polymarket and Kalshi, ranked by volume |

## The autonomous monitor ([OK])
Jobs are caught and fulfilled at near-zero compute via a 3-layer monitor:
1. **Listener daemon** — `acp events listen` streams job events to a file. Zero LLM.
2. **Drain + triage** — classifies events, tracks per-job state, idempotent. Zero LLM.
3. **Reasoning handler** — fires only on a real funded job: reads the requirement, runs
   the mapped tool, submits a tailored deliverable, settles, logs to `intel/catalog/`.

This keeps cost ≈ 0 while idle; the model only wakes when escrow money is on the table.

## Client side (hiring other agents) [WIP]
VAPE can also delegate: `acp browse "<service>"` → `acp client create-job` → `fund` →
`complete`. Used to obtain specialist work (data, compute, content) when cheaper than
doing it in-house.

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
- [OK] End-to-end deliverable automation for 22 of 30 offerings —
  `scripts/acp-monitor/auto_fulfill.py` imports `agents/acp_fulfill.py`'s
  `HANDLERS` dict directly, so the monitor auto-submits a real deliverable
  the moment escrow funds. [TBD] the remaining 8 (`partner_referral`,
  `wallet_recon`, `tx_decode`, `whale_watch`, `bulk_safety_bundle`,
  `deep_contract_audit`, `forensics_deep`, and `bounty_deep_dive`'s async
  escalation) still need manual or human-in-the-loop fulfillment.
- [TBD] Dynamic pricing from demand + dedup against `intel/catalog/`.
- [TBD] Client-side delegation for compute-heavy audits.
