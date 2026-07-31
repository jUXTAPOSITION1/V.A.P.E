<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — WMATIC

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![40/100](https://img.shields.io/badge/SAFETY_SCORE-40%2F100-FBAF37?style=flat-square)

- **Target:** `0xDbE20ADb609420Db52cc3093478aB334D1E3f57A`
- **Chain:** 137 (Polygon)
- **Date:** 2026-07-31T06:56:55Z
- **Verdict:** REJECT (40/100)

---

## Executive Summary
**Overall: REJECT (40/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-20] Very few holders (8) — thin, easily manipulated distribution
- [-15] Top 8 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Deep liquidity ($26,829,721)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-20] Very few holders (8) — thin, easily manipulated distribution
  - [-15] Top 8 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) Deep liquidity ($26,829,721)
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence points to a low-effort wrapper or mimic token rather than any legitimate project. The contract is verified under the name TeamToken yet trades on Sushi as WMATIC/Wrapped Polygon at a price far below canonical MATIC; the canonical WMATIC address on Polygon is a completely different contract (0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270), so this is not an official or bridged version. With only eight holders controlling the entire supply and essentially zero 24 h volume against a $26.8 M liquidity pool, the pool depth cannot represent organic market-making; it is almost certainly liquidity seeded and still controlled by those same eight addresses. The fact that ownership is listed as None and zero percent of liquidity is locked simply confirms the deployer (or the handful of large holders) retains the practical ability to drain the pool at any time. The “custom verified source” signal does not offset this; a non-factory contract can still be a minimal wrapper with no additional safeguards.

The rule-based score correctly flags the concentration and unlocked liquidity but under-weights the mismatch between reported liquidity depth and actual trading activity; that gap is the clearest red flag that the pool is cosmetic rather than functional. It also slightly over-weights the “no audit” item, since an audit would be irrelevant once the holder distribution already shows the token is not circulating.

Next step: pull the LP-token balance sheet for the Sushi pair and trace the top holders of those LP tokens to see whether they overlap with the eight token holders already identified.

## Market & Liquidity
- Symbol/Name: WMATIC / Wrapped Polygon
- Price: $0.05661
- Liquidity: $26829721.32
- 24h Volume: $0.23
- 24h Change: None%
- DEX: sushiswap

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
- holder_count: `8`

## Holder Distribution & Liquidity Lock
- Top 8 non-LP/burn holders control 100.0% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Polygon RPC)
- Is contract: unavailable this cycle (HTTP Error 401: Unauthorized)

## Contract Verification
- Verified: True
- Name: TeamToken · Compiler: v0.6.12+commit.27d51765
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
- Block explorer: https://polygonscan.com/address/0xDbE20ADb609420Db52cc3093478aB334D1E3f57A
- Market pair: https://dexscreener.com/polygon/0x362f4ed7efb3514803030678256e691a26bf8980
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*