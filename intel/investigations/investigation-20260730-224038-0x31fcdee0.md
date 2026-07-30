<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — INVEST

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0x31fcdee0aEa658E0F7A3D275fD126f6faf3b6D82`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-30T22:40:38Z
- **Verdict:** REJECT (0/100)

---

## Executive Summary
**Overall: REJECT (0/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 75/100 |
| Holder Distribution & Liquidity | 34/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Low holder count (56)
- [-8] Top 10 non-LP/burn holders control 67% of supply — meaningful concentration
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $8,110 (rug/illiquid)
- [-10] Low liquidity $8,110
- [-10] Violent 24h move +310% (volatility/manipulation)
- [-15] Pair only 0.3 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +310% (volatility/manipulation)
  - [-15] Pair only 0.3 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 5 flag(s), 0 positive signal(s)
  - [-8] Low holder count (56)
  - [-8] Top 10 non-LP/burn holders control 67% of supply — meaningful concentration
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $8,110 (rug/illiquid)
  - [-10] Low liquidity $8,110
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

This token is a brand-new Uniswap pair ("Dog In Vest") that launched less than a day ago with a custom but minimal ERC-20 contract (verified, ~7 kB, no proxy, ownership renounced, zero taxes, non-mintable). The on-chain footprint is consistent with a low-effort meme coin: 56 holders, $8 k liquidity, and a 310 % price spike on modest volume all point to the same pattern—early wallets (top 10 controlling 67 %) still hold the bulk of supply while liquidity remains fully withdrawable by whoever deployed the pair. Nothing in the data suggests an actual product, team, or utility; the "custom verified source" signal only confirms it is not a blatant copy-paste honeypot template, but does not offset the structural risks of an unlocked, tiny pool controlled by a handful of anonymous addresses.

The rule-based score correctly weights the combination of extreme recency, unlocked liquidity, and holder concentration as decisive red flags; it does not appear to overweight volatility, which is the expected outcome of exactly those conditions. The one area it may under-weight is the absence of any on-chain or off-chain footprint beyond the contract itself—no social links, website, or even a token-description hash appear in the gathered data, leaving the project as a pure liquidity event rather than a coordinated launch.

Next concrete step: pull the top-20 holder addresses and their transaction histories to determine whether the concentrated wallets are still accumulating, already distributing, or simply dormant since launch.

## Market & Liquidity
- Symbol/Name: INVEST / Dog In Vest
- Price: $0.00001094
- Liquidity: $8110.5
- 24h Volume: $46173
- 24h Change: 310%
- DEX: uniswap

## Project Links
- twitter: https://x.com/DogInVestETH

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
- holder_count: `56`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 67.4% of supply
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
- Block explorer: https://etherscan.io/address/0x31fcdee0aEa658E0F7A3D275fD126f6faf3b6D82
- Market pair: https://dexscreener.com/ethereum/0x139a552b6590ff4912dc3c31b6c0acc969c642db6c953f14b998afce6f3af621
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*