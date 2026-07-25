<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — JAKEX

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![65/100](https://img.shields.io/badge/SAFETY_SCORE-65%2F100-B4BD40?style=flat-square)

- **Target:** `0xD60ABFB751dB36514a592963fD71DD50c6CF9Ba9`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-25T18:57:58Z
- **Verdict:** CAUTION (65/100)

---

## Executive Summary
**Overall: CAUTION (65/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 65/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-25] Very low liquidity $1,778 (rug/illiquid)
- [-10] Low liquidity $1,778

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Trading 705+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-25] Very low liquidity $1,778 (rug/illiquid)
  - [-10] Low liquidity $1,778
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 705+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence paints JAKEX as a long-dormant, low-stakes ERC-20 that launched on Uniswap roughly two years ago, reached a modest 419-holder base, then effectively froze. Renounced ownership plus zero-address owner, zero mint capability, zero taxes, and no honeypot flags line up with a one-time fair launch that was never upgraded or backdoored later; the 8 kB verified contract size is consistent with a simple custom token rather than a cloned factory template. The $1.7 k liquidity and $75 daily volume, however, show the project has no ongoing activity or liquidity provision, so the “705+ days without incident” signal mainly reflects abandonment rather than active stewardship.

The rule-based score correctly flags illiquidity as the dominant risk but under-weights how the combination of renouncement, verified custom code, and multi-year clean history removes the classic rug vectors that usually accompany low-liquidity tokens; the 65/100 therefore reads slightly harsher than the on-chain facts alone justify for a holder who already accepted the position years ago.

Next concrete check: pull the verified source from Etherscan and scan for any hidden transfer restrictions, fee switches, or balance-modifying functions that GoPlus’s surface flags would have missed.

## Market & Liquidity (DexScreener)
- Symbol/Name: JAKEX / JakeX
- Price: $0.00001440
- Liquidity: $1777.76
- 24h Volume: $75.59
- 24h Change: -9.66%
- DEX: uniswap

## Project Links (as declared on DexScreener)
- Website: https://www.jakex.win/
- Website: https://www.jakex.win/the-jakepaper
- twitter: https://twitter.com/JakeXOfficial88
- telegram: https://t.me/JakeXOfficial

## Tokenomics (CoinGecko, address-verified)
- Not available this cycle (CoinGecko does not track this exact contract address, or the token isn't listed there yet) — absence noted, not penalized.

## Token Security (GoPlus)
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
- holder_count: `419`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 10 non-LP/burn holders control 47.3% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 8128 bytes

## Contract Verification
- Verified: True
- Name: JakeX · Compiler: v0.8.19+commit.7dd6d404
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, burn, burnFrom, mint, renounceOwnership, setFeeTo, setFeeToSetter, transferOwnership

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
- Block explorer: https://etherscan.io/address/0xD60ABFB751dB36514a592963fD71DD50c6CF9Ba9
- DexScreener pair: https://dexscreener.com/ethereum/0x166bf1ff9001abdc4ca3d7bb4e3e0dc4a10026f6
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*