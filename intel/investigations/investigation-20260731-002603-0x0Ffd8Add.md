<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — MEMESTOCK

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0x0Ffd8Add68ED4D1c3305baA2BF66B5D6440206F7`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-31T00:26:03Z
- **Verdict:** REJECT (0/100)

---

## Executive Summary
**Overall: REJECT (0/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 30/100 |
| Transparency & Provenance | 60/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: 401K (0x7075DdC6b9D265a372b697296A9114ed1Af3F9D7) — REJECT 5/100 — likely the same serial campaign
- [-20] Very few holders (4) — thin, easily manipulated distribution
- [-15] Top 4 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-25] Very low liquidity $3,201 (rug/illiquid)
- [-10] Low liquidity $3,201
- [-15] Pair only 0.4 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.4 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 4 flag(s), 0 positive signal(s)
  - [-20] Very few holders (4) — thin, easily manipulated distribution
  - [-15] Top 4 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-25] Very low liquidity $3,201 (rug/illiquid)
  - [-10] Low liquidity $3,201
**Transparency & Provenance** — 2 flag(s), 1 positive signal(s)
  - [-30] Same deployer has a prior CAUTION/REJECT verdict on record: 401K (0x7075DdC6b9D265a372b697296A9114ed1Af3F9D7) — REJECT 5/100 — likely the same serial campaign
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints a picture of a hastily launched, minimally distributed token controlled by an extremely small set of wallets. With only four holders owning the entire supply (outside any LP or burn) and liquidity sitting at roughly $3.2k on a Uniswap pair that is less than half a day old, the structure is consistent with a single operator (or tight group) seeding a token, adding tiny liquidity, and waiting for external buyers. The zero taxes, non-mintable status, and lack of proxy are technically clean, yet they do not offset the fact that the same deployer previously launched 401K, which received an identical REJECT classification; together the two contracts point to a repeatable pattern rather than an isolated experiment. The custom verified source code is the sole mitigating detail, but at 7 kB it is still a standard ERC-20 skeleton and does not imply any unique utility or team accountability.

The rule-based score correctly weights the combination of extreme concentration, microscopic liquidity, and serial-deployer history; it does not appear to overweight any single factor. The one element that could be under-weighted is the absence of any on-chain activity linking the four holders to external exchanges or known liquidity providers, which would further confirm whether distribution is genuinely organic or simply parked.

Next step: pull the full transaction history of the deployer address across both 401K and MEMESTOCK to map exact timing of liquidity adds versus any sells or transfers to the current four holders.

## Market & Liquidity
- Symbol/Name: MEMESTOCK / MEMESTOCK
- Price: $0.000003227
- Liquidity: $3200.76
- 24h Volume: $1110.09
- 24h Change: 6.11%
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
- holder_count: `4`

## Holder Distribution & Liquidity Lock
- Top 4 non-LP/burn holders control 100.0% of supply
- Liquidity-lock status not available this cycle.

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
- Block explorer: https://etherscan.io/address/0x0Ffd8Add68ED4D1c3305baA2BF66B5D6440206F7
- Market pair: https://dexscreener.com/ethereum/0x90ce3686a9d9de5c95566eee991eee11fb13c1175c7c49e239f8899181b2bccd
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*