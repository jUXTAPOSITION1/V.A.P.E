<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — RELICS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![PROCEED](https://img.shields.io/badge/VERDICT-PROCEED-10B981?style=flat-square) ![80/100](https://img.shields.io/badge/SAFETY_SCORE-80%2F100-6EBB5C?style=flat-square)

- **Target:** `0x1fEb4AeC0d592eC55b137f12cBC57229ee899602`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-08-04T05:21:58Z
- **Verdict:** PROCEED (80/100)

---

## Expert Assessment
Evidence for RELICS remains thin, with no declared website, social links, or team provenance available in the scan. One concrete fact present is 100% liquidity lock paired with an unrenounced owner at 0x7fd1a796d7c6f73c95f5e3ea9590c8d17cdaf762 and absolute liquidity of only $12,190.

The data supports basic technical hygiene: verified source code of 13.5 kB, zero honeypot or tax flags, zero mint capability, and 396 holders after 907 days of continuous trading with independent pricing history.

Primary residual risks are the absent narrative or social surface, the low absolute liquidity, and the retained owner privileges that could still alter contract behavior despite the lock.

Technical-safety confidence sits at roughly 70% given the clean on-chain flags; overall investment-thesis confidence is below 30% because no external usage or holder-distribution signals exist to corroborate staying power.

No grounded recommendation is possible yet.

## Gaps & Confidence

- **no social or web footprint declared** (confidence: 90%) — next: search X/Telegram/Discord mentions for RELICS token by contract address

## Scoring Dashboard
**Overall: 80/100 — PROCEED** ![80/100](https://img.shields.io/badge/overall-80%2F100-6EBB5C?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![90/100](https://img.shields.io/badge/security-90%2F100-3FBA6E?style=flat-square) | Owner not renounced (0x7fd1a796d7c6f73c95f5e3ea9590c8d17cdaf762) — can still act on the contract. |
| Liquidity Health & Lock Quality | 20% | ![90/100](https://img.shields.io/badge/liquidity-90%2F100-3FBA6E?style=flat-square) | Low liquidity $12,190; (+) 100% of liquidity is locked — reduced rug-pull risk. |
| Holder Distribution & Concentration | 15% | ![100/100](https://img.shields.io/badge/holders-100%2F100-10B981?style=flat-square) | No signal either way this cycle. |
| Transparency & Provenance | 15% | ![100/100](https://img.shields.io/badge/transparency-100%2F100-10B981?style=flat-square) | (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![25/100](https://img.shields.io/badge/narrative-25%2F100-FB9854?style=flat-square) | no coherent project narrative could be established this cycle. |
| Longevity & Clean Track Record | 10% | ![100/100](https://img.shields.io/badge/longevity-100%2F100-10B981?style=flat-square) | (+) DefiLlama has priced this token for 907+ days — independent longevity corroboration. |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x7fd1a796d7c6f73c95f5e3ea9590c8d17cdaf762) — can still act on the contract
- [-10] Low liquidity $12,190

## Positive Signals (real legitimacy evidence found)
- 100% of liquidity is locked — reduced rug-pull risk
- Trading 907+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 907+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x7fd1a796d7c6f73c95f5e3ea9590c8d17cdaf762) — can still act on the contract
**Holder Distribution & Liquidity** — 1 flag(s), 1 positive signal(s)
  - [-10] Low liquidity $12,190
  - (positive) 100% of liquidity is locked — reduced rug-pull risk
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 907+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 907+ days — independent longevity corroboration

## Market & Liquidity
- Symbol/Name: RELICS / Alien Relics
- Price: $8.90
- Liquidity: $12189.98
- 24h Volume: $517.34
- 24h Change: 8.4%
- DEX: uniswap
- Price-change trend (h6/h24): `▁▁` (h6: +8.4%, h24: +8.4%)
- Volume trend (m5/h1/h6/h24): `▁▁██` (m5: $0, h1: $0, h6: $517, h24: $517)

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
- holder_count: `396`
- owner_address: `0x7fd1a796d7c6f73c95f5e3ea9590c8d17cdaf762`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 41.0% of supply
- 100.0% of tracked liquidity-pool tokens are locked (across 2 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 13526 bytes

## Contract Verification
- Verified: True
- Name: Relics · Compiler: v0.8.22+commit.4fc1097e
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, setFeeTo, setFeeToSetter, setWhitelist, transferOwnership

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- First DefiLlama price: 2024-02-08T21:51:37Z (907.3 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0x1fEb4AeC0d592eC55b137f12cBC57229ee899602
- Market pair: https://dexscreener.com/ethereum/0x9b1ea371f1296ff0fe8a88bb55e255f80c0c79f6
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*