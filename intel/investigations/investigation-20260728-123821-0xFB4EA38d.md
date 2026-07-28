<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — 币有

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![45/100](https://img.shields.io/badge/SAFETY_SCORE-45%2F100-FBB72E?style=flat-square)

- **Target:** `0xFB4EA38d713afBb3eD35869B790aec3CA53B0000`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-28T12:38:21Z
- **Verdict:** REJECT (45/100)

---

## Executive Summary
**Overall: REJECT (45/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 75/100 |
| Holder Distribution & Liquidity | 80/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-20] Very few holders (0) — thin, easily manipulated distribution
- [-10] Violent 24h move +1560% (volatility/manipulation)
- [-15] Pair only 0.0 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +1560% (volatility/manipulation)
  - [-15] Pair only 0.0 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 1 flag(s), 0 positive signal(s)
  - [-20] Very few holders (0) — thin, easily manipulated distribution
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints a picture of a zero-substance launch engineered for rapid volume inflation rather than any functional token or community. A contract that is verified, non-proxy, and non-mintable with renounced ownership would normally reduce certain rug vectors, yet those traits sit alongside literally zero holders, a pair that is minutes old, and $44 M in 24 h volume on only $64 k liquidity. That volume figure cannot be organic trading; it is almost certainly wash trading or coordinated bot activity across a single pool, which is consistent with the reported 1560 % price swing. The Chinese pair name and generic “TokenERC” label add no project substance—they function only as marketing flavor on an otherwise empty deployment. Nothing in the on-chain or market data suggests an actual product, treasury, or user base; the combination instead matches the pattern of a short-lived pump vehicle that will collapse once the volume bots move on.

The rule-based score correctly flags the thin distribution and fresh-pair risk but under-weights the internal contradiction between zero holders and tens of millions in reported volume; that single mismatch is stronger evidence of manipulation than any of the individual risk factors taken alone. It also slightly over-weights the “ownership renounced” signal, which loses relevance when there are no holders to protect in the first place.

Next step: pull the first 50 transactions that created the liquidity pair and seeded the initial LP tokens to identify the deployer wallet(s) and any subsequent large transfers out of that wallet.

## Market & Liquidity
- Symbol/Name: 币有 / 何必东奔西走 币安全部都有
- Price: $0.00003505
- Liquidity: $64288.02
- 24h Volume: $44521762.04
- 24h Change: 1560%
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
- holder_count: `0`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock
- Top-holder concentration not available this cycle.
- Liquidity-lock status not available this cycle.

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 8249 bytes

## Contract Verification
- Verified: True
- Name: TokenERC · Compiler: v0.8.36+commit.8a079791
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _setImplementation, _transferOwnership, renounceOwnership, transferOwnership

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
- Block explorer: https://bscscan.com/address/0xFB4EA38d713afBb3eD35869B790aec3CA53B0000
- Market pair: https://dexscreener.com/bsc/0x9b65e79cddd88aebab79874df613a2c06eb76f56
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*