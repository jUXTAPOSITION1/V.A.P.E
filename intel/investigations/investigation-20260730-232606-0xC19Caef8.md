<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — SPX

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0xC19Caef8f179cdf7eE77423868b1677a572db5Cd`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-30T23:26:06Z
- **Verdict:** REJECT (0/100)

---

## Executive Summary
**Overall: REJECT (0/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 15/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-20] Very few holders (11) — thin, easily manipulated distribution
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $3,494 (rug/illiquid)
- [-10] Low liquidity $3,494
- [-15] Pair only 0.4 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.4 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 5 flag(s), 0 positive signal(s)
  - [-20] Very few holders (11) — thin, easily manipulated distribution
  - [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-25] Very low liquidity $3,494 (rug/illiquid)
  - [-10] Low liquidity $3,494
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints SPX as an ultra-fresh Uniswap pair (0.4 days) between two similarly-named tokens, with just $3.5k liquidity, 11 total holders, and 100% of supply sitting in the top 10 non-LP addresses. Zero taxes, zero mint capability, no proxy, and owner=None are all present, yet the complete absence of any liquidity lock or burn means the same small set of wallets that already control the float can drain the pool at will. The contract is custom and verified rather than a cloned factory template, but its 7kB size and lack of any disclosed team or audit leave no independent way to confirm whether the verified source actually matches the deployed bytecode or contains hidden withdrawal logic. Taken together, the on-chain picture is internally consistent with a minimal-effort meme or test deployment that has not yet attracted (or been designed to attract) organic distribution.

The rule-based scoring correctly flags the extreme concentration and liquidity risk but may overweight the “pair age” penalty relative to the concrete tax/mint/owner data, which already shows no ongoing privileged control; conversely, it underweights the fact that the entire supply is still in the hands of the same 11 addresses that launched it, making the “no owner” flag less meaningful than it appears.

Next cycle or a human reviewer should pull the full verified source plus the exact transfer and liquidity-add events from the first block the pair appeared, then cross-check whether any of the top holders also seeded the initial liquidity.

## Market & Liquidity
- Symbol/Name: SPX / SPX6900
- Price: $0.000003561
- Liquidity: $3494.28
- 24h Volume: $8414.41
- 24h Change: 14.31%
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
- holder_count: `11`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 100.0% of supply
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
- Block explorer: https://etherscan.io/address/0xC19Caef8f179cdf7eE77423868b1677a572db5Cd
- Market pair: https://dexscreener.com/ethereum/0x332e2e7ec71930f543ad828d304d8b7a6ce7f29dd1fcbc8c2b0ac463e01c410b
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*