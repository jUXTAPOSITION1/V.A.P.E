<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — Claude

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![27/100](https://img.shields.io/badge/SAFETY_SCORE-27%2F100-FB9B51?style=flat-square)

- **Target:** `0xcBBD206D1b844fB3A2AaD1bA198686C616e46737`
- **Chain:** 8453 (Base)
- **Date:** 2026-08-06T22:20:11Z
- **Verdict:** REJECT (27/100)

---

## Expert Assessment
The token shows clear high-risk signals on impersonation and control. Evidence establishes a direct name/symbol match to the well-known AI company with zero declared affiliation or web presence, alongside top-10 holders controlling 100 % of supply and zero liquidity locked. Holder count reaches 23 386 and taxes sit at zero, yet these do not offset the structural issues. Liquidity sits at roughly $103 k with zero 24-hour volume reported.

Residual risks center on the upgradeable-proxy flag, the complete absence of any social or project footprint, and the deployer’s ability to remove remaining liquidity at will. No team, provenance, or utility details appear in the data.

Technical-safety read rests on limited on-chain fields only; overall investment thesis carries very low . A re-check would require on-chain holder-distribution snapshots and any newly declared contract or social links.

## Gaps & Confidence

- **no website/social links or project documentation located** (confidence: 90%) — next: search for any off-chain references tied to the exact contract address

## Scoring Dashboard
**Overall: 27/100 — REJECT** ![27/100](https://img.shields.io/badge/overall-27%2F100-FB9B51?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![92/100](https://img.shields.io/badge/security-92%2F100-36BA72?style=flat-square) | Upgradeable proxy (verify implementation). |
| Liquidity Health & Lock Quality | 20% | ![85/100](https://img.shields.io/badge/liquidity-85%2F100-56BB65?style=flat-square) | Only 0% of liquidity is locked — the deployer can pull the rest at any time. |
| Holder Distribution & Concentration | 15% | ![85/100](https://img.shields.io/badge/holders-85%2F100-56BB65?style=flat-square) | Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated; (+) 23386 holders — reasonably distributed. |
| Transparency & Provenance | 15% | ![65/100](https://img.shields.io/badge/transparency-65%2F100-B4BD40?style=flat-square) | Token name/symbol (Claude / Claude) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence; (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![25/100](https://img.shields.io/badge/narrative-25%2F100-FB9854?style=flat-square) | no coherent project narrative could be established this cycle. |
| Longevity & Clean Track Record | 10% | ![100/100](https://img.shields.io/badge/longevity-100%2F100-10B981?style=flat-square) | No signal either way this cycle. |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-35] Token name/symbol (Claude / Claude) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- 23386 holders — reasonably distributed
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-35] Token name/symbol (Claude / Claude) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence
**Holder Distribution & Liquidity** — 2 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 23386 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)

## Market & Liquidity
- Symbol/Name: Claude / Claude
- Price: $0.0001053
- Liquidity: $103214.29
- 24h Volume: $0
- 24h Change: None%
- DEX: uniswap
- Volume trend (m5/h1/h6/h24): `▁▁▁▁` (m5: $0, h1: $0, h6: $0, h24: $0)

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: `0`
- sell_tax: `0`
- is_proxy: `1`
- holder_count: `23386`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 100.0% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 44 bytes

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
- DATA AGENT hired 2 of VAPE's own x402 market-data offerings against this token (real USDC on Base, 2 settled, $0.02 total):
  - **chain_fees** (settled, cdp) — total_fees_24h=1066812.68; total_fees_7d=8051930.629999994; protocols: 20 item(s)
  - **token_intel** (settled, vapor) — no notable fields

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://basescan.org/address/0xcBBD206D1b844fB3A2AaD1bA198686C616e46737
- Market pair: https://dexscreener.com/base/0xb7990b3065988a251400f97da2fa4c3696d0d8830b1ff9487d7bb7ac68b30be5
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*