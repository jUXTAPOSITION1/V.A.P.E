<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — CTM

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![75/100](https://img.shields.io/badge/SAFETY_SCORE-75%2F100-86BC52?style=flat-square)

- **Target:** `0xc8Fb80fCc03f699C70ff0CC08C09106288888888`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-25T19:43:37Z
- **Verdict:** CAUTION (75/100)

---

## Executive Summary
**Overall: CAUTION (75/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 85/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x70f279fa72c82110a0bb4745d6283b790190c33f) — can still act on the contract
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- 4725 holders — reasonably distributed
- Top holders control only 15% of supply — broad distribution
- Deep liquidity ($2,431,313)
- Trading 116+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 464+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x70f279fa72c82110a0bb4745d6283b790190c33f) — can still act on the contract
**Holder Distribution & Liquidity** — 1 flag(s), 3 positive signal(s)
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 4725 holders — reasonably distributed
  - (positive) Top holders control only 15% of supply — broad distribution
  - (positive) Deep liquidity ($2,431,313)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 116+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 464+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

The evidence paints CTM as a live, organically grown Uniswap token that has sustained real usage for well over a year: DefiLlama has carried an independent price feed since roughly April 2024, liquidity sits above $2.4 M with daily volume in the same range, and holder distribution (4 725 wallets, top 15 % combined) is broad enough to rule out obvious insider concentration. The contract itself is a modest 3.9 kB verified custom implementation with no mint, no taxes, no proxy, and no honeypot flags, which aligns with a straightforward ERC-20 that has simply continued trading without incident.

What undercuts the “settled project” narrative is the still-active owner (0x70f279fa72c82110a0bb4745d6283b790190c33f) paired with 0 % locked liquidity. Those two facts are directly linked: the same address that deployed the token can still move the entire LP pool at any moment, and nothing in the on-chain data shows any prior renouncement or vesting transaction that would neutralize that power. The 116-day clean trading window is therefore better read as “hasn’t pulled yet” than “structurally safe.”

The rule-based CAUTION score correctly flags the two largest remaining attack surfaces but under-weights the corroborative weight of the DefiLlama history and holder breadth; those metrics are not cosmetic—they indicate the token has already survived the period when most rugs occur. Conversely, the score does not over-weight the owner risk, because an unlocked pool controlled by a single EOA remains a concrete, one-transaction exit vector regardless of past restraint.

Next concrete check: pull the verified source and enumerate every non-view function still callable by the owner address, then cross-reference the most recent liquidity-add transactions to confirm whether that address can unilaterally remove the entire pool without further approvals.

## Market & Liquidity (DexScreener)
- Symbol/Name: CTM / c8ntinuum
- Price: $0.2220
- Liquidity: $2431313.15
- 24h Volume: $2069074.37
- 24h Change: 0.26%
- DEX: uniswap

## Project Links (as declared on DexScreener)
- Website: https://c8ntinuum.com
- twitter: https://x.com/c8ntinuum
- telegram: https://t.me/c8ntinuumANN
- discord: https://discord.com/invite/c8ntinuum
- tiktok: https://www.tiktok.com/@c8ntinuum

## Tokenomics (CoinGecko, address-verified)
- Circulating supply: 0 CTM
- Total supply: 8,888,888,888
- Max supply: 8,888,888,888
- Market cap: $0
- Fully diluted valuation: $1,748,484,404
- Homepage: https://c8ntinuum.com/

> #c8ntinuum is rewriting the narrative — prioritizing cooperation over competition among blockchains. Multichain powered protocol unleashing unrivaled mechanisms designed to achieve ultimate interoperability, scalability, and long term sustainability. c8ntinuum is the first permissionless Layer 0 protocol that supports multiple layers, enabling trust-minimized and secure multi-chain interoperability through zero-knowledge on-chain light clients.

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
- holder_count: `4725`
- owner_address: `0x70f279fa72c82110a0bb4745d6283b790190c33f`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 10 non-LP/burn holders control 15.2% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 3 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 3911 bytes

## Contract Verification
- Verified: True
- Name: CTM · Compiler: v0.8.34+commit.80d5c536
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, burn, mint

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.19703717962051878 · confidence: 0.99 · symbol: CTM
- First DefiLlama price: 2025-04-18T08:31:14Z (463.5 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0xc8Fb80fCc03f699C70ff0CC08C09106288888888
- DexScreener pair: https://dexscreener.com/ethereum/0xdb4c4d91f12ce76f5c9ac0eae193cf3b4d6684cd5f09bf35d03dd9ae6d8a43b1
- CoinGecko: https://www.coingecko.com/en/coins/c8ntinuum
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*