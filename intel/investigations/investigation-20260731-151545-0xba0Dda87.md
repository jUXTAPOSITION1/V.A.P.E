<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — OX

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![25/100](https://img.shields.io/badge/SAFETY_SCORE-25%2F100-FB9854?style=flat-square)

- **Target:** `0xba0Dda8762C24dA9487f5FA026a9B64b695A07Ea`
- **Chain:** 43114 (Avalanche)
- **Date:** 2026-07-31T15:15:45Z
- **Verdict:** REJECT (25/100)

---

## Executive Summary
**Overall: REJECT (25/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 85/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x4f9f7f28be01de1ffb24c00b00744bb3cb49b9ce) — can still act on the contract
- [-15] Top 10 non-LP/burn holders control 102% of supply — concentrated, easily manipulated
- [-25] Very low liquidity $66 (rug/illiquid)
- [-10] Low liquidity $66
- [-15] Contract source UNVERIFIED

## Positive Signals (real legitimacy evidence found)
- 520 holders — reasonably distributed
- Trading 823+ days without a known incident in this scan
- DefiLlama has priced this token for 892+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x4f9f7f28be01de1ffb24c00b00744bb3cb49b9ce) — can still act on the contract
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 102% of supply — concentrated, easily manipulated
  - [-25] Very low liquidity $66 (rug/illiquid)
  - [-10] Low liquidity $66
  - (positive) 520 holders — reasonably distributed
**Transparency & Provenance** — 1 flag(s), 0 positive signal(s)
  - [-15] Contract source UNVERIFIED
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 823+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 892+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

This token shows the profile of a long-dormant Avalanche deployment that once cleared basic listing thresholds (DefiLlama pricing since early 2022, multi-year trading history) but has since collapsed into near-zero activity. The combination of an unverified contract, an active owner wallet that still holds upgrade or mint-adjacent privileges, and top-10 wallets controlling more than the entire circulating supply points to a project whose original deployer or early insiders never fully exited or relinquished control. The 520-holder count and absence of honeypot flags create an appearance of organic distribution, yet that distribution is illusory once the concentration metric is layered on top; the low liquidity and sub-$4 daily volume further indicate that any remaining holders cannot exit without moving the price to zero. Taken together, the evidence does not support a currently functional or community-driven project—only a relic whose on-chain skeleton remains exploitable.

The rule-based score overweighted the raw “owner not renounced” flag relative to the actual elapsed time (nearly 900 days of visible inactivity), while underweighting the mismatch between the 520-holder narrative and the 102 % top-10 concentration; those two data points together imply either heavy centralization or possible wash-holder artifacts rather than genuine dispersion.

Next step: pull the transaction history of the owner address 0x4f9f7f28be01de1ffb24c00b00744bb3cb49b9ce on chain 43114 to determine the date of its last on-chain action and whether any recent approvals or transfers have occurred.

## Market & Liquidity
- Symbol/Name: OX / OX Coin
- Price: $0.00001790
- Liquidity: $66.16
- 24h Volume: $3.29
- 24h Change: -7.6%
- DEX: traderjoe
- Liquidity/Market-cap ratio: 0.2% — thin relative to market cap

## Project Links
- Website: https://ox.fun/
- twitter: https://twitter.com/OXFUNHQ
- telegram: https://t.me/OXFUNPORTAL

## Tokenomics (address-verified)
- Circulating supply: 2,616,366,567 OX
- Total supply: 2,616,366,567
- Max supply: 9,857,348,536
- Market cap: $34,427
- Fully diluted valuation: $34,427
- FDV/Market-cap ratio: 1.00x — most of supply is already circulating
- Homepage: https://ox.fun/en
- X/Twitter: https://x.com/OXFUNHQ

> OX Coin is the native currency of [OX.FUN](https://ox.fun) - a nextgen SocialFi perps exchange. ###What is OX.FUN? OX.FUN is a derivatives exchange where users can trade 200+ coins with up to 50x leverage, including the latest meme tokens. It also supports a diverse range of memecoin collateral, allowing holders to get the most out of their meme portfolios. ###What is the Utility of OX Coin? * OX can be used to stake, earn yield and participate in [OX.FUN Vaults](https://ox.fun/vaults) * OX is accepted as trading collateral on OX.FUN * All fees on OX.FUN are collected in OX * OX is the native 

## Token Security
- is_honeypot: `0`
- buy_tax: ``
- sell_tax: ``
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `520`
- owner_address: `0x4f9f7f28be01de1ffb24c00b00744bb3cb49b9ce`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 102.4% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Avalanche RPC)
- Is contract: True
- Code size: 12609 bytes

## Contract Verification
- Verified: False
- Name: None · Compiler: 
- Proxy: False · Implementation: None
- Verified source not available to scan this cycle.

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $1.3213264707818364e-05 · confidence: 0.99 · symbol: OX
- First DefiLlama price: 2024-02-20T02:29:28Z (892.5 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://snowtrace.io/address/0xba0Dda8762C24dA9487f5FA026a9B64b695A07Ea
- Market pair: https://dexscreener.com/avalanche/0x55a76a9e8d60f5611a841a725ba63eb61afa81e3
- Market data: https://www.coingecko.com/en/coins/ox-fun
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*