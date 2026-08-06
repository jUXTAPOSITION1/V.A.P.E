<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — ZBT

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![18/100](https://img.shields.io/badge/SAFETY_SCORE-18%2F100-FB8D62?style=flat-square)

- **Target:** `0xfAB99fCF605fD8f4593EDb70A43bA56542777777`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-08-06T23:22:30Z
- **Verdict:** REJECT (18/100)

---

## Expert Assessment
The evidence gathered on ZBT (0xfAB99fCF605fD8f4593EDb70A43bA56542777777) suggests a high-risk investment due to significant dilution risk, hidden ownership, and concentrated supply control. Despite having a reasonably distributed holder base of 122,881 and trading for over 294 days without a known incident, the lack of liquidity lock, low liquidity of $12,569, and high concentration of supply among the top 10 non-LP/burn holders pose substantial risks. The project's declared description outlines an ambitious vision for a decentralized cryptographic infrastructure network utilizing zero-knowledge proofs and trusted execution environments, but the absence of a declared web presence and the hidden owner raise concerns about transparency and accountability.

Given the thin evidence on the project's actual implementation and utility, I have low confidence in the overall investment thesis. The technical safety read is more positive, with no honeypot, buy tax, or sell tax detected, and a custom-verified source indicating a non-mass-produced contract. However, the presence of a mintable supply and the owner's ability to act on the contract are significant risks. To improve confidence, concrete signals such as renouncing ownership, locking liquidity, and demonstrating transparent project development and communication would be necessary.

A practical recommendation would be to approach ZBT with extreme caution, considering it only as a small, high-risk speculative position, if at all. The next check should focus on verifying the project's web presence, social media, and community engagement to assess the team's transparency and commitment to the project.

## Gaps & Confidence

- **Verify project web presence and social media** (confidence: 80%) — next: Targeted web search for ZEROBASE official website and social links

## Scoring Dashboard
**Overall: 18/100 — REJECT** ![18/100](https://img.shields.io/badge/overall-18%2F100-FB8D62?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![58/100](https://img.shields.io/badge/security-58%2F100-D5BE33?style=flat-square) | Mintable supply (dilution risk); Hidden owner; Owner not renounced (0xa14f20130e9a0a27d580fd30fd4bbf035a492ab2) — can still act on the contract. |
| Liquidity Health & Lock Quality | 20% | ![75/100](https://img.shields.io/badge/liquidity-75%2F100-86BC52?style=flat-square) | Only 0% of liquidity is locked — the deployer can pull the rest at any time; Low liquidity $12,569. |
| Holder Distribution & Concentration | 15% | ![85/100](https://img.shields.io/badge/holders-85%2F100-56BB65?style=flat-square) | Top 10 non-LP/burn holders control 89% of supply — concentrated, easily manipulated; (+) 122881 holders — reasonably distributed. |
| Transparency & Provenance | 15% | ![100/100](https://img.shields.io/badge/transparency-100%2F100-10B981?style=flat-square) | (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![50/100](https://img.shields.io/badge/narrative-50%2F100-FBBF24?style=flat-square) | a real, address-verified project narrative was established. |
| Longevity & Clean Track Record | 10% | ![100/100](https://img.shields.io/badge/longevity-100%2F100-10B981?style=flat-square) | (+) DefiLlama has priced this token for 293+ days — independent longevity corroboration. |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
## Known Facts
Address-level identity verification for the $ZBT contract is confirmed by an independent market-data lookup. The declared project description states: "ZEROBASE is a decentralized cryptographic infrastructure network that enables verifiable off-chain computation using zero-knowledge proofs (ZKPs) and trusted execution environments (TEEs). It powers products like zkStaking, zkLogin, and ProofYield—bridging institutional DeFi, user privacy, and real-world asset strategies. ZEROBASE delivers programmable, compliance-aligned staking and transparent cryptographic assurance without exposing sensitive data." The declared homepage is https://zerobase.pro/. Real web search results returned nothing relevant this cycle.

## Findings
Evidence is limited to the declared description above; no independent sources, traction metrics, integrations, history, team names, or community signals were surfaced. The project is described as providing ZKP- and TEE-based verifiable off-chain computation for the listed products, but no realized user numbers, volume, or adoption details are available from this round. No relaunch, rebrand, incident, or leadership changes are documented here. No named team or social signals appear in the supplied data.

A concrete next check is to visit the declared homepage directly and extract any team, roadmap, or on-chain activity sections for verifiable details on execution or traction, given the absence of external search results.

Sources: https://zerobase.pro/

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-20] Hidden owner
- [-10] Owner not renounced (0xa14f20130e9a0a27d580fd30fd4bbf035a492ab2) — can still act on the contract
- [-15] Top 10 non-LP/burn holders control 89% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $12,569

## Positive Signals (real legitimacy evidence found)
- 122881 holders — reasonably distributed
- Trading 294+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 293+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 3 flag(s), 0 positive signal(s)
  - [-12] Mintable supply (dilution risk)
  - [-20] Hidden owner
  - [-10] Owner not renounced (0xa14f20130e9a0a27d580fd30fd4bbf035a492ab2) — can still act on the contract
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 89% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-10] Low liquidity $12,569
  - (positive) 122881 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 294+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 293+ days — independent longevity corroboration

## Market & Liquidity
- Symbol/Name: ZBT / ZEROBASE
- Price: $0.1838
- Liquidity: $12568.67
- 24h Volume: $90553.19
- 24h Change: 43.89%
- DEX: uniswap
- Price-change trend (m5/h1/h6/h24): `▁▁▃█` (m5: +0.4%, h1: +1.1%, h6: +13.1%, h24: +43.9%)
- Volume trend (m5/h1/h6/h24): `▁▁▂█` (m5: $6, h1: $916, h6: $18,562, h24: $90,553)
- Liquidity/Market-cap ratio: 0.0% — thin relative to market cap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Circulating supply: 293,749,996 ZBT
- Total supply: 1,000,000,000
- Max supply: 1,000,000,000
- Market cap: $53,857,245
- Fully diluted valuation: $183,343,814
- FDV/Market-cap ratio: 3.40x — a meaningful share of supply is still non-circulating (dilution risk)
- Homepage: https://zerobase.pro/
- X/Twitter: https://x.com/zerobasezk

> ZEROBASE is a decentralized cryptographic infrastructure network that enables verifiable off-chain computation using zero-knowledge proofs (ZKPs) and trusted execution environments (TEEs). It powers products like zkStaking, zkLogin, and ProofYield—bridging institutional DeFi, user privacy, and real-world asset strategies. ZEROBASE delivers programmable, compliance-aligned staking and transparent cryptographic assurance without exposing sensitive data.

## Token Security
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `1`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `122881`
- owner_address: `0xa14f20130e9a0a27d580fd30fd4bbf035a492ab2`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 88.7% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 7 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 23055 bytes

## Contract Verification
- Verified: True
- Name: ZEROBASE · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, burn, mint, renounceOwnership, setMinter, setWhitelisted, transferOwnership, withdrawFee, withdrawLzTokenFee

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.18347099294193728 · confidence: 0.99 · symbol: ZBT
- First DefiLlama price: 2025-10-17T12:58:25Z (293.4 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://bscscan.com/address/0xfAB99fCF605fD8f4593EDb70A43bA56542777777
- Market pair: https://dexscreener.com/bsc/0xb69b56825fd0e2e95f69e5e0955f621c4da3c2bb
- Market data: https://www.coingecko.com/en/coins/zerobase
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*