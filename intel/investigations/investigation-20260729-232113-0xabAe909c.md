<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — XPULS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![75/100](https://img.shields.io/badge/SAFETY_SCORE-75%2F100-86BC52?style=flat-square)

- **Target:** `0xabAe909cd93Bc2ddf90086f9aA6C3f8e154E8228`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-29T23:21:13Z
- **Verdict:** CAUTION (75/100)

---

## Executive Summary
**Overall: CAUTION (75/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 85/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x22ef3a24c1ed3f6dca365bcd36eeafabb8f3eaaa) — can still act on the contract
- [-15] Only 35% of liquidity is locked — the deployer can pull the rest at any time

## Positive Signals (real legitimacy evidence found)
- 6046 holders — reasonably distributed
- Trading 201+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x22ef3a24c1ed3f6dca365bcd36eeafabb8f3eaaa) — can still act on the contract
**Holder Distribution & Liquidity** — 1 flag(s), 1 positive signal(s)
  - [-15] Only 35% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 6046 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 201+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence paints XPULS as a long-running BSC token (201+ days live) that has reached meaningful distribution—over 6,000 holders with no honeypot flags, no mint capability, and only minimal taxes—yet remains under active developer control. The verified custom contract (11 kB, not a clone) and $402 k liquidity pool on PancakeSwap are consistent with a project that survived its early phase and attracted real trading interest ($4.4 M daily volume), but the combination of an unrenounced owner at 0x22ef3a24c1ed3f6dca365bcd36eeafabb8f3eaaa plus only 35 % of liquidity locked creates an unresolved tension: the same wallet that could still modify fees or drain the unlocked portion has not done so in the recorded history, yet nothing in the data proves it cannot or will not. The sharp –87 % 24 h price move against that volume further suggests either a large exit or external shock, neither of which the on-chain snapshot can attribute to the owner or rule out.

The rule-based score correctly weights the two structural risks but under-weights the age-plus-holder distribution signal; 201 days of incident-free operation with thousands of wallets is stronger evidence of restraint than a generic “owner not renounced” flag usually implies. Conversely, it over-weights the liquidity-lock percentage in isolation without context on how much of the unlocked portion is actually tradeable versus already removed.

Next cycle or human check should pull the owner wallet’s full transaction list since deployment and cross-reference any calls to the token contract against the dates of the largest liquidity movements or the recent price collapse.

## Market & Liquidity
- Symbol/Name: XPULS / XPULS
- Price: $0.002665
- Liquidity: $402514.32
- 24h Volume: $4444997.38
- 24h Change: -87.64%
- DEX: pancakeswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- is_honeypot: `0`
- buy_tax: `0.05`
- sell_tax: `0.0501`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `6046`
- owner_address: `0x22ef3a24c1ed3f6dca365bcd36eeafabb8f3eaaa`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 37.9% of supply
- 35.3% of tracked liquidity-pool tokens are locked (across 6 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 11168 bytes

## Contract Verification
- Verified: True
- Name: XPLUSToken · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, emergencyWithdraw, renounceOwnership, transferOwnership

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
- Block explorer: https://bscscan.com/address/0xabAe909cd93Bc2ddf90086f9aA6C3f8e154E8228
- Market pair: https://dexscreener.com/bsc/0xd7501ec4223cf439da3606e038e463eeeaaf1627
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*