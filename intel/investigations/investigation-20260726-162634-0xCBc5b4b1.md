<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — DCA

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![70/100](https://img.shields.io/badge/SAFETY_SCORE-70%2F100-9DBD49?style=flat-square)

- **Target:** `0xCBc5b4b1a171fc4f86106e3E36853592AC16aaaa`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-26T16:26:34Z
- **Verdict:** CAUTION (70/100)

---

## Executive Summary
**Overall: CAUTION (70/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 70/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-15] Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- Deep liquidity ($1,024,451)
- Trading 107+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Holder Distribution & Liquidity** — 2 flag(s), 1 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) Deep liquidity ($1,024,451)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 107+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence paints DCA as a low-distribution token on PancakeSwap that has sustained $1M+ liquidity and steady (if modest) volume for over three months, yet the ownership and control picture is sharply at odds with that surface stability. The 85% concentration in the top ten non-LP wallets, paired with literally zero liquidity locked, means the same small set of addresses that already dominate supply can also drain the entire pool at any moment; the 5% sell tax does nothing to blunt that risk because it is a protocol fee, not a lock. The contract itself is verified and non-proxy with a modest 7.9 kB footprint, but its on-chain name (ERC20TokenX) is the generic placeholder typical of quick-deploy templates rather than a bespoke DCA-protocol implementation, creating a quiet mismatch with the “DCA protocol” branding shown in the market data. No mint function and no honeypot flag are genuine positives, yet they are outweighed by the fact that 230 total holders still leaves the token effectively controlled by a handful of wallets after 107 days of trading.

The rule-based score correctly weights the two largest red flags but under-weights the contract-name discrepancy; that single on-chain detail, when read against the extreme concentration, suggests the project may never have intended broad distribution and is operating more like a controlled vehicle than a public protocol.

Next step: pull the top-ten holder addresses and cross-reference their first-interaction timestamps and any common funding sources against the deployer wallet to test whether the concentration is organic or coordinated.

## Market & Liquidity
- Symbol/Name: DCA / DCA protocol
- Price: $53.66
- Liquidity: $1024451.33
- 24h Volume: $64135.1
- 24h Change: -0.05%
- DEX: pancakeswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- buy_tax: `0`
- sell_tax: `0.05`
- cannot_sell_all: `0`
- holder_count: `230`
- owner_address: ``

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 85.0% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 3 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 7945 bytes

## Contract Verification
- Verified: True
- Name: ERC20TokenX · Compiler: v0.7.5+commit.eb77ed08
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _burnFrom, _mint, burn, burnFrom, mint, totalBurn
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- No correlation to recent exploit techniques.

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
- Block explorer: https://bscscan.com/address/0xCBc5b4b1a171fc4f86106e3E36853592AC16aaaa
- Market pair: https://dexscreener.com/bsc/0xe4ff7b71e3987748671c70fdc11d56af697ec4d3
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*