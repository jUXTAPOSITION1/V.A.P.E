<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — gLGNS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![7/100](https://img.shields.io/badge/SAFETY_SCORE-7%2F100-FB7C77?style=flat-square)

- **Target:** `0x85bAbbd6124589F5Ef3AE12a2745267cc1852f42`
- **Chain:** 137 (Polygon)
- **Date:** 2026-07-26T04:55:25Z
- **Verdict:** REJECT (7/100)

---

## Executive Summary
**Overall: REJECT (7/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 90/100 |
| Holder Distribution & Liquidity | 27/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Low holder count (68)
- [-15] Top 10 non-LP/burn holders control 95% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $41 (rug/illiquid)
- [-10] Low liquidity $41
- [-10] Violent 24h move +166% (volatility/manipulation)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +166% (volatility/manipulation)
**Holder Distribution & Liquidity** — 5 flag(s), 0 positive signal(s)
  - [-8] Low holder count (68)
  - [-15] Top 10 non-LP/burn holders control 95% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $41 (rug/illiquid)
  - [-10] Low liquidity $41
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

This token presents as a minimal, likely abandoned or experimental deployment on Polygon (Uniswap V2 pair), with a verified contract named BananaToken that bears no evident connection to any broader project, website, or community. The renounced ownership combined with GoPlus flags confirming zero mint capability, zero taxes, and no proxy strongly indicates the deployer has no remaining technical levers to drain or inflate supply directly. Yet this does not create a coherent legitimate picture: the 95% concentration in the top 10 non-LP wallets, paired with only $41 in liquidity and a 166% single-day swing on $114 volume, points instead to a closed circle of holders who can (and apparently do) move the price at will with negligible capital. The extreme illiquidity and zero locked LP further mean any exit attempt by outsiders would be impossible without total slippage, rendering the token non-functional as a trading vehicle regardless of its "safe" contract parameters.

The rule-based score correctly weights the concentration and liquidity risks as dominant, but underweights the verified custom source as a mild positive signal of non-malicious intent (most rugs reuse factory templates precisely to hide malicious code). No evidence gap here suggests hidden minting or honeypot behavior that the score missed.

Next check: pull the full verified source from Polygonscan for 0x85bAbbd6124589F5Ef3AE12a2745267cc1852f42 and inspect the constructor plus any transfer or balance logic for non-standard behavior.

## Market & Liquidity (DexScreener)
- Symbol/Name: gLGNS / gLGNS
- Price: $0.01269
- Liquidity: $41.06
- 24h Volume: $114.5
- 24h Change: 166%
- DEX: uniswap

## Project Links (as declared on DexScreener)
- No official website/social links declared on this token's DexScreener listing.

## Tokenomics (CoinGecko, address-verified)
- Not available this cycle (CoinGecko does not track this exact contract address, or the token isn't listed there yet) — absence noted, not penalized.

## Token Security (GoPlus)
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
- holder_count: `68`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 10 non-LP/burn holders control 95.0% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 2 LP holder(s))

## On-chain Presence (Polygon RPC)
- Is contract: unavailable this cycle (HTTP Error 401: Unauthorized)

## Contract Verification
- Verified: True
- Name: BananaToken · Compiler: v0.8.20+commit.a1b79de6
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _transferOwnership, renounceOwnership, transferOwnership

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
- Block explorer: https://polygonscan.com/address/0x85bAbbd6124589F5Ef3AE12a2745267cc1852f42
- DexScreener pair: https://dexscreener.com/polygon/0x564b06522f0accfc9078b44b90e5b3b4ef2b5830
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*