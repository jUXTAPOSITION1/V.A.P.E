<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — BTW

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0x2FcB6f3d1Be8F16002B101ee3182eD9668797777`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-08-02T12:44:43Z
- **Verdict:** REJECT (0/100)

---

## Executive Summary
**Overall: REJECT (0/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 92/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 30/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-20] Very few holders (5) — thin, easily manipulated distribution
- [-15] Top 5 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-25] Very low liquidity $7,149 (rug/illiquid)
- [-10] Low liquidity $7,149
- [-15] Pair only 0.8 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 1 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
  - (positive) Ownership renounced
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.8 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 4 flag(s), 0 positive signal(s)
  - [-20] Very few holders (5) — thin, easily manipulated distribution
  - [-15] Top 5 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-25] Very low liquidity $7,149 (rug/illiquid)
  - [-10] Low liquidity $7,149
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence gathered this cycle is thin, limited to on-chain metrics and automated risk flags with no external pages, news, or third-party reports available for cross-check. One concrete detail present is the verified contract name FlapTaxTokenV3 on BSC with ownership renounced and a 0.8-day-old pair. No grounded recommendation is possible yet.

## Gaps & Confidence

- **No independent confirmation of team, docs, or launch claims beyond on-chain flags** (confidence: 90%) — next: Search for any socials, website, or prior mentions of FlapTaxTokenV3 or the exact contract address

## Market & Liquidity
- Symbol/Name: BTW / BTW
- Price: $0.000003230
- Liquidity: $7148.57
- 24h Volume: $194.88
- 24h Change: -4.45%
- DEX: flapsh

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: ``
- sell_tax: ``
- is_mintable: `0`
- is_proxy: `1`
- holder_count: `5`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock
- Top 5 non-LP/burn holders control 100.0% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 45 bytes

## Contract Verification
- Verified: True
- Name: FlapTaxTokenV3 · Compiler: v0.8.24+commit.e11b9ed9
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, emergencyWithdraw, renounceOwnership, transferOwnership, withdrawDividends, withdrawDividendsFor, withdrawableDividends, withdrawnDividends
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
- Block explorer: https://bscscan.com/address/0x2FcB6f3d1Be8F16002B101ee3182eD9668797777
- Market pair: https://dexscreener.com/bsc/0x372c1cc0aaf312671adfb2d705523aba2e200332
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*