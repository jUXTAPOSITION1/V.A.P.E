<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — SOON

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![62/100](https://img.shields.io/badge/SAFETY_SCORE-62%2F100-C3BE3A?style=flat-square)

- **Target:** `0xb9E1Fd5A02D3A33b25a14d661414E6ED6954a721`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-29T16:45:05Z
- **Verdict:** CAUTION (62/100)

---

## Executive Summary
**Overall: CAUTION (62/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 92/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 70/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 92% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- 10949 holders — reasonably distributed
- Deep liquidity ($511,499)
- Trading 433+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 432+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
**Holder Distribution & Liquidity** — 2 flag(s), 2 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 92% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 10949 holders — reasonably distributed
  - (positive) Deep liquidity ($511,499)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 433+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 432+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

The evidence paints SOON as a long-running BSC token (first priced on DefiLlama in May 2023) that has sustained real trading activity on PancakeSwap for over 432 days, with current liquidity above $500k and daily volume in the millions. The combination of 10,949 holders, zero buy/sell taxes, and a non-factory verified proxy contract suggests an intentional, custom deployment rather than a disposable meme launch. However, the same data set shows the top-10 wallets still control 92% of supply outside LP/burn addresses, liquidity remains fully unlocked, and the contract is explicitly an upgradeable TransparentUpgradeableProxy. These three facts together indicate that whatever team or entity originally deployed the token retains structural levers to alter supply, fees, or drain liquidity at any time, even after more than a year of operation. The longevity and volume are therefore not fully reassuring; they can coexist with a project that simply never chose to renounce control.

The rule-based score correctly flags the proxy and concentration risks but appears to underweight the unlocked-liquidity penalty relative to the observed market depth. A $511k pool that has survived 432 days without incident implies either genuine restraint by the deployer or that the economic cost of pulling it now would be high; the raw “0% locked” flag treats both scenarios identically. Conversely, the 10,949-holder count is given positive weight, yet it does not offset the 92% top-10 concentration once the proxy upgrade path is considered—large holders could still coordinate or be pressured if the logic contract changes.

Next step: pull the current implementation address behind the proxy and inspect its ownership/upgrade functions plus any recent calls to those functions.

## Market & Liquidity
- Symbol/Name: SOON / SOON Token
- Price: $0.2074
- Liquidity: $511499.33
- 24h Volume: $4912848.72
- 24h Change: -25.56%
- DEX: pancakeswap
- Liquidity/Market-cap ratio: 0.7% — thin relative to market cap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Circulating supply: 339,791,742 SOON
- Total supply: 1,004,877,312
- Market cap: $70,417,795
- Fully diluted valuation: $208,248,864
- FDV/Market-cap ratio: 2.96x — a meaningful share of supply is still non-circulating (dilution risk)
- Homepage: https://soo.network/
- X/Twitter: https://x.com/soon_svm

> SOON stack is the most efficient rollup stack delivering high performance to every L1, powered by SVM. SOON team pioneered Decoupled SVM, which allows SVM rollups to be spun up across different L1s with native fraud proofs, reduced DA cost and horizontal scaling capacity. SOON's SAS (Super Adoption Stack) creates a native interop among all SOON chains as well as with SOL &amp; TON. We launched the first SOL x TON bridge with native TG mini app. Devs can access users without leaving the SOON ecosystem, making it a more effective user acquisition tool at a fraction of the cost of TVL game.

## Token Security
- buy_tax: `0`
- sell_tax: `0`
- is_proxy: `1`
- cannot_sell_all: `0`
- holder_count: `10949`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 92.4% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 10 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 1159 bytes

## Contract Verification
- Verified: True
- Name: TransparentUpgradeableProxy · Compiler: v0.8.22+commit.4fc1097e
- Proxy: True · Implementation: 0x87d133d4ccb68a5240430c10a4d19a29dede7fe6
- Notable functions found in verified source (informational, not scored): _dispatchUpgradeToAndCall, _setImplementation, _transferOwnership, renounceOwnership, transferOwnership, upgradeToAndCall
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.20741510135242286 · confidence: 0.99 · symbol: SOON
- First DefiLlama price: 2025-05-23T12:59:02Z (432.2 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://bscscan.com/address/0xb9E1Fd5A02D3A33b25a14d661414E6ED6954a721
- Market pair: https://dexscreener.com/bsc/0x0b2eb4332a15e5165477aad2c79721925920a383
- Market data: https://www.coingecko.com/en/coins/soon-2
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*