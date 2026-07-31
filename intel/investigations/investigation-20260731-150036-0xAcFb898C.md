<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — NOCHILL

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![PROCEED](https://img.shields.io/badge/VERDICT-PROCEED-10B981?style=flat-square) ![90/100](https://img.shields.io/badge/SAFETY_SCORE-90%2F100-3FBA6E?style=flat-square)

- **Target:** `0xAcFb898Cff266E53278cC0124fC2C7C94C8cB9a5`
- **Chain:** 43114 (Avalanche)
- **Date:** 2026-07-31T15:00:36Z
- **Verdict:** PROCEED (90/100)

---

## Executive Summary
**Overall: PROCEED (90/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 90/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Low liquidity $48,007

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- 44361 holders — reasonably distributed
- 98% of liquidity is locked — reduced rug-pull risk
- Trading 956+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 948+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Holder Distribution & Liquidity** — 1 flag(s), 2 positive signal(s)
  - [-10] Low liquidity $48,007
  - (positive) 44361 holders — reasonably distributed
  - (positive) 98% of liquidity is locked — reduced rug-pull risk
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 956+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 948+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

This token's profile is consistent with a long-running Avalanche meme coin that launched in late 2023 and has since settled into low-activity status. The combination of a verified, non-proxy contract with zero taxes, renounced ownership at the zero address, and 98 % of liquidity locked directly explains the absence of minting or honeypot flags; those on-chain facts also align with the 956-day trading history and DefiLlama pricing record, indicating the project has not undergone the typical post-launch rug or liquidity removal that would have triggered incidents. The 44 k holder count further supports a distributed base rather than a handful of controlled wallets, reinforcing that the contract is functioning as a plain ERC-20 with no evident backdoors.

The rule-based 90 score correctly weights the renounced/locked positives but under-weights the practical impact of the $7.6 k daily volume against $48 k liquidity: that ratio implies wide spreads and potential slippage far beyond the nominal “low liquidity” deduction, especially on Trader Joe where order-book depth is already thin. No contradictory signals appear in the on-chain or market data, but the gap between “reasonably distributed” holders and actual tradable depth is the clearest unexamined risk.

Next step: pull the top-20 holder balances and cross-check their cumulative share against the 44 k total to quantify whether distribution remains broad or has quietly consolidated.

## Market & Liquidity
- Symbol/Name: NOCHILL / AVAX HAS NO CHILL
- Price: $0.0001851
- Liquidity: $48006.58
- 24h Volume: $7653.19
- 24h Change: -12.04%
- DEX: traderjoe
- Liquidity/Market-cap ratio: 16.8% — reasonable depth for its size

## Project Links
- Website: https://nochill.io
- Website: https://linktr.ee/nochillavax
- twitter: https://x.com/nochillavax

## Tokenomics (address-verified)
- Circulating supply: 1,550,000,000 NOCHILL
- Total supply: 1,550,000,000
- Max supply: 1,550,000,000
- Market cap: $286,201
- Fully diluted valuation: $286,201
- FDV/Market-cap ratio: 1.00x — most of supply is already circulating
- Homepage: https://nochill.io
- X/Twitter: https://x.com/nochillavax

> NOCHILL is a cult catalyst token on Avalanche. Born out of The Arena and airdropped to Gladiator badge holders, NOCHILL is one of Avalanche's 5 culture catalyst tokens and no wider community can be found than the one that's formed around this token. The token was launched on December 18, 2023 and airdropped to roughly 300 users all holding the Gladiator badge. NOCHILL sports a diverse community of users - those native to the Avalanche ecosystem and those natives to other EVM ecosystems. NOCHILL can refer to the fact that the community says it like it is without sugar coating the words. NOCHILL

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
- holder_count: `44361`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 30.0% of supply
- 98.1% of tracked liquidity-pool tokens are locked (across 7 LP holder(s))

## On-chain Presence (Avalanche RPC)
- Is contract: True
- Code size: 7491 bytes

## Contract Verification
- Verified: True
- Name: NoChill · Compiler: v0.8.17+commit.8df45f5f
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _canBurn, _canMint, _canSetOwner, _mint, burn, burnFrom, mintTo, renounceOwnership, setOwner
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.0001852558297030574 · confidence: 0.99 · symbol: NOCHILL
- First DefiLlama price: 2023-12-26T15:10:00Z (948.0 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://snowtrace.io/address/0xAcFb898Cff266E53278cC0124fC2C7C94C8cB9a5
- Market pair: https://dexscreener.com/avalanche/0x2d38bde22e044ea59688ca7cdd4f0b5307cc519a
- Market data: https://www.coingecko.com/en/coins/avax-has-no-chill
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*