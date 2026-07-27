<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — MegaDoge

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![50/100](https://img.shields.io/badge/SAFETY_SCORE-50%2F100-FBBF24?style=flat-square)

- **Target:** `0xCBf4AB00b6Aa19B4d5D29C7c3508B393a1C01Fe3`
- **Chain:** 137 (Polygon)
- **Date:** 2026-07-27T02:57:34Z
- **Verdict:** CAUTION (50/100)

---

## Executive Summary
**Overall: CAUTION (50/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-15] Only 5% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $6,067 (rug/illiquid)
- [-10] Low liquidity $6,067

## Positive Signals (real legitimacy evidence found)
- 992126 holders — reasonably distributed
- Trading 182+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-15] Only 5% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $6,067 (rug/illiquid)
  - [-10] Low liquidity $6,067
  - (positive) 992126 holders — reasonably distributed
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 182+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence sketches an abandoned legacy meme token: nearly a million holders accumulated over 182+ days of trading, with ownership fully renounced (owner=None), zero mint capability, zero taxes, and a non-factory verified contract. That combination plus the absence of honeypot flags creates a coherent picture of a once-distributed community token that simply died rather than an active scam. The glaring mismatch is the $6k liquidity pool on Uniswap (Polygon) where only 5% is locked—the remaining 95% can still be removed by whoever holds the LP tokens, and the $13 daily volume shows no one is actually using the token anymore. The holder count is reassuring on distribution but does not offset the fact that the asset is functionally illiquid and the unlock risk remains live.

The rule-based score correctly flags the liquidity and lock issues but slightly overweights them relative to the renounced contract and long clean history; those two factors make a sudden full drain less likely than with a fresh low-liq token that still has an active owner.

Next cycle or a human should pull the actual LP-token balance and any lock contracts tied to the Uniswap pair to confirm exactly who controls the unlocked portion and whether any unlock schedule exists.

## Market & Liquidity
- Symbol/Name: MegaDoge / MegaDoge.Org
- Price: $0.00006036
- Liquidity: $6067.41
- 24h Volume: $13.85
- 24h Change: 1.11%
- DEX: uniswap

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
- holder_count: `992126`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 24.0% of supply
- 5.3% of tracked liquidity-pool tokens are locked (across 10 LP holder(s))

## On-chain Presence (Polygon RPC)
- Is contract: unavailable this cycle (HTTP Error 401: Unauthorized)

## Contract Verification
- Verified: True
- Name: ERC20 · Compiler: v0.8.7+commit.e28d00a7
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint

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
- Block explorer: https://polygonscan.com/address/0xCBf4AB00b6Aa19B4d5D29C7c3508B393a1C01Fe3
- Market pair: https://dexscreener.com/polygon/0x02994255a5bb3714e96a4e71abd2d3468f6b0ba1
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*