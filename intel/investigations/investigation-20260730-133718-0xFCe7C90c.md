<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — GOD

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![40/100](https://img.shields.io/badge/SAFETY_SCORE-40%2F100-FBAF37?style=flat-square)

- **Target:** `0xFCe7C90cf19b847690A7B7267e8817B8cC9822e6`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-30T13:37:18Z
- **Verdict:** REJECT (40/100)

---

## Executive Summary
**Overall: REJECT (40/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 75/100 |
| Holder Distribution & Liquidity | 75/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $25,349
- [-10] Violent 24h move +1623% (volatility/manipulation)
- [-15] Pair only 2.6 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +1623% (volatility/manipulation)
  - [-15] Pair only 2.6 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-10] Low liquidity $25,349
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints this as a bare-bones anonymous meme launch on Uniswap: a freshly deployed, verified custom ERC-20 (UERC20, 7 kB) with ownership already renounced, taxes and minting disabled, and no proxy. It is paired against “Vitalik” (likely a direct ETH or Vitalik-related liquidity route) and has attracted 249 holders plus $315 k in 24-hour volume despite only $25 k locked liquidity. The 2.6-day pair age plus the 1 623 % price spike are consistent with a single coordinated liquidity injection and subsequent retail chase rather than organic growth or any underlying utility; nothing in the on-chain data or market snapshot indicates a team, roadmap, or product that would justify the move.

The rule-based score correctly flags the unlocked liquidity and extreme youth as primary rug vectors, but it under-weights the combination of renounced ownership + zero mint/tax flags, which materially reduces the most common post-launch attack surfaces even if liquidity itself remains pullable. Conversely, it over-weights the lack of a third-party audit, which is largely redundant once the contract is verified and the owner address is already None.

Next step: pull the holder-distribution snapshot (top-20 wallets and any exchange or deployer-linked addresses) to quantify concentration risk that the current 249-holder count alone does not reveal.

## Market & Liquidity
- Symbol/Name: GOD / Vitalik
- Price: $0.00007492
- Liquidity: $25349.22
- 24h Volume: $315693.87
- 24h Change: 1623%
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
- transfer_pausable: `0`
- holder_count: `249`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 39.2% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 7154 bytes

## Contract Verification
- Verified: True
- Name: UERC20 · Compiler: v0.8.28+commit.7893614a
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
- Block explorer: https://etherscan.io/address/0xFCe7C90cf19b847690A7B7267e8817B8cC9822e6
- Market pair: https://dexscreener.com/ethereum/0x8be3f3c07ae261db04b805ac53a67f94e15078e36adc88a931ce90aaa34912cf
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*