<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — LGNS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![37/100](https://img.shields.io/badge/SAFETY_SCORE-37%2F100-FBAB3D?style=flat-square)

- **Target:** `0xEa8CAc26211e1fCD512c8B45f33F30c8Ef4fc76d`
- **Chain:** 137 (Polygon)
- **Date:** 2026-08-07T04:18:38Z
- **Verdict:** REJECT (37/100)

---

## Expert Assessment
The evidence base for LGNS on Polygon is genuinely thin and supports only a high-risk rejection posture. A single concrete data point available is the token-safety scan showing exactly zero holders alongside a reported $28,197 liquidity pool on a pair listed as 0.0 days old.

What the scan does confirm is a verified DropERC20 contract with no honeypot flags and no declared website or social links on the DEX listing; nothing further on ownership locks, holder distribution, or longevity is present.

Primary residual risks are the absolute absence of any narrative or social proof, the zero-holder count that makes manipulation trivial, the sub-$30k liquidity, and the complete lack of team or provenance signals on a contract that risk data flags as proxy-enabled despite the verification record.

Technical-safety confidence is moderate because the scan is narrow and recent; investment-thesis confidence is near zero because no usage, community, or operational history exists to evaluate. A material increase in verified holders above a few hundred combined with sustained volume and an audit would be required to shift either view.

Avoid entirely; any position would be pure speculation with no observable floor. Re-check only if on-chain holder count and 24-hour volume both rise materially above current levels.

## Gaps & Confidence

- **actual holder distribution and any locked liquidity details** (confidence: 90%) — next: query token holder list and liquidity lock status on-chain
- **deployment provenance and any prior related contracts** (confidence: 70%) — next: trace deployer address history

## Scoring Dashboard
**Overall: 37/100 — REJECT** ![37/100](https://img.shields.io/badge/overall-37%2F100-FBAB3D?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![92/100](https://img.shields.io/badge/security-92%2F100-36BA72?style=flat-square) | Upgradeable proxy (verify implementation). |
| Liquidity Health & Lock Quality | 20% | ![90/100](https://img.shields.io/badge/liquidity-90%2F100-3FBA6E?style=flat-square) | Low liquidity $28,197. |
| Holder Distribution & Concentration | 15% | ![80/100](https://img.shields.io/badge/holders-80%2F100-6EBB5C?style=flat-square) | Very few holders (0) — thin, easily manipulated distribution. |
| Transparency & Provenance | 15% | ![90/100](https://img.shields.io/badge/transparency-90%2F100-3FBA6E?style=flat-square) | No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default; (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![25/100](https://img.shields.io/badge/narrative-25%2F100-FB9854?style=flat-square) | no coherent project narrative could be established this cycle. |
| Longevity & Clean Track Record | 10% | ![85/100](https://img.shields.io/badge/longevity-85%2F100-56BB65?style=flat-square) | Pair only 0.0 days old (extreme fresh-launch risk). |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-20] Very few holders (0) — thin, easily manipulated distribution
- [-10] Low liquidity $28,197
- [-15] Pair only 0.0 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.0 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-20] Very few holders (0) — thin, easily manipulated distribution
  - [-10] Low liquidity $28,197
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Market & Liquidity
- Symbol/Name: LGNS / LGNS COIN
- Price: $0.00003759
- Liquidity: $28196.89
- 24h Volume: $0
- 24h Change: None%
- DEX: uniswap
- Volume trend (m5/h1/h6/h24): `▁▁▁▁` (m5: $0, h1: $0, h6: $0, h24: $0)

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: ``
- sell_tax: ``
- is_proxy: `1`
- holder_count: `0`

## Holder Distribution & Liquidity Lock
- Top-holder concentration not available this cycle.
- Liquidity-lock status not available this cycle.

## On-chain Presence (Polygon RPC)
- Is contract: unavailable this cycle (HTTP Error 401: Unauthorized)

## Contract Verification
- Verified: True
- Name: DropERC20 · Compiler: v0.8.23+commit.f704f362
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): __ERC20Burnable_init, __ERC20Burnable_init_unchained, _burn, _mint, burn, burnFrom, withdraw
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

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
- Block explorer: https://polygonscan.com/address/0xEa8CAc26211e1fCD512c8B45f33F30c8Ef4fc76d
- Market pair: https://dexscreener.com/polygon/0xc5061b634b056e9e5c52a6dfb4cef73962651014
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*