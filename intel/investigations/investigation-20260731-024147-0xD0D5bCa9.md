<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — SNP500

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![40/100](https://img.shields.io/badge/SAFETY_SCORE-40%2F100-FBAF37?style=flat-square)

- **Target:** `0xD0D5bCa9Eaa78A5056A28d4064438af3fA1352a9`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-31T02:41:47Z
- **Verdict:** REJECT (40/100)

---

## Executive Summary
**Overall: REJECT (40/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 65/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-20] Very few holders (3) — thin, easily manipulated distribution
- [-15] Top 3 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Pair only 0.0 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.0 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-20] Very few holders (3) — thin, easily manipulated distribution
  - [-15] Top 3 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints SNP500 as an ultra-fresh, three-wallet deployment on Uniswap whose entire supply sits in the hands of its creators with zero external distribution yet. The custom (non-factory) verified UERC20 contract and zero taxes/no honeypot flags suggest the deployer put in minimal effort to avoid obvious red flags, but the pairing against two other obscure meme-named assets plus the complete absence of liquidity data and $9 volume after launch point to a closed-loop setup rather than any genuine market or community. Nothing in the on-chain footprint or token-safety results contradicts the picture of an anonymous team retaining full control over a brand-new token whose name invokes a stock index for branding only.

The rule-based score correctly flags the concentration and age risks but underweights the empty owner field combined with verified source code; that combination implies the deployer may have already renounced or never set privileged functions, which is a concrete (if narrow) positive signal worth separating from generic “new token” penalties.

Next step: pull the three holder addresses and trace their funding source plus any prior contract interactions to see whether this is a single-operator test or coordinated wallets.

## Market & Liquidity
- Symbol/Name: SNP500 / Sock and Pussy 500
- Price: $0.000002664
- Liquidity: $None
- 24h Volume: $9.37
- 24h Change: None%
- DEX: uniswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: `0`
- sell_tax: `0`
- cannot_sell_all: `0`
- holder_count: `3`
- owner_address: ``

## Holder Distribution & Liquidity Lock
- Top 3 non-LP/burn holders control 100.0% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 7154 bytes

## Contract Verification
- Verified: True
- Name: UERC20 · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint

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
- Block explorer: https://etherscan.io/address/0xD0D5bCa9Eaa78A5056A28d4064438af3fA1352a9
- Market pair: https://dexscreener.com/ethereum/0xcb92348c4eabd21a0a45a89606b9fa6fc671f532e367e285122b0fa88cff5fee
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*