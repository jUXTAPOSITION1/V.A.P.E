<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — 币有

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![10/100](https://img.shields.io/badge/SAFETY_SCORE-10%2F100-FB8172?style=flat-square)

- **Target:** `0xeBd6d1E042bD16893a51a3F9E5c495998a4D4444`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-28T08:21:05Z
- **Verdict:** REJECT (10/100)

---

## Executive Summary
**Overall: REJECT (10/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 35/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-15] Top 10 non-LP/burn holders control 98% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $1 (rug/illiquid)
- [-10] Low liquidity $1
- [-15] Pair only 1.8 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 1.8 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 4 flag(s), 0 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 98% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $1 (rug/illiquid)
  - [-10] Low liquidity $1
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

This token deploys as a bare-bones SimpleToken on BSC with verified but minimal custom source (4224 bytes, no proxy, no mint function, zero taxes). The 346-holder count and zero honeypot flags create an initial appearance of distribution, yet the 98 % concentration in the top-10 non-LP wallets directly contradicts that picture: the remaining 336 addresses necessarily hold dust-level balances, leaving effective control with a handful of entities that can move the entire float at will. Liquidity sits at roughly half a dollar on a 1.8-day-old Pancake pair with negligible volume, so the “0 % locked” flag is almost moot—the deployer can simply drain what exists or let it sit inert. The combination points to either an abandoned test deployment or a low-effort launch that never attracted real participants; nothing in the on-chain or market data suggests ongoing development, utility, or community activity.

The rule-based score correctly flags the concentration and age risks but over-weights the unlocked-liquidity penalty relative to the actual dollar value at stake; once liquidity is already sub-$1, the marginal difference between locked and unlocked becomes cosmetic. It under-weights the verified custom source, which at least rules out the most common copy-paste scam templates, though that single positive does not offset the supply-control and liquidity realities.

Next cycle should pull the top-10 holder addresses and trace their funding sources and any common creation timestamps to test whether they represent one controlling party.

## Market & Liquidity
- Symbol/Name: 币有 / 币有
- Price: $0.000001415
- Liquidity: $0.52
- 24h Volume: $0.01
- 24h Change: 4.41%
- DEX: pancakeswap

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
- holder_count: `346`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 97.7% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 2 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 4224 bytes

## Contract Verification
- Verified: True
- Name: SimpleToken · Compiler: v0.8.36+commit.8a079791
- Proxy: False · Implementation: None
- No notable privileged-sounding function names found in verified source.

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
- Block explorer: https://bscscan.com/address/0xeBd6d1E042bD16893a51a3F9E5c495998a4D4444
- Market pair: https://dexscreener.com/bsc/0x5c1628ebe46229d66861f1f553d6335648f1feab
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*