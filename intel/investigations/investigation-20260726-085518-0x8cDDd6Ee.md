<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — PUPPY

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![50/100](https://img.shields.io/badge/SAFETY_SCORE-50%2F100-FBBF24?style=flat-square)

- **Target:** `0x8cDDd6EeA1067b78B77255e49861843F69D4703D`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-26T08:55:18Z
- **Verdict:** CAUTION (50/100)

---

## Executive Summary
**Overall: CAUTION (50/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 75/100 |
| Holder Distribution & Liquidity | 85/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Violent 24h move +16882% (volatility/manipulation)
- [-15] Pair only 0.9 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +16882% (volatility/manipulation)
  - [-15] Pair only 0.9 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 1 flag(s), 0 positive signal(s)
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints PUPPY as a textbook anonymous Uniswap memecoin launch: a minimal StandardToken contract deployed less than a day ago, renounced (owner=None), with zero taxes and no mint capability, yet paired with fully unlocked liquidity that the deployer can still drain. The 304 holders and $529k volume already reflect rapid distribution after the +16882% spike, but the tiny 62k liquidity pool and 0.9-day pair age tie directly to the extreme volatility, indicating the move was almost certainly driven by early snipers rather than organic demand or any underlying utility. Nothing in the on-chain data or GoPlus flags suggests hidden malicious functions, but the complete absence of any project footprint or audit also means the "custom verified source" positive signal only confirms a hand-written ERC20, not legitimacy.

The rule-based verdict overweighted the volatility metric in isolation; that 16882% figure is the expected outcome of any fresh low-liquidity launch rather than an independent red flag, while it underweighted the clean renounced + zero-tax combination, which at least removes the most common rug vectors even if LP remains unlocked.

Next concrete check: pull the exact LP-add transaction timestamp and the deployer's prior wallet activity to see whether liquidity was seeded from a fresh address or one with a history of similar launches.

## Market & Liquidity (DexScreener)
- Symbol/Name: PUPPY / Puppy
- Price: $0.0003645
- Liquidity: $62341.88
- 24h Volume: $529665.6
- 24h Change: 16882%
- DEX: uniswap

## Project Links (as declared on DexScreener)
- No official website/social links declared on this token's DexScreener listing.

## Tokenomics (CoinGecko, address-verified)
- Not available this cycle (CoinGecko does not track this exact contract address, or the token isn't listed there yet) — absence noted, not penalized.

## Token Security (GoPlus)
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `304`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 10 non-LP/burn holders control 33.1% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 2104 bytes

## Contract Verification
- Verified: True
- Name: StandardToken · Compiler: v0.8.20+commit.a1b79de6
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _mint, launchAndLockWithBurnBps, mint, registerTokenIdBurnBps, setBurnBps, transferOwnership, withdrawAllToken

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0x8cDDd6EeA1067b78B77255e49861843F69D4703D
- DexScreener pair: https://dexscreener.com/ethereum/0x2f5a2acdd4cff3edb70087b1017e9c16322c2ac9
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*