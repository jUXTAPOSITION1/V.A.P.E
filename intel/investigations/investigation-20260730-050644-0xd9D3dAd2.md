<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — 喵喵币

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![25/100](https://img.shields.io/badge/SAFETY_SCORE-25%2F100-FB9854?style=flat-square)

- **Target:** `0xd9D3dAd2EfeD7eE99F1363FAC549f5E476F19A5a`
- **Chain:** 56 (BNB Chain)
- **Date:** 2026-07-30T05:06:44Z
- **Verdict:** REJECT (25/100)

---

## Executive Summary
**Overall: REJECT (25/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 75/100 |
| Holder Distribution & Liquidity | 70/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x005ccee4f3024d7343e4c244eea3873783c84f04) — can still act on the contract
- [-15] Top 10 non-LP/burn holders control 95% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Violent 24h move +382% (volatility/manipulation)
- [-15] Pair only 1.1 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- 18429 holders — reasonably distributed
- Deep liquidity ($1,979,447)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x005ccee4f3024d7343e4c244eea3873783c84f04) — can still act on the contract
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +382% (volatility/manipulation)
  - [-15] Pair only 1.1 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 2 flag(s), 2 positive signal(s)
  - [-15] Top 10 non-LP/burn holders control 95% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 18429 holders — reasonably distributed
  - (positive) Deep liquidity ($1,979,447)
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

This appears to be a Chinese-language cat-themed meme token launched on PancakeSwap roughly 24 hours before the snapshot. The combination of a verified but non-factory contract, non-zero taxes, and sudden 382% price surge points to a deliberate launch engineered for rapid retail accumulation rather than an organic community project. The 18k-holder count looks broad on the surface, yet the 95% top-10 concentration (outside LP/burn) implies the bulk of those wallets are dust positions; the same wallets that control supply can therefore dictate both price action and any future sell pressure. Liquidity depth near $2 M is real, but the complete absence of locks paired with an unrenounced owner at 0x005ccee4f3024d7343e4c244eea3873783c84f04 creates a direct, low-friction exit path that the volatility data already hints has been tested.

The rule-based score correctly weights the unlocked liquidity and holder concentration as primary red flags; these two items together outweigh the “many holders” and “deep liquidity” positives because the distribution data shows the liquidity is effectively hostage to the same small set of addresses. What the score slightly under-weights is the custom verified source code: while not proof of legitimacy, it rules out the cheapest copy-paste rugs and suggests the deployer invested at least minimal effort in presentation, which can extend the window before a pull.

Next cycle or a human reviewer should pull the transaction history of the owner address itself to see whether it has previously deployed or exited similar tokens and whether any recent approvals or liquidity removals have occurred.

## Market & Liquidity
- Symbol/Name: 喵喵币 / 喵喵币
- Price: $0.00005185
- Liquidity: $1979447.43
- 24h Volume: $1760351.76
- 24h Change: 382%
- DEX: pancakeswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- is_honeypot: `0`
- buy_tax: `0.0697`
- sell_tax: `0.1`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `18429`
- owner_address: `0x005ccee4f3024d7343e4c244eea3873783c84f04`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 94.6% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 2 LP holder(s))

## On-chain Presence (BNB Chain RPC)
- Is contract: True
- Code size: 10197 bytes

## Contract Verification
- Verified: True
- Name: MMToken · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _setImplementation, _transferOwnership, batchSetFeeExempt, batchSetWhitelistTier, renounceOwnership, setFeeExempt, setFeeRecipients, transferOwnership

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
- Block explorer: https://bscscan.com/address/0xd9D3dAd2EfeD7eE99F1363FAC549f5E476F19A5a
- Market pair: https://dexscreener.com/bsc/0x6f6a6eabbf07af11ea58ba523cf74618f45fd190
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*