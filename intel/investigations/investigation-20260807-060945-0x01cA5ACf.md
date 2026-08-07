<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — FORGE

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![7/100](https://img.shields.io/badge/SAFETY_SCORE-7%2F100-FB7C77?style=flat-square)

- **Target:** `0x01cA5ACf53D0a18943dAe0dd6C08B88e62ad0BA3`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-08-07T06:09:45Z
- **Verdict:** REJECT (7/100)

---

## Expert Assessment
The token carries extreme risk and is not suitable for any investment exposure. Evidence from on-chain data and market feeds confirms an unrenounced owner at 0xf45930620d727a222826729d4abc08b88e62ad0BA3, 141 holders with the top 10 non-LP addresses controlling 85% of supply, zero liquidity locked, $10,380 in liquidity, and a 0.6-day-old Uniswap pair. The contract itself is verified with custom (non-factory) source, zero buy/sell tax, and no honeypot or mint flags detected. No independent corroboration exists for the self-declared website narrative around proof-of-work/proof-of-stake mechanics or any team identity. 

Primary residual risks are the unlocked liquidity, extreme holder concentration, and complete absence of provenance or audit signals, which together outweigh the clean technical hygiene read. Confidence in the technical safety assessment is moderate because the contract flags are directly observable, while confidence in any investment thesis is near zero given the missing external validation. 

Avoid the token entirely; re-check only if liquidity lock status or holder distribution materially improves with verifiable on-chain proof.

## Gaps & Confidence

- **Independent confirmation of website-project linkage or team identity** (confidence: 90%) — next: Search for any third-party mentions, audits, or prior deployments tied to theforge.eth.limo or the contract address
- **Liquidity lock transaction or multi-sig ownership details** (confidence: 80%) — next: Scan recent contract calls or LP token movements for any lock events

## Scoring Dashboard
**Overall: 7/100 — REJECT** ![7/100](https://img.shields.io/badge/overall-7%2F100-FB7C77?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![90/100](https://img.shields.io/badge/security-90%2F100-3FBA6E?style=flat-square) | Owner not renounced (0xf45930620d727a222826729d4abc08cb2c6162a2) — can still act on the contract. |
| Liquidity Health & Lock Quality | 20% | ![75/100](https://img.shields.io/badge/liquidity-75%2F100-86BC52?style=flat-square) | Only 0% of liquidity is locked — the deployer can pull the rest at any time; Low liquidity $10,380. |
| Holder Distribution & Concentration | 15% | ![77/100](https://img.shields.io/badge/holders-77%2F100-7CBC56?style=flat-square) | Low holder count (141); Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipulated. |
| Transparency & Provenance | 15% | ![90/100](https://img.shields.io/badge/transparency-90%2F100-3FBA6E?style=flat-square) | No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default; (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![60/100](https://img.shields.io/badge/narrative-60%2F100-CCBE37?style=flat-square) | has a declared project website; a narrative exists but this contract's affiliation with it is unverified. |
| Longevity & Clean Track Record | 10% | ![75/100](https://img.shields.io/badge/longevity-75%2F100-86BC52?style=flat-square) | Violent 24h move +18683% (volatility/manipulation); Pair only 0.6 days old (extreme fresh-launch risk). |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
> ⚠️ **Unverified identity**: this contract's affiliation with the project described below has NOT been independently confirmed. The name/symbol is only self-declared by the token — the search results and narrative below could describe a real but unrelated project whose name/branding this contract has simply reused.

## Known Facts
Address-level identity verification is NOT CONFIRMED for this token. The contract's affiliation with the project described below is unconfirmed, and the name/symbol could be reused by an unrelated or impersonating token.

All information below is drawn solely from the project's self-declared website (https://theforge.eth.limo and https://theforge.eth.limo/docs.html). No relevant results were returned from independent web searches this cycle.

The declared project describes FORGE as an ERC-20 token on Ethereum L1 that combines proof-of-work and proof-of-stake distribution mechanisms for a single token. It states a fixed supply cap of 21,000,000 FORGE with halving, no premine, no VC allocation, and no team bags. Users can either stake a small amount to unlock SHA-256 mining for new issuance or stake tokens to earn yield. The site positions the token as "Bitcoin's issuance, Ethereum's yield" and links to an open dApp and docs.

No user counts, trading volume, integrations, team names, leadership details, community signals, prior incidents, relaunches, or rebrands are mentioned in the provided excerpts.

## Findings
The declared materials present a hybrid PoW/PoS ERC-20 distribution model on Ethereum without its own chain. No external corroboration of adoption, traction, or team identity exists in the data available this cycle.

A concrete next check is to verify whether the deployed contract address matches the one referenced (or linked) on https://theforge.eth.limo and to cross-check on-chain issuance mechanics against the stated 21M cap and halving schedule.

Sources: https://theforge.eth.limo, https://theforge.eth.limo/docs.html

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0xf45930620d727a222826729d4abc08cb2c6162a2) — can still act on the contract
- [-8] Low holder count (141)
- [-15] Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $10,380
- [-10] Violent 24h move +18683% (volatility/manipulation)
- [-15] Pair only 0.6 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0xf45930620d727a222826729d4abc08cb2c6162a2) — can still act on the contract
**Tokenomics & Track Record** — 2 flag(s), 0 positive signal(s)
  - [-10] Violent 24h move +18683% (volatility/manipulation)
  - [-15] Pair only 0.6 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 4 flag(s), 0 positive signal(s)
  - [-8] Low holder count (141)
  - [-15] Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - [-10] Low liquidity $10,380
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Market & Liquidity
- Symbol/Name: FORGE / Forge
- Price: $0.3925
- Liquidity: $10380.44
- 24h Volume: $212187.3
- 24h Change: 18683%
- DEX: uniswap
- Price-change trend (m5/h1/h6/h24): `▁▁▁█` (m5: -0.5%, h1: -23.1%, h6: +9.7%, h24: +18683.0%)
- Volume trend (m5/h1/h6/h24): `▁▁▂█` (m5: $14, h1: $7,023, h6: $48,725, h24: $212,187)

## Project Links
- Website: https://theforge.eth.limo
- Website: https://theforge.eth.limo/docs.html

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
- holder_count: `141`
- owner_address: `0xf45930620d727a222826729d4abc08cb2c6162a2`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 84.8% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 1 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 9579 bytes

## Contract Verification
- Verified: True
- Name: Forge · Compiler: v0.8.26+commit.8a97fa7a
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
- Block explorer: https://etherscan.io/address/0x01cA5ACf53D0a18943dAe0dd6C08B88e62ad0BA3
- Market pair: https://dexscreener.com/ethereum/0x9b2652abbc3f8d74a3db0ac508c53dc83292619bbe040221df6830aa70324e80
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*