<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — gCOTI

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![42/100](https://img.shields.io/badge/SAFETY_SCORE-42%2F100-FBB334?style=flat-square)

- **Target:** `0xAf2CA40d3fc4459436D11B94d21FA4b8A89fB51d`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-28T18:13:24Z
- **Verdict:** REJECT (42/100)

---

## Executive Summary
**Overall: REJECT (42/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 92/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 91% of supply — concentrated, easily manipulated
- [-25] Very low liquidity $9,476 (rug/illiquid)
- [-10] Low liquidity $9,476

## Positive Signals (real legitimacy evidence found)
- 624 holders — reasonably distributed
- Trading 993+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 988+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 91% of supply — concentrated, easily manipulated
  - [-25] Very low liquidity $9,476 (rug/illiquid)
  - [-10] Low liquidity $9,476
  - (positive) 624 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 993+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 988+ days — independent longevity corroboration

## Expert Assessment
- ⚠️ **DISAGREES with the verdict above**:

The evidence paints gCOTI as a long-running, low-activity governance or wrapped variant tied to the established COTI payments/DeFi project rather than a fresh deployment. Its 988-day pricing history on an independent aggregator, 993+ days of trading with zero recorded incidents, verified custom (non-factory) source, and zero buy/sell taxes line up with a mature token that has simply aged into illiquidity. The ERC1967Proxy structure and owner=None state are consistent with an older upgradeable contract whose admin rights were later renounced or never set, not an active control vector. The 91 % top-10 concentration and $9.5 k liquidity, while objectively risky for manipulation or exit, sit alongside 624 total holders and no mint capability, suggesting the large wallets are more likely project treasuries, vesting contracts, or early locked positions than anonymous insiders poised to dump.

The rule-based score overweighted the proxy and concentration flags in isolation while underweighting the cross-signal of multi-year external pricing coverage plus zero-tax, non-mintable status; those longevity markers are not generic and directly contradict the typical rug pattern the score appears calibrated against. A genuine gap remains around whether the top holders are publicly documented COTI entities or opaque wallets, which the on-chain data alone cannot resolve.

Next cycle or human check should pull the top-10 holder addresses and cross-reference them against any known COTI treasury or vesting contracts on Etherscan or the project's own disclosures.

## Market & Liquidity
- Symbol/Name: gCOTI / gCOTI Token
- Price: $0.002574
- Liquidity: $9475.85
- 24h Volume: $3684.38
- 24h Change: -15.94%
- DEX: uniswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Circulating supply: 0 GCOTI
- Total supply: 1,000,000,000
- Max supply: 1,000,000,000
- Market cap: $0
- Fully diluted valuation: $2,511,771
- Homepage: https://coti.io/
- X/Twitter: https://x.com/COTInetwork

> gCOTI is the COTI Governance Token. gCOTI empowers community governance over COTI's Treasury for the first time ever. It is the first token to be issued on top of the MultiDAG 2.0 Mainnet, based on the CMD (COTI MultiDAG) standard. The introduction of gCOTI allows Treasury participants to gain multiple benefits from COTI’s Treasury such as: Governance, APY Booster and participation in liquidation rewards.

## Token Security
- buy_tax: `0`
- sell_tax: `0`
- is_proxy: `1`
- cannot_sell_all: `0`
- holder_count: `624`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 91.1% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 680 bytes

## Contract Verification
- Verified: True
- Name: ERC1967Proxy · Compiler: v0.8.9+commit.e5eed63a
- Proxy: True · Implementation: 0x006a641635e9fbafa41bf08389b8861a342f9fc4
- Notable functions found in verified source (informational, not scored): _setImplementation, _upgradeTo, _upgradeToAndCall, _upgradeToAndCallSecure, renounceOwnership, transferOwnership, upgradeTo, upgradeToAndCall
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.00248150968109758 · confidence: 0.99 · symbol: gCOTI
- First DefiLlama price: 2023-11-13T09:59:43Z (988.3 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0xAf2CA40d3fc4459436D11B94d21FA4b8A89fB51d
- Market pair: https://dexscreener.com/ethereum/0x7335e5e5e6ffb7f85d959b359e2adaf7c86d2ac4
- Market data: https://www.coingecko.com/en/coins/coti-governance-token
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*