<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — BLUAI

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![60/100](https://img.shields.io/badge/SAFETY_SCORE-60%2F100-CCBE37?style=flat-square)

- **Target:** `0xed9Ae3DEF8d6F052971Bb8b6d1975FF267Cf9aaD`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-29T18:16:18Z
- **Verdict:** CAUTION (60/100)

---

## Executive Summary
**Overall: CAUTION (60/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 70/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x8f8063ac8917a4c752f0bf0c16d0f22f1ce454fd) — can still act on the contract
- [-15] Top 10 non-LP/burn holders control 88% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- 38901 holders — reasonably distributed
- Deep liquidity ($726,592)
- Trading 282+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 281+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x8f8063ac8917a4c752f0bf0c16d0f22f1ce454fd) — can still act on the contract
**Holder Distribution & Liquidity** — 2 flag(s), 2 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 88% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 38901 holders — reasonably distributed
  - (positive) Deep liquidity ($726,592)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 282+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 281+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

The evidence paints BLUAI as a roughly nine-month-old BSC token (BlueWhaleToken) that reached meaningful scale—$726k liquidity on PancakeSwap, steady daily volume, and 38k+ holders—without triggering a honeypot or tax exploit. Its verified custom contract, zero mint capability, and DefiLlama pricing history all line up with a project that survived the typical early rug window and is still actively traded.  

However, the same data set reveals a persistent control layer that never went away: the original deployer still holds the owner role, zero liquidity is locked, and the top ten wallets (non-LP) sit on 88 % of supply. These three facts connect directly—unlocked LP plus concentrated holdings plus an active owner create a low-friction exit path that the 281-day track record has not closed. The large holder count therefore does not signal broad distribution; it mainly shows retail wallets layered on top of a whale-heavy cap table that has not been diluted or renounced.

The rule-based 60/100 score correctly flags the structural risks but under-weights how little the longevity actually mitigates them. Nine months of survival is reassuring only if the owner has demonstrated restraint; here the contract still permits the same actions that would enable a pull today. The “no incident” signal is therefore weaker than it appears because the preconditions for an incident remain fully intact.

Next concrete check: pull the full transaction history and token-balance changes for the owner address 0x8f8063ac8917a4c752f0bf0c16d0f22f1ce454fd to see whether it has ever moved large BLUAI amounts or interacted with other tokens in a pattern consistent with prior launches.

## Market & Liquidity
- Symbol/Name: BLUAI / Bluwhale AI
- Price: $0.01195
- Liquidity: $726592.44
- 24h Volume: $72900.1
- 24h Change: -4.32%
- DEX: pancakeswap
- Liquidity/Market-cap ratio: 4.9% — reasonable depth for its size

## Project Links
- Website: https://www.bluwhale.com/
- Website: https://bluwhale.gitbook.io/bluwhaleai/
- Website: https://medium.com/@bluwhaleai
- Website: https://www.youtube.com/@bluwhaleai
- twitter: https://x.com/bluwhaleai
- telegram: https://t.me/bluwhaleofficial
- discord: https://discord.gg/bluwhale

## Tokenomics (address-verified)
- Circulating supply: 1,228,000,000 BLUAI
- Total supply: 10,000,000,000
- Max supply: 10,000,000,000
- Market cap: $14,736,101
- Fully diluted valuation: $120,000,825
- FDV/Market-cap ratio: 8.14x — a meaningful share of supply is still non-circulating (dilution risk)
- Homepage: https://www.bluwhale.com/
- X/Twitter: https://x.com/bluwhaleai

> BluWhale is Web3’s Intelligence Layer — a consumer-powered decentralized AI network where developers and enterprises deploy AI agents to serve 3.6 million users with financial services. Backed by UOB Venture Management and SBI Holdings and integrated with chains including Sui, Arbitrum, Tezos, Cardano, and Movement Labs, BluWhale builds a multi-chain infrastructure for AI-driven financial intelligence. Its TGE on October 21 2025 introduces $BLUAI for gas fees, governance, staking, and node operations.

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
- holder_count: `38901`
- owner_address: `0x8f8063ac8917a4c752f0bf0c16d0f22f1ce454fd`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 88.3% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 10 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 2059 bytes

## Contract Verification
- Verified: True
- Name: BlueWhaleToken · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, renounceOwnership, transferOwnership

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.012020818978038595 · confidence: 0.99 · symbol: BLUAI
- First DefiLlama price: 2025-10-21T12:22:04Z (281.2 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://bscscan.com/address/0xed9Ae3DEF8d6F052971Bb8b6d1975FF267Cf9aaD
- Market pair: https://dexscreener.com/bsc/0xba20fe9506a904a30ebb8b7c348f4969f5a5ea07
- Market data: https://www.coingecko.com/en/coins/bluwhale
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*