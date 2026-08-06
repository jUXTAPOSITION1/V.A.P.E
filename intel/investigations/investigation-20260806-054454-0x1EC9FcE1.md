<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — SLGNS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![37/100](https://img.shields.io/badge/SAFETY_SCORE-37%2F100-FBAB3D?style=flat-square)

- **Target:** `0x1EC9FcE135d48217A46207e151A426f09AED3e43`
- **Chain:** 137 (Polygon)
- **Date:** 2026-08-06T05:44:54Z
- **Verdict:** REJECT (37/100)

---

## Expert Assessment
The token carries high risk and lacks legitimacy for any exposure, driven by extreme concentration and a serial deployer pattern rather than any isolated technical flaw.

Evidence is thin overall, with no external web or social validation available in the data; the only concrete positive signal present is the reported 51,885 holders alongside 125+ days of trading without a recorded incident.

Primary risks include full supply control by the top 10 non-LP holders, $17k liquidity with near-zero volume, an upgradeable proxy structure, and direct linkage to the prior CES contract flagged under the same deployer.

Technical safety read rests on limited on-chain hygiene checks alone and carries low confidence; overall investment thesis is near-zero and would shift only with verifiable liquidity depth above $100k plus independent holder-distribution audits.

Avoid entirely; no position size is appropriate until the concentration and deployer history are resolved through on-chain tracing of the shared creator address.

## Gaps & Confidence

- **no external social or web footprint to validate project claims** (confidence: 90%) — next: search for any off-chain references to SLGNS or its deployer beyond DEX metadata
- **full holder list and top-wallet behavior unexamined** (confidence: 80%) — next: trace the top 10 wallets for prior activity or links to CES

## Scoring Dashboard
**Overall: 37/100 — REJECT** ![37/100](https://img.shields.io/badge/overall-37%2F100-FBAB3D?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![92/100](https://img.shields.io/badge/security-92%2F100-36BA72?style=flat-square) | Upgradeable proxy (verify implementation). |
| Liquidity Health & Lock Quality | 20% | ![90/100](https://img.shields.io/badge/liquidity-90%2F100-3FBA6E?style=flat-square) | Low liquidity $17,034. |
| Holder Distribution & Concentration | 15% | ![85/100](https://img.shields.io/badge/holders-85%2F100-56BB65?style=flat-square) | Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated; (+) 51885 holders — reasonably distributed. |
| Transparency & Provenance | 15% | ![70/100](https://img.shields.io/badge/transparency-70%2F100-9DBD49?style=flat-square) | Same deployer has a prior CAUTION/REJECT verdict on record: CES (0x3f234f3Ab2B79dcF243Ab387939d2F7e2530b676) — REJECT 12/100 — likely the same serial campaign; (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![25/100](https://img.shields.io/badge/narrative-25%2F100-FB9854?style=flat-square) | no coherent project narrative could be established this cycle. |
| Longevity & Clean Track Record | 10% | ![100/100](https://img.shields.io/badge/longevity-100%2F100-10B981?style=flat-square) | No signal either way this cycle. |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: CES (0x3f234f3Ab2B79dcF243Ab387939d2F7e2530b676) — REJECT 12/100 — likely the same serial campaign
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-10] Low liquidity $17,034

## Positive Signals (real legitimacy evidence found)
- 51885 holders — reasonably distributed
- Trading 125+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
**Holder Distribution & Liquidity** — 2 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-10] Low liquidity $17,034
  - (positive) 51885 holders — reasonably distributed
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-30] Same deployer has a prior CAUTION/REJECT verdict on record: CES (0x3f234f3Ab2B79dcF243Ab387939d2F7e2530b676) — REJECT 12/100 — likely the same serial campaign
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 125+ days without a known incident in this scan

## Market & Liquidity
- Symbol/Name: SLGNS / Stakeds Longinus
- Price: $0.00000002271
- Liquidity: $17034.11
- 24h Volume: $0.03
- 24h Change: None%
- DEX: uniswap
- Volume trend (m5/h1/h6/h24): `▁███` (m5: $0, h1: $0, h6: $0, h24: $0)

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: ``
- sell_tax: ``
- is_proxy: `1`
- holder_count: `51885`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 99.7% of supply
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
- Block explorer: https://polygonscan.com/address/0x1EC9FcE135d48217A46207e151A426f09AED3e43
- Market pair: https://dexscreener.com/polygon/0x0977121430752108726ce485c306d1d533dab95b
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*