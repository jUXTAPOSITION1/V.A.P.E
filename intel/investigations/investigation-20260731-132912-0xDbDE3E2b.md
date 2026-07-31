<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — CZ Moon

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![45/100](https://img.shields.io/badge/SAFETY_SCORE-45%2F100-FBB72E?style=flat-square)

- **Target:** `0xDbDE3E2bA260d988E16bB61aCAeB4331b0884444`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-31T13:29:12Z
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
- [-10] Violent 24h move +245% (volatility/manipulation)
- [-15] Pair only 0.0 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +245% (volatility/manipulation)
  - [-15] Pair only 0.0 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 1 flag(s), 0 positive signal(s)
  - [-20] Very few holders (0) — thin, easily manipulated distribution
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints CZ Moon as an ultra-fresh BSC deployment on the fourmeme DEX whose contract was just verified with custom (non-template) Solidity. That single positive signal is immediately undercut by the complete absence of any holder distribution, a liquidity figure reported as none, and a 245 % price swing on only ~$9.5 k of volume; together these indicate the token was minted, paired, and immediately traded in the same block window, with zero external wallets yet able to accumulate. The generic on-chain name “Token” and empty tax/mint/owner fields further suggest the deployer either retained full control or simply has not yet configured the contract, both of which are classic early-stage rug vectors rather than signs of a maturing project.

The rule-based score correctly weights the zero-holder and zero-day-pair facts as dominant red flags; it does not appear to overweight anything, because the lone mitigating detail (custom source) cannot offset an empty holder set or missing liquidity on a platform already known for rapid meme launches.

Next cycle or a human analyst should pull the exact creation transaction and the first liquidity-add event to map the deployer address and any linked wallets that may have seeded the pool.

## Market & Liquidity
- Symbol/Name: CZ Moon / CZ Moon
- Price: $0.00004012
- Liquidity: $None
- 24h Volume: $9468.13
- 24h Change: 245%
- DEX: fourmeme

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: ``
- sell_tax: ``
- holder_count: `0`
- owner_address: ``

## Holder Distribution & Liquidity Lock
- Top-holder concentration not available this cycle.
- Liquidity-lock status not available this cycle.

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
- Block explorer: https://bscscan.com/address/0xDbDE3E2bA260d988E16bB61aCAeB4331b0884444
- Market pair: https://dexscreener.com/bsc/0xdbde3e2ba260d988e16bb61acaeb4331b0884444:4meme
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*