<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — SPYon

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![52/100](https://img.shields.io/badge/SAFETY_SCORE-52%2F100-F2BF28?style=flat-square)

- **Target:** `0xFeDC5f4a6c38211c1338aa411018DFAf26612c08`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-30T22:10:03Z
- **Verdict:** CAUTION (52/100)

---

## Executive Summary
**Overall: CAUTION (52/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 92/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 60/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 73% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $25,509

## Positive Signals (real legitimacy evidence found)
- 1704 holders — reasonably distributed
- Trading 316+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 332+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-8] Upgradeable proxy (verify implementation)
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 73% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-10] Low liquidity $25,509
  - (positive) 1704 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 316+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 332+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

This token is a BeaconProxy implementation of an Ondo-issued tokenized SPDR S&P 500 ETF share (SPYon), deployed roughly 332 days ago and continuously priced on DefiLlama since then. The combination of verified custom source, zero taxes, 1,704 holders, and sustained Uniswap volume without recorded exploits points to a real, operational RWA wrapper rather than a quick-exit meme. The 73 % top-10 concentration and fully unlocked liquidity are not contradictory with that picture; they are consistent with an institutional RWA structure in which large custodians or the issuer itself retain the bulk of supply while a thin public market exists on Uniswap. The low $25 k liquidity pool is the clearest operational constraint: it explains both the modest 24 h volume and the structural risk that any single large holder (or the proxy admin) could materially move price or drain the pool.

The rule-based score overweighted the generic “upgradeable proxy” flag while under-weighting the 300-plus-day DefiLlama pricing history and the explicit “Ondo Tokenized” branding; both are stronger signals of continuity than a static ownership check. Conversely, it correctly flagged the unlocked liquidity and holder concentration as live risks that the longevity data does not mitigate.

Next step: retrieve the current beacon address and implementation contract, then inspect the implementation’s admin functions (especially any mint, upgrade, or fee-setter roles) to determine whether control still rests with Ondo’s known multisig or has been renounced.

## Market & Liquidity
- Symbol/Name: SPYon / SPDR S&P 500 ETF (Ondo Tokenized)
- Price: $741.74
- Liquidity: $25509.38
- 24h Volume: $173286.06
- 24h Change: -1.21%
- DEX: uniswap
- Liquidity/Market-cap ratio: 0.1% — thin relative to market cap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Circulating supply: 57,223 SPYON
- Total supply: 57,223
- Market cap: $42,756,402
- Fully diluted valuation: $42,756,402
- FDV/Market-cap ratio: 1.00x — most of supply is already circulating
- Homepage: https://app.ondo.finance/assets/spyon
- X/Twitter: https://x.com/ondofinance

> SPYon is the Ondo Tokenized version of the SPDR S&amp;P 500 ETF, giving tokenholders economic exposure similar to holding SPY and reinvesting any dividends. Ondo tokenized stocks enable non-US retail and institutional users around the world to instantly mint and redeem tokenized U.S. stocks and ETFs, 24 hours a day, five days a week with full access to traditional exchange liquidity. Additional restrictions apply. Learn more at ondo.finance/global-markets.

## Token Security
- buy_tax: `0`
- sell_tax: `0`
- is_proxy: `1`
- cannot_sell_all: `0`
- holder_count: `1704`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 73.2% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 10 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 824 bytes

## Contract Verification
- Verified: True
- Name: BeaconProxy · Compiler: v0.8.16+commit.07a7930e
- Proxy: True · Implementation: 0xebbcb2cee51c2fee4062c9c1270dcb98b0b22250
- Notable functions found in verified source (informational, not scored): _setImplementation, _upgradeTo, _upgradeToAndCall, _upgradeToAndCallUUPS
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $747.8681642222007 · confidence: 1 · symbol: SPYon
- First DefiLlama price: 2025-09-02T00:00:00Z (331.9 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0xFeDC5f4a6c38211c1338aa411018DFAf26612c08
- Market pair: https://dexscreener.com/ethereum/0xd192a9f86a0cff3c814251d90328d19ecd05826b
- Market data: https://www.coingecko.com/en/coins/spdr-s-p-500-etf-ondo-tokenized-etf
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*