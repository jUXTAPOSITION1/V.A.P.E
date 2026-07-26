<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — EUL

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![65/100](https://img.shields.io/badge/SAFETY_SCORE-65%2F100-B4BD40?style=flat-square)

- **Target:** `0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-26T01:36:14Z
- **Verdict:** CAUTION (65/100)

---

## Executive Summary
**Overall: CAUTION (65/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 88/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 77/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-8] Top 10 non-LP/burn holders control 56% of supply — meaningful concentration
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- 5366 holders — reasonably distributed
- Deep liquidity ($1,127,747)
- Trading 289+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 1493+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-12] Mintable supply (dilution risk)
**Holder Distribution & Liquidity** — 2 flag(s), 2 positive signal(s)
  - [-8] Top 10 non-LP/burn holders control 56% of supply — meaningful concentration
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 5366 holders — reasonably distributed
  - (positive) Deep liquidity ($1,127,747)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 289+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 1493+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

This is the governance token for Euler Finance, a DeFi lending protocol that launched on Ethereum in mid-2022. The combination of 1493 days of continuous DefiLlama pricing history, 5366 holders, $1.1 M+ Uniswap liquidity, and a non-factory verified contract forms a coherent picture of an established protocol token rather than a short-lived meme or rug. The mintable flag and 56 % top-10 concentration are consistent with a live lending market that still needs incentive emissions and likely holds protocol or investor allocations; the unlocked liquidity is likewise typical once a project moves beyond initial bootstrapping and manages its own pools. Nothing in the on-chain or market data contradicts this reading.

The rule-based score overweighted the generic “mintable + unlocked LP” penalties without adjusting for the project’s documented multi-year operating history and independent price feed. Those flags would be decisive for a fresh deployment but are less diagnostic here given the longevity signal.

Next step: pull the verified source and trace the mint function’s access control (who can call it and under what timelock or governance constraints).

## Market & Liquidity (DexScreener)
- Symbol/Name: EUL / Euler
- Price: $2.17
- Liquidity: $1127746.8
- 24h Volume: $76195.79
- 24h Change: 90.65%
- DEX: uniswap
- Liquidity/Market-cap ratio: 1.9% — thin relative to market cap

## Project Links (as declared on DexScreener)
- Website: https://euler.finance/
- Website: https://discord.euler.finance/
- Website: https://www.youtube.com/@EulerFinance
- Website: https://github.com/euler-xyz
- Website: https://docs.euler.finance/
- twitter: https://x.com/eulerfinance
- telegram: https://t.me/eulerfinance_official

## Tokenomics (CoinGecko, address-verified)
- Circulating supply: 24,146,317 EUL
- Total supply: 27,182,818
- Max supply: 27,182,818
- Market cap: $58,652,156
- Fully diluted valuation: $58,652,156
- FDV/Market-cap ratio: 1.00x — most of supply is already circulating
- Homepage: https://www.euler.finance/
- X/Twitter: https://x.com/eulerfinance

> The ability to lend and borrow assets efficiently is a crucial feature of any financial system. In the world of traditional finance, this process is typically facilitated by trusted and permissioned third-parties such as banks, who connect people with a surplus of money to those who need access to it in the short term. In the world of decentralised finance (DeFi), trusted and permissioned third-parties are no longer needed; banks have been replaced by trustless and permissionless lending protocols running on the blockchain (1). Among the first-generation of DeFi lending protocols are Compound 

## Token Security (GoPlus)
- is_honeypot: `0`
- buy_tax: ``
- sell_tax: ``
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `5366`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 10 non-LP/burn holders control 56.3% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 10 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 19936 bytes

## Contract Verification
- Verified: True
- Name: Eul · Compiler: v0.8.4+commit.c7e474f2
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, mint

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $2.164553852265336 · confidence: 0.99 · symbol: EUL
- First DefiLlama price: 2022-06-24T05:23:07Z (1492.8 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b
- DexScreener pair: https://dexscreener.com/ethereum/0xb976c70758724d5a89ce77ee84b4443e13b383f1a0e1f77c29f24172481478b4
- CoinGecko: https://www.coingecko.com/en/coins/euler
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*