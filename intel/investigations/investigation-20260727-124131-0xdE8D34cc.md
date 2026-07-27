<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — HRC

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![15/100](https://img.shields.io/badge/SAFETY_SCORE-15%2F100-FB8868?style=flat-square)

- **Target:** `0xdE8D34cc700055aA6Bc8F7614851a051ca14bF33`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-27T12:41:31Z
- **Verdict:** REJECT (15/100)

---

## Executive Summary
**Overall: REJECT (15/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 65/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-25] Owner can change balances (rug surface)
- [-10] Owner not renounced (0x759fe3a464b80e9594dad8ed2d42cb42909190bc) — can still act on the contract
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $339 (rug/illiquid)
- [-10] Low liquidity $339

## Positive Signals (real legitimacy evidence found)
- Top holders control only 4% of supply — broad distribution
- Trading 781+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 2 flag(s), 0 positive signal(s)
  - [-25] Owner can change balances (rug surface)
  - [-10] Owner not renounced (0x759fe3a464b80e9594dad8ed2d42cb42909190bc) — can still act on the contract
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $339 (rug/illiquid)
  - [-10] Low liquidity $339
  - (positive) Top holders control only 4% of supply — broad distribution
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 781+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence paints a picture of an abandoned or near-dead token that has lingered on PancakeSwap for over two years with almost no activity. The contract (verified under the name SDT rather than HRC) carries persistent owner privileges that explicitly allow balance alterations, a capability that has not been renounced despite the long trading history. This directly undercuts the otherwise reassuring signals of 470 holders and top-wallet concentration at only 4 percent: distribution is broad only in appearance, because the owner address (0x759fe3a464b80e9594dad8ed2d42cb42909190bc) retains the technical ability to override it at any moment. Liquidity sits at roughly $339 with negligible volume, and none of it is locked, so the same owner can also drain whatever remains. The 20 kB custom source code and zero mint/proxy flags are real but largely irrelevant once the project has effectively gone dark; they do not offset the live control surface.

The rule-based scoring correctly weights the owner-risk and illiquidity factors heavily; it does not appear to overweight them. The only potential under-weighting is the mismatch between the token symbol (HRC) and the on-chain contract name (SDT), which could indicate an unadvertised rebrand or migration that never completed—something the long incident-free record does not address.

Next step: pull the full transaction history of the owner address to see whether the balance-alteration functions have ever been called and whether the same key controls any other low-liquidity tokens that later went to zero.

## Market & Liquidity
- Symbol/Name: HRC / HRC
- Price: $0.00000002494
- Liquidity: $339.42
- 24h Volume: $9.5
- 24h Change: 0.42%
- DEX: pancakeswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- is_honeypot: `0`
- buy_tax: `0.03`
- sell_tax: `0.0295`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `1`
- hidden_owner: `0`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `470`
- owner_address: `0x759fe3a464b80e9594dad8ed2d42cb42909190bc`

## Holder Distribution & Liquidity Lock
- Top 9 non-LP/burn holders control 4.1% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 4 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 20454 bytes

## Contract Verification
- Verified: True
- Name: SDT · Compiler: v0.8.24+commit.e11b9ed9
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): addWhitelist, burn, isWhitelistContract, mint, setFee, setTaxFreeUser, setWhitelistContract, suggestSetFee

## Threat Correlation
- Owner can alter balances/ownership — matches a real recent incident: AFX Bridge ($24.15M, Private Key Compromised, 2026-07-22, Arbitrum).

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
- Block explorer: https://bscscan.com/address/0xdE8D34cc700055aA6Bc8F7614851a051ca14bF33
- Market pair: https://dexscreener.com/bsc/0x32bdb06f14c48e2128b7fd11d396d15dcfdc4157
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*