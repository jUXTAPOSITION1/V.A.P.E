<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — 币有

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![75/100](https://img.shields.io/badge/SAFETY_SCORE-75%2F100-86BC52?style=flat-square)

- **Target:** `0xd0bc8Ab397851ECfa58009D03bBc1a41FC764444`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-27T22:00:18Z
- **Verdict:** CAUTION (75/100)

---

## Executive Summary
**Overall: CAUTION (75/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 100/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Violent 24h move +591% (volatility/manipulation)
- [-5] Pair 25.4 days old — under a month, still unproven
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- 9245 holders — reasonably distributed
- 100% of liquidity is locked — reduced rug-pull risk
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +591% (volatility/manipulation)
  - [-5] Pair 25.4 days old — under a month, still unproven
**Holder Distribution & Liquidity** — 0 flag(s), 2 positive signal(s)
  - (positive) 9245 holders — reasonably distributed
  - (positive) 100% of liquidity is locked — reduced rug-pull risk
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

This token's on-chain profile and market footprint point to a Chinese-language meme play rather than any utility project. The contract name "Token" plus the trading pair phrasing ("币有/何必东奔西走 币安全部都有") read as slang-heavy wordplay around "having coins" and Binance references, consistent with a community hype token that launched roughly 25 days ago and has since drawn 9,245 wallets. The combination of renounced ownership, fully locked liquidity, zero mint capability, and zero taxes aligns with a deliberate effort to remove classic rug vectors, while the 3.8 kB custom verified source (not a clone) suggests someone put in minimal but non-factory effort. The 591 % price spike on 4.27 M USD volume against only 124 k USD liquidity fits the pattern of a low-float meme catching retail attention on PancakeSwap; nothing in the data indicates hidden minting, proxy upgrades, or honeypot logic.

The rule-based score overweighted the age/volatility pair because those traits are expected (and often priced in) for this category; it underweighted the concrete distribution and renouncement signals that materially reduce rug probability once liquidity is locked. A remaining gap is the lack of any on-chain or off-chain trace of the deployer wallet's prior activity or any concentrated holder cluster that could still exert outsized sell pressure.

Next step: pull the top-20 holder list and their cumulative buy/sell flows over the last 72 hours to quantify whether distribution is genuinely broad or dominated by a small number of wallets that entered early.

## Market & Liquidity
- Symbol/Name: 币有 / 何必东奔西走 币安全部都有
- Price: $0.001050
- Liquidity: $124350.25
- 24h Volume: $4276001.35
- 24h Change: 591%
- DEX: pancakeswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `9245`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 29.0% of supply
- 100.0% of tracked liquidity-pool tokens are locked (across 2 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 3822 bytes

## Contract Verification
- Verified: True
- Name: Token · Compiler: v0.8.20+commit.a1b79de6
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, renounceOwnership, transferOwnership

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
- Block explorer: https://bscscan.com/address/0xd0bc8Ab397851ECfa58009D03bBc1a41FC764444
- Market pair: https://dexscreener.com/bsc/0x844d4f95ca2c355d831c7fbdf7ba55924a0e0600
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*