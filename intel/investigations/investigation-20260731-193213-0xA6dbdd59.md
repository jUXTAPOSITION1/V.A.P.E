<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — ASTEROID

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0xA6dbdd59318e212ad3Eb6Ca002D5De47195cA27c`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-31T19:32:13Z
- **Verdict:** REJECT (0/100)

---

## Executive Summary
**Overall: REJECT (0/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 88/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 60/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: CTM (0x279a9C40151bfe9AFEFf5530c5F32bc6ecea652a) — REJECT 0/100 — likely the same serial campaign
- [-20] Very few holders (2) — thin, easily manipulated distribution
- [-15] Top 2 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Deep liquidity ($5,903,427)
- Trading 97+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 1 positive signal(s)
  - [-12] Mintable supply (dilution risk)
  - (positive) Ownership renounced
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-20] Very few holders (2) — thin, easily manipulated distribution
  - [-15] Top 2 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) Deep liquidity ($5,903,427)
**Transparency & Provenance** — 2 flag(s), 1 positive signal(s)
  - [-30] Same deployer has a prior CAUTION/REJECT verdict on record: CTM (0x279a9C40151bfe9AFEFf5530c5F32bc6ecea652a) — REJECT 0/100 — likely the same serial campaign
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 97+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence paints ASTEROID as a low-activity Uniswap token whose contract name (MintBurnTeamToken) and verified source suggest a custom mint/burn mechanism rather than a generic template. Yet the on-chain reality shows a renounced owner paired with a still-mintable flag, exactly two holders controlling 100 % of supply, and liquidity that has sat untouched for 97+ days with essentially zero volume. That combination is hard to reconcile with any organic project: a legitimate mint/burn design would normally show either broader distribution or at least some usage of the burn function, while the deep liquidity pool appears to function mainly as a static backdrop rather than active market depth. The fact that the same deployer previously launched CTM (also rejected on identical concentration and mintability grounds) strengthens the picture of a serial pattern rather than an isolated experiment.

The rule-based score correctly flags the mintable + two-holder concentration risk, but it may slightly overweight the “0 % liquidity locked” item once ownership is already renounced; the more material gap is the absence of any on-chain history showing whether mint calls have ever been executed or disabled post-renounce. The prior CTM link is under-weighted in the sense that it turns the “no audit/anonymous” default into a repeated-behavior signal rather than a one-off unknown.

Next step: pull the verified source and any past mint/burn transactions on the ASTEROID contract itself (or on CTM) to determine whether the mint function remains callable by anyone after renouncement.

## Market & Liquidity
- Symbol/Name: ASTEROID / Asteroid
- Price: $0.01180
- Liquidity: $5903426.62
- 24h Volume: $0.01
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
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `2`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock
- Top 2 non-LP/burn holders control 100.0% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 5150 bytes

## Contract Verification
- Verified: True
- Name: MintBurnTeamToken · Compiler: v0.6.12+commit.27d51765
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, burn, burnFrom, mint, renounceOwnership, transferOwnership

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
- Block explorer: https://etherscan.io/address/0xA6dbdd59318e212ad3Eb6Ca002D5De47195cA27c
- Market pair: https://dexscreener.com/ethereum/0xab82da12629b887c692c8c4a94832ad5bf578d6a
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*