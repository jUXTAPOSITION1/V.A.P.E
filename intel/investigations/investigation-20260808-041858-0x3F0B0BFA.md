<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — OPENAI

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0x3F0B0BFA0418C2a050340bc01347E7343F9a1bA3`
- **Chain:** 8453 (Base)
- **Date:** 2026-08-08T04:18:58Z
- **Verdict:** REJECT (0/100)

---

## Expert Assessment
This token carries extreme risk and shows no credible signs of legitimacy. The evidence base is genuinely thin, consisting solely of on-chain contract data with no external corroboration or market history.

What the data does show is a 4.5-day-old Uniswap pair, ten total holders, and full supply control by the top nine non-LP addresses, alongside an active owner at 0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12 and an upgradeable proxy structure.

Primary residual risks are the explicit name/symbol impersonation of OpenAI with zero affiliation, complete absence of declared website or social links, negligible liquidity and volume, and the unaudited anonymous deployment.

Technical-safety signals can be read with moderate confidence from the verified contract scan, but overall investment viability rests on almost no supporting information. The view would shift only with verifiable renouncement, liquidity lock, and independent third-party coverage that directly addresses the impersonation pattern.

Avoid any position; the combination of concentration, control, and mimicry makes even small speculative exposure unwarranted.

## Gaps & Confidence

- **No external web or social footprint located** (confidence: 95%) — next: Manual search for any off-chain references tied to the exact contract address

## Scoring Dashboard
**Overall: 0/100 — REJECT** ![0/100](https://img.shields.io/badge/overall-0%2F100-FB7185?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![82/100](https://img.shields.io/badge/security-82%2F100-65BB60?style=flat-square) | Upgradeable proxy (verify implementation); Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act on the contract. |
| Liquidity Health & Lock Quality | 20% | ![100/100](https://img.shields.io/badge/liquidity-100%2F100-10B981?style=flat-square) | No signal either way this cycle. |
| Holder Distribution & Concentration | 15% | ![65/100](https://img.shields.io/badge/holders-65%2F100-B4BD40?style=flat-square) | Very few holders (10) — thin, easily manipulated distribution; Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipulated. |
| Transparency & Provenance | 15% | ![55/100](https://img.shields.io/badge/transparency-55%2F100-E4BE2D?style=flat-square) | Token name/symbol (OPEN AI / OPENAI) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence; No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default; (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![25/100](https://img.shields.io/badge/narrative-25%2F100-FB9854?style=flat-square) | no coherent project narrative could be established this cycle. |
| Longevity & Clean Track Record | 10% | ![90/100](https://img.shields.io/badge/longevity-90%2F100-3FBA6E?style=flat-square) | Pair 4.5 days old — under two weeks, no track record yet. |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-10] Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act on the contract
- [-35] Token name/symbol (OPEN AI / OPENAI) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence
- [-20] Very few holders (10) — thin, easily manipulated distribution
- [-15] Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-10] Pair 4.5 days old — under two weeks, no track record yet
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 2 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
  - [-10] Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act on the contract
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-35] Token name/symbol (OPEN AI / OPENAI) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence
  - [-10] Pair 4.5 days old — under two weeks, no track record yet
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-20] Very few holders (10) — thin, easily manipulated distribution
  - [-15] Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Market & Liquidity
- Symbol/Name: OPENAI / OPEN AI
- Price: $0.0000001056
- Liquidity: $None
- 24h Volume: $4.82
- 24h Change: None%
- DEX: uniswap
- Volume trend (m5/h1/h6/h24): `▁▁▁█` (m5: $0, h1: $0, h6: $0, h24: $5)

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: ``
- sell_tax: ``
- is_proxy: `1`
- holder_count: `10`
- owner_address: `0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12`

## Holder Distribution & Liquidity Lock
- Top 9 non-LP/burn holders control 100.0% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 44 bytes

## Contract Verification
- Verified: True
- Name: DopplerERC20V1 · Compiler: v0.8.26+commit.8a97fa7a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _setOwner, burn, renounceOwnership, transferOwnership

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 2 of VAPE's own x402 market-data offerings against this token (real USDC on Base, 0 settled, $0.00 total):
  - **chain_fees** (failed, cdp) — error — HTTP 500
  - **token_intel** (failed, vapor) — error — HTTP 500

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://basescan.org/address/0x3F0B0BFA0418C2a050340bc01347E7343F9a1bA3
- Market pair: https://dexscreener.com/base/0x664bd40c2ba74bd6a71e225e7ae7d90253f53106622546c045249ceaf0d9d183
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*