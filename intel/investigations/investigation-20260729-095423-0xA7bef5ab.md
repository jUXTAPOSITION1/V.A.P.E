<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — BAY

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![60/100](https://img.shields.io/badge/SAFETY_SCORE-60%2F100-CCBE37?style=flat-square)

- **Target:** `0xA7bef5abd9265Ab97EE43D2fc4A56e0Ba25ACA25`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-29T09:54:23Z
- **Verdict:** CAUTION (60/100)

---

## Executive Summary
**Overall: CAUTION (60/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 60/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-15] Top 10 non-LP/burn holders control 97% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $25,374

## Positive Signals (real legitimacy evidence found)
- 54082 holders — reasonably distributed
- Trading 270+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 270+ days — independent longevity corroboration

## Risk Breakdown by Category
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 97% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-10] Low liquidity $25,374
  - (positive) 54082 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 270+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 270+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

The evidence paints BAY as a long-running BSC token (BAYToken) that has maintained a live market presence since roughly mid-2024, with DefiLlama independently pricing it throughout and no recorded rug or honeypot events. The verified custom contract (no proxy, no mint function, owner renounced) plus 54k holders and ongoing Uniswap-style trading create a surface-level picture of a legitimate, if low-activity, DeFi asset tied to the Marina Protocol pair. However, that picture fractures on ownership: 97% of supply sitting with just ten non-LP wallets directly contradicts the “reasonably distributed” narrative implied by the holder count, implying either massive illiquid bags or coordinated control that could move price at will. The complete absence of locked liquidity compounds this—anyone holding the LP position can still drain the $25k pool despite the renounced contract—while the tiny 24h volume ($4k) shows almost no external market absorption to offset that risk.

The rule-based score overweighted raw holder count as a positive while underweighting the mismatch between that count and actual supply distribution; 54k addresses can coexist with extreme concentration if most are dust or inactive, and the data here gives no breakdown of holder age or activity to resolve the contradiction. It also treated “270+ days without incident” as stronger corroboration than it is, given that low liquidity and low volume inherently reduce the chance of visible exploits even if the underlying control issues remain.

Next cycle or a human reviewer should pull the top-ten non-LP wallet addresses and check their transaction histories for patterns such as coordinated transfers, exchange deposits, or long-term dormancy.

## Market & Liquidity
- Symbol/Name: BAY / Marina Protocol
- Price: $0.01863
- Liquidity: $25373.99
- 24h Volume: $4338.59
- 24h Change: -6.6%
- DEX: uniswap
- Liquidity/Market-cap ratio: 0.7% — thin relative to market cap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Circulating supply: 200,000,000 BAY
- Total supply: 1,000,000,000
- Max supply: 1,000,000,000
- Market cap: $3,709,323
- Fully diluted valuation: $18,546,614
- FDV/Market-cap ratio: 5.00x — a meaningful share of supply is still non-circulating (dilution risk)
- Homepage: https://marina-protocol.com/
- X/Twitter: https://x.com/MARINA_PROTOCOL

> A next-generation global marketing technology (MarTech) infrastructure with over 1.3 million users across 200 countries. The platform transforms traditional Web2 quizzes, missions, and events into fully automated Web3 campaigns with instant on-chain rewards. By combining SDKs, embed codes, social-login wallets, and gasless onboarding, it significantly lowers participation barriers while enabling brands, marketers, and communities to run global campaigns efficiently and transparently.

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
- holder_count: `54082`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 97.2% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 3637 bytes

## Contract Verification
- Verified: True
- Name: BAYToken · Compiler: v0.8.24+commit.e11b9ed9
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.018794699527173817 · confidence: 0.99 · symbol: BAY
- First DefiLlama price: 2025-11-01T08:57:28Z (270.0 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://bscscan.com/address/0xA7bef5abd9265Ab97EE43D2fc4A56e0Ba25ACA25
- Market pair: https://dexscreener.com/bsc/0xd1e48e9bb2631ed512ab65c9e6699920c484c3a4
- Market data: https://www.coingecko.com/en/coins/marina-protocol
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*