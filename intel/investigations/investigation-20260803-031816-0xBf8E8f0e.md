<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — aeon

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![65/100](https://img.shields.io/badge/SAFETY_SCORE-65%2F100-B4BD40?style=flat-square)

- **Target:** `0xBf8E8f0e8866a7052F948C16508644347c57aba3`
- **Chain:** 8453 (Base)
- **Date:** 2026-08-03T03:18:16Z
- **Verdict:** CAUTION (65/100)

---

## Executive Summary
**Overall: CAUTION (65/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 90/100 |
| Holder Distribution & Liquidity | 85/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act on the contract
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Violent 24h move +164% (volatility/manipulation)

## Positive Signals (real legitimacy evidence found)
- 8430 holders — reasonably distributed
- Deep liquidity ($955,677)
- Trading 145+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act on the contract
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +164% (volatility/manipulation)
**Holder Distribution & Liquidity** — 1 flag(s), 2 positive signal(s)
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 8430 holders — reasonably distributed
  - (positive) Deep liquidity ($955,677)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 145+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence gathered this cycle is thin, limited to raw on-chain metrics and automated flags with no external pages, search hits, or project documentation available to review. One concrete detail present is the contract owner address 0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12 that remains active. No grounded recommendation is possible yet.

## Gaps & Confidence

- **No off-chain identity or deployment context for the active owner** (confidence: 80%) — next: Check Base explorer for prior txs from 0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12

## Market & Liquidity
- Symbol/Name: aeon / aeon
- Price: $0.00001671
- Liquidity: $955677.34
- 24h Volume: $1979165.05
- 24h Change: 164%
- DEX: uniswap
- Liquidity/Market-cap ratio: 66.0% — reasonable depth for its size

## Project Links
- Website: https://www.aeon.fun/
- Website: https://github.com/aaronjmars/aeon
- twitter: https://x.com/aeonframework
- telegram: https://t.me/aeon_agent

## Tokenomics (address-verified)
- Circulating supply: 87,467,587,094 AEON
- Total supply: 100,000,000,000
- Max supply: 100,000,000,000
- Market cap: $1,447,214
- Fully diluted valuation: $1,654,572
- FDV/Market-cap ratio: 1.14x — most of supply is already circulating
- Homepage: https://www.aeon.fun/
- X/Twitter: https://x.com/aeonframework

> The most autonomous agent framework. Give it a direction — it'll leverage 121 skills like deep research, PR reviews, market monitoring, Vercel deploys, and more to get it done. No approval loops. No babysitting. Configure once, forget forever. Most agent tools put you in the driver's seat — approve this tool call, review this diff, confirm this action. That's useful for interactive work. But there's a whole class of tasks where you just want the work done while you're not there: morning briefs, market monitoring, PR reviews, research digests, security scans. The key difference: other agents ar

## Token Security
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `8430`
- owner_address: `0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 39.3% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 10143 bytes

## Contract Verification
- Verified: True
- Name: DERC20 · Compiler: v0.8.26+commit.8a97fa7a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _setImplementation, _transferOwnership, burn, mintInflation, renounceOwnership, transferOwnership, updateMintRate

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $1.7416110481674743e-05 · confidence: 0.99 · symbol: aeon
- First DefiLlama price: 2026-05-22T00:19:28Z (73.1 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: not due yet (49/55 still owed today — pacing to the growing minimum, not a fixed cadence); vapor: 30m interval not yet up (15m remaining) — skipped this cycle

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://basescan.org/address/0xBf8E8f0e8866a7052F948C16508644347c57aba3
- Market pair: https://dexscreener.com/base/0x4a9b9e13975d26f4e3e17c655593bb82145dd4452aedafb826d856b817c9cfd4
- Market data: https://www.coingecko.com/en/coins/aeon-2
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*