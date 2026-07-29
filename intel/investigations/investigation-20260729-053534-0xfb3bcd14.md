<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — ZAMA

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![40/100](https://img.shields.io/badge/SAFETY_SCORE-40%2F100-FBAF37?style=flat-square)

- **Target:** `0xfb3bcd142ab83505d57c446e1718D8429424DE3b`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-29T05:35:34Z
- **Verdict:** REJECT (40/100)

---

## Executive Summary
**Overall: REJECT (40/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 50/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-20] Very few holders (2) — thin, easily manipulated distribution
- [-15] Top 2 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- Deep liquidity ($119,260,116)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Holder Distribution & Liquidity** — 3 flag(s), 1 positive signal(s)
  - [-20] Very few holders (2) — thin, easily manipulated distribution
  - [-15] Top 2 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) Deep liquidity ($119,260,116)
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

This token shows a stark mismatch between its reported $119M liquidity pool on Uniswap and its actual on-chain footprint: only two wallets hold the entire supply, trading volume has collapsed to a single cent in the last 24 hours, and zero liquidity is locked despite ownership being renounced to the zero address. The verified custom contract (no proxy, no mint, zero taxes) creates an appearance of legitimacy, but that is undermined by the fact that the same two holders necessarily control both the token distribution and any LP tokens—renouncement prevents the original deployer from calling privileged functions, yet does nothing to prevent those holders from removing liquidity at will. The result is a project that looks more like a dormant or deliberately inert vehicle than a functioning market; the deep liquidity figure is technically present but economically meaningless given the absence of counterparties or activity.

The rule-based score correctly flags concentration and the unlocked pool as primary risks, but underweights the liquidity-versus-volume disconnect. That gap is not explained by normal illiquidity; it is a concrete signal that the pool may be one-sided or inaccessible in practice, amplifying manipulation potential beyond what holder count alone captures.

Next step: pull the exact addresses of the two holders and check whether either wallet currently owns the Uniswap V2/V3 LP NFT or tokens for this pair, then trace any prior transfers from the deployer.

## Market & Liquidity
- Symbol/Name: ZAMA / Zama
- Price: $0.02162
- Liquidity: $119260115.89
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
- is_mintable: `0`
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
- Code size: 5476 bytes

## Contract Verification
- Verified: True
- Name: token · Compiler: v0.8.20+commit.a1b79de6
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, renounceOwnership, transferOwnership

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
- Block explorer: https://etherscan.io/address/0xfb3bcd142ab83505d57c446e1718D8429424DE3b
- Market pair: https://dexscreener.com/ethereum/0x9f63c93960ffff49b9f599219ce99aadfea1faa9
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*