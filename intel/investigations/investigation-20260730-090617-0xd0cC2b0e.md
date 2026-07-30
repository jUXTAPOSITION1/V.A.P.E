<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — VIBESTR

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![52/100](https://img.shields.io/badge/SAFETY_SCORE-52%2F100-F2BF28?style=flat-square)

- **Target:** `0xd0cC2b0eFb168bFe1f94a948D8df70FA10257196`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-30T09:06:17Z
- **Verdict:** CAUTION (52/100)

---

## Executive Summary
**Overall: CAUTION (52/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 82/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 100/100 |
| Transparency & Provenance | 70/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-10] Owner not renounced (0x019817ad02a31b990433542097be29d97613e8cb) — can still act on the contract
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: FWA (0x47883e389BB6be3650B0C0935b300b50a95fc072) — REJECT 35/100 — likely the same serial campaign

## Positive Signals (real legitimacy evidence found)
- 1269 holders — reasonably distributed
- Deep liquidity ($561,555)
- Trading 294+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 294+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 2 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
  - [-10] Owner not renounced (0x019817ad02a31b990433542097be29d97613e8cb) — can still act on the contract
**Holder Distribution & Liquidity** — 0 flag(s), 2 positive signal(s)
  - (positive) 1269 holders — reasonably distributed
  - (positive) Deep liquidity ($561,555)
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-30] Same deployer has a prior CAUTION/REJECT verdict on record: FWA (0x47883e389BB6be3650B0C0935b300b50a95fc072) — REJECT 35/100 — likely the same serial campaign
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 294+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 294+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

The evidence paints VibeStrategy as a persistent, low-volume Uniswap token that has maintained deep liquidity and a distributed holder base for nearly 300 days without recorded exploits or honeypot behavior. The verified custom source and DefiLlama pricing history support a picture of a live project rather than a quick-exit template, yet this sits uneasily against the non-renounced owner address that still controls the contract and the direct link to the same deployer’s earlier FWA token, which received a much harsher rejection. The 121-byte contract size and zero taxes are consistent with a minimal, long-running implementation, but the conflicting proxy signals—one dataset flags upgradeability while verification explicitly states proxy=False—introduce an unresolved structural question about whether the owner can still alter logic post-deployment.

The rule-based score appears to overweight the serial-deployer correlation without enough weight on the 294-day survival metric and liquidity depth, which together reduce the probability of an imminent rug relative to fresh launches from the same wallet. At the same time it may underweight the owner-control risk because no on-chain activity log for that address is provided here, leaving open whether the control has been exercised benignly or is simply dormant.

Next step: pull the transaction history for the owner address 0x019817ad02a31b990433542097be29d97613e8cb specifically on this contract to see whether any privileged functions have been called since launch, and cross-reference the exact same address’s activity on the FWA token for pattern matching.

## Market & Liquidity
- Symbol/Name: VIBESTR / VibeStrategy
- Price: $0.001939
- Liquidity: $561555.07
- 24h Volume: $1817.34
- 24h Change: -1.32%
- DEX: uniswap
- Liquidity/Market-cap ratio: 39.6% — reasonable depth for its size

## Project Links
- Website: https://www.goodvibesclub.io/
- Website: https://opensea.io/collection/good-vibes-club
- twitter: https://x.com/goodvibesclub
- telegram: https://t.me/GoodVibesClub
- discord: https://discord.com/invite/goodvibesclub

## Tokenomics (address-verified)
- Circulating supply: 729,081,671 VIBESTR
- Total supply: 729,081,671
- Max supply: 1,000,000,000
- Market cap: $1,416,949
- Fully diluted valuation: $1,416,949
- FDV/Market-cap ratio: 1.00x — most of supply is already circulating
- Homepage: https://www.nftstrategy.fun/strategies/0xd0cc2b0efb168bfe1f94a948d8df70fa10257196
- X/Twitter: https://x.com/token_works

## Token Security
- buy_tax: `0`
- sell_tax: `0`
- is_proxy: `1`
- holder_count: `1269`
- owner_address: `0x019817ad02a31b990433542097be29d97613e8cb`

## Holder Distribution & Liquidity Lock
- Top 9 non-LP/burn holders control 30.9% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 121 bytes

## Contract Verification
- Verified: True
- Name: VibeStrategy · Compiler: v0.8.30+commit.73712a01
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _buyAndBurnTokens, _mint, _mintAndSetExtraDataUnchecked, _safeMint, _setOwner, burn, mint, pendingWithdrawals, renounceOwnership, transferOwnership, upgradeToAndCall, withdraw
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.0019417268692359265 · confidence: 0.99 · symbol: VIBESTR
- First DefiLlama price: 2025-10-09T18:01:32Z (293.6 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0xd0cC2b0eFb168bFe1f94a948D8df70FA10257196
- Market pair: https://dexscreener.com/ethereum/0x56c8fc0c410ec0778484600246847e2e77c428f888a35a11351dc12bbff09c6d
- Market data: https://www.coingecko.com/en/coins/vibestrategy
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*