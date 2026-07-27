<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — RWA

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![32/100](https://img.shields.io/badge/SAFETY_SCORE-32%2F100-FBA347?style=flat-square)

- **Target:** `0xA64aC4eCc7302Ba4dCF1F9Cc8856Ac5C2eD2C581`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-27T16:12:38Z
- **Verdict:** REJECT (32/100)

---

## Executive Summary
**Overall: REJECT (32/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 90/100 |
| Tokenomics & Track Record | 75/100 |
| Holder Distribution & Liquidity | 77/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0xe1450d7708de452b1d89cbf9b83e0cba97719d39) — can still act on the contract
- [-8] Low holder count (66)
- [-15] Top 10 non-LP/burn holders control 82% of supply — concentrated, easily manipulated
- [-10] Violent 24h move +634% (volatility/manipulation)
- [-15] Pair only 0.8 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0xe1450d7708de452b1d89cbf9b83e0cba97719d39) — can still act on the contract
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +634% (volatility/manipulation)
  - [-15] Pair only 0.8 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-8] Low holder count (66)
  - [-15] Top 10 non-LP/burn holders control 82% of supply — concentrated, easily manipulated
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints a classic ultra-fresh launch with heavy insider control rather than any coherent RWA narrative. The contract (verified under the name TTT, not Real World Acquisitions) has been live less than a day, yet already shows a 634% price spike on over $1M volume against only $214k liquidity; that combination lines up directly with the 82% supply held by the top 10 wallets and the mere 66 total holders, indicating the move was almost certainly driven by a small group rather than organic demand. The still-active owner at 0xe1450d7708de452b1d89cbf9b83e0cba97719d39 retains full authority while the token carries zero taxes and no mint function, which removes the most obvious rug vectors but leaves open the possibility of targeted transfers, privileged role abuse, or coordinated dumps. The custom (non-factory) source code is the single mitigating detail, yet it does not reconcile with the total absence of any team identity or audit trail.

The rule-based score correctly flags the age, concentration, and owner risk but may be overweighting the volatility number itself; a 634% move on a sub-day pair is the expected symptom of the 82% holder concentration rather than an independent red flag. It also under-weights the name mismatch (TTT vs. RWA marketing), which points to possible re-branding or copy-paste deception not captured in the numeric factors.

Next step: pull the full transaction history of the owner address 0xe1450d7708de452b1d89cbf9b83e0cba97719d39 to see whether it has deployed or interacted with prior tokens that later rugged or vanished.

## Market & Liquidity
- Symbol/Name: RWA / Real World Acquisitions
- Price: $0.0003552
- Liquidity: $214227.24
- 24h Volume: $1029689.55
- 24h Change: 634%
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
- holder_count: `66`
- owner_address: `0xe1450d7708de452b1d89cbf9b83e0cba97719d39`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 81.5% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 9260 bytes

## Contract Verification
- Verified: True
- Name: TTT · Compiler: v0.8.30+commit.73712a01
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _setOwner, burn, mint, onBurn, renounceOwnership, setFeeAddress, transferOwnership

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
- Block explorer: https://etherscan.io/address/0xA64aC4eCc7302Ba4dCF1F9Cc8856Ac5C2eD2C581
- Market pair: https://dexscreener.com/ethereum/0x04e84ced393e50336af437a7381d422111e469ceae8db0d26481c7adfd212483
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*