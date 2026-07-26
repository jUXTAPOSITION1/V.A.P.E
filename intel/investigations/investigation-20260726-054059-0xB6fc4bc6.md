<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — $PLY

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![20/100](https://img.shields.io/badge/SAFETY_SCORE-20%2F100-FB905E?style=flat-square)

- **Target:** `0xB6fc4bc614BC3275C36D609B7a9E1f5017274aB1`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-26T05:40:59Z
- **Verdict:** REJECT (20/100)

---

## Executive Summary
**Overall: REJECT (20/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 30/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-20] Very few holders (8) — thin, easily manipulated distribution
- [-15] Top 8 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-25] Very low liquidity $8,183 (rug/illiquid)
- [-10] Low liquidity $8,183
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Trading 92+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Holder Distribution & Liquidity** — 4 flag(s), 0 positive signal(s)
  - [-20] Very few holders (8) — thin, easily manipulated distribution
  - [-15] Top 8 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-25] Very low liquidity $8,183 (rug/illiquid)
  - [-10] Low liquidity $8,183
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 1 positive signal(s)
  - (positive) Trading 92+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

The evidence paints $PLY as a minimal, long-dormant memecoin on Base whose on-chain footprint (renounced ownership at the zero address, zero taxes/mint/proxy flags, verified but tiny 44-byte contract named simply "Memecoin") is consistent with a one-off deployment that has not been actively controlled for months. The 92-day trading history without incident and lack of honeypot signals reinforce that it is not an active rug in the classic sense; instead, the picture is of an abandoned or failed experiment whose entire supply sits in eight wallets with essentially no external liquidity or volume to speak of. That concentration plus the $8k liquidity pool creates a coherent but fragile reality: any single holder can move the market dramatically, and the absence of third-party audit or identifiable deployer leaves no counterweight to that risk.

The rule-based score correctly weights the holder and liquidity red flags as dominant, but it may slightly overweight the "no audit" penalty relative to the concrete renouncement evidence; once ownership is provably burned, the practical rug vector shrinks even if the project remains unaudited and anonymous. The low volume and 92-day age are under-weighted as signals that the token has already survived the window when most rugs occur.

Next step: pull the eight holder addresses and the Uniswap pair contract to determine exact LP share versus circulating tokens, then scan the pair's historical mint/burn events for any prior liquidity removal attempts.

## Market & Liquidity (DexScreener)
- Symbol/Name: $PLY / PLAY
- Price: $0.00000008182
- Liquidity: $8182.97
- 24h Volume: $0.2
- 24h Change: None%
- DEX: uniswap

## Project Links (as declared on DexScreener)
- No official website/social links declared on this token's DexScreener listing.

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
- transfer_pausable: `0`
- holder_count: `8`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 8 non-LP/burn holders control 100.0% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 44 bytes

## Contract Verification
- Verified: True
- Name: Memecoin · Compiler: v0.8.27+commit.40a35a09
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _mintAndSetExtraDataUnchecked, _safeMint, _setOwner, burn, burnFrom, crosschainBurn, crosschainMint, mint, renounceOwnership, setFeeCalculator, setFeeDistribution, setFeeExemption, transferOwnership, withdraw, withdrawFees
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- cdp: not due yet (40/51 still owed today — pacing to the growing minimum, not a fixed cadence); vapor: 30m interval not yet up (15m remaining) — skipped this cycle

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://basescan.org/address/0xB6fc4bc614BC3275C36D609B7a9E1f5017274aB1
- DexScreener pair: https://dexscreener.com/base/0x21b4d210327e241d716d4a4024d2b33926a06611478ac98279c5863b92124f0e
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*