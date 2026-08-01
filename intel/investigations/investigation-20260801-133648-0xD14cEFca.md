<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — OFC

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![20/100](https://img.shields.io/badge/SAFETY_SCORE-20%2F100-FB905E?style=flat-square)

- **Target:** `0xD14cEFcaF95BBE72F363CBDFF1ca18DAe1D3C858`
- **Chain:** 8453 (Base)
- **Date:** 2026-08-01T13:36:48Z
- **Verdict:** REJECT (20/100)

---

## Executive Summary
**Overall: REJECT (20/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 78/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 42/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-10] Owner not renounced (0x936323159e83c8e92b6dda95bc134902749cf213) — can still act on the contract
- [-8] Top 10 non-LP/burn holders control 65% of supply — meaningful concentration
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $2 (rug/illiquid)
- [-10] Low liquidity $2

## Positive Signals (real legitimacy evidence found)
- 133085 holders — reasonably distributed
- Trading 114+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 2 flag(s), 0 positive signal(s)
  - [-12] Mintable supply (dilution risk)
  - [-10] Owner not renounced (0x936323159e83c8e92b6dda95bc134902749cf213) — can still act on the contract
**Holder Distribution & Liquidity** — 4 flag(s), 1 positive signal(s)
  - [-8] Top 10 non-LP/burn holders control 65% of supply — meaningful concentration
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $2 (rug/illiquid)
  - [-10] Low liquidity $2
  - (positive) 133085 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 114+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence gathered this cycle is thin, consisting only of aggregated on-chain metrics and automated risk flags with no deeper page content or external sources to cross-check. One concrete fact available is the reported liquidity of $1.74 paired with 133085 holders. No grounded recommendation for a next check is possible yet.

## Gaps & Confidence

_No material gaps flagged this round._

## Market & Liquidity
- Symbol/Name: OFC / OFC
- Price: $0.000002932
- Liquidity: $1.74
- 24h Volume: $0
- 24h Change: None%
- DEX: uniswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `133085`
- owner_address: `0x936323159e83c8e92b6dda95bc134902749cf213`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 65.3% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 15718 bytes

## Contract Verification
- Verified: True
- Name: ERC20FixedSupply · Compiler: v0.8.24+commit.e11b9ed9
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): Whitelist, _burn, _mint, _transferOwnership, renounceOwnership, setFeeTo, setFeeToSetter, transferOwnership

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 2 of VAPE's own $0.01 x402 market-data offerings against this token (real USDC on Base, 2 settled, $0.02 total):
  - **bridges** (settled, cdp) — count=6; data_source=bridge-exploit incident feed (bridge volume list unavailable this cycle); recent_bridge_incidents: 6 item(s); note=Live bridge-volume ranking unavailable this cycle; showing recent bridge-category exploit incidents instead as the nearer-term threat signal.
  - **dex_volumes** (settled, vapor) — total_vol_24h=1061771661.75; dexs: 20 item(s)

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://basescan.org/address/0xD14cEFcaF95BBE72F363CBDFF1ca18DAe1D3C858
- Market pair: https://dexscreener.com/base/0x88cc658ffdd23da13f696d8a7bc96d9fc73156ce485e691a9840b1eb44ebd7f1
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*