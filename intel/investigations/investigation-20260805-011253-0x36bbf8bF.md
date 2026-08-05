<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — STACK

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0x36bbf8bFe6921E137b621668Bda207A287c9442f`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-08-05T01:12:53Z
- **Verdict:** REJECT (0/100)

---

## Expert Assessment
The evidence base here is genuinely thin, limited to on-chain token-safety data and a DEX listing with no declared web or social presence. STACK shows clean technical hygiene on the contract itself—no honeypot behavior, zero buy or sell tax, mint disabled, and verified source code of 3202 bytes rather than a factory template.

Holder distribution and liquidity metrics are the dominant problems: only three holders total, with extreme concentration in the top addresses, plus liquidity of just $1,945 on a pair that is 0.3 days old. Ownership has not been renounced, leaving the listed controller able to act on the contract.

No team identity, audit, or external proof of legitimacy appears in the data, so the clean security scan does not offset the fresh-launch and concentration risks.

Technical safety read carries high confidence because the on-chain flags are direct and consistent; overall investment thesis carries low confidence because narrative, distribution, and liquidity signals are absent or negative. A single concrete positive is the verified non-factory source, but that alone does not change posture.

Avoid entirely until ownership is renounced, liquidity deepens materially, and holder count plus distribution improve.

## Gaps & Confidence

- **no external validation or social proof exists** (confidence: 90%) — next: search for any off-chain mentions of the deployer address or token name beyond DEX listing

## Scoring Dashboard
**Overall: 0/100 — REJECT** ![0/100](https://img.shields.io/badge/overall-0%2F100-FB7185?style=flat-square)

| Category | Weight | Score | Rationale |
|---|---|---|---|
| Contract Security & Controls | 25% | ![90/100](https://img.shields.io/badge/security-90%2F100-3FBA6E?style=flat-square) | Owner not renounced (0x7ebf7592100fa5769ddaa22e1b656035c47c6545) — can still act on the contract. |
| Liquidity Health & Lock Quality | 20% | ![65/100](https://img.shields.io/badge/liquidity-65%2F100-B4BD40?style=flat-square) | Very low liquidity $1,945 (rug/illiquid); Low liquidity $1,945. |
| Holder Distribution & Concentration | 15% | ![65/100](https://img.shields.io/badge/holders-65%2F100-B4BD40?style=flat-square) | Very few holders (3) — thin, easily manipulated distribution; Top 3 non-LP/burn holders control 195% of supply — concentrated, easily manipulated. |
| Transparency & Provenance | 15% | ![90/100](https://img.shields.io/badge/transparency-90%2F100-3FBA6E?style=flat-square) | No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default; (+) Custom verified source (not a mass-produced factory template). |
| Narrative Strength & Social Proof | 15% | ![25/100](https://img.shields.io/badge/narrative-25%2F100-FB9854?style=flat-square) | no coherent project narrative could be established this cycle. |
| Longevity & Clean Track Record | 10% | ![85/100](https://img.shields.io/badge/longevity-85%2F100-56BB65?style=flat-square) | Pair only 0.3 days old (extreme fresh-launch risk). |

*Weighted, multi-factor category view for where the risk actually concentrates — the Overall score above, computed by the full deterministic scoring engine, is the authoritative verdict; these categories are supporting instrumentation, not a second scoring engine.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x7ebf7592100fa5769ddaa22e1b656035c47c6545) — can still act on the contract
- [-20] Very few holders (3) — thin, easily manipulated distribution
- [-15] Top 3 non-LP/burn holders control 195% of supply — concentrated, easily manipulated
- [-25] Very low liquidity $1,945 (rug/illiquid)
- [-10] Low liquidity $1,945
- [-15] Pair only 0.3 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-10] Owner not renounced (0x7ebf7592100fa5769ddaa22e1b656035c47c6545) — can still act on the contract
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.3 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 4 flag(s), 0 positive signal(s)
  - [-20] Very few holders (3) — thin, easily manipulated distribution
  - [-15] Top 3 non-LP/burn holders control 195% of supply — concentrated, easily manipulated
  - [-25] Very low liquidity $1,945 (rug/illiquid)
  - [-10] Low liquidity $1,945
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Market & Liquidity
- Symbol/Name: STACK / Stack
- Price: $0.000001028
- Liquidity: $1945.46
- 24h Volume: $113.46
- 24h Change: -0.47%
- DEX: uniswap
- Volume trend (m5/h1/h6/h24): `▁▁▁█` (m5: $0, h1: $0, h6: $0, h24: $113)

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
- holder_count: `3`
- owner_address: `0x7ebf7592100fa5769ddaa22e1b656035c47c6545`

## Holder Distribution & Liquidity Lock
- Top 3 non-LP/burn holders control 194.6% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 3202 bytes

## Contract Verification
- Verified: True
- Name: Token · Compiler: v0.8.23+commit.f704f362
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): renounceOwnership, rescueERC20, rescueETH

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
- Block explorer: https://etherscan.io/address/0x36bbf8bFe6921E137b621668Bda207A287c9442f
- Market pair: https://dexscreener.com/ethereum/0x4aaf00ae05f15bd4a189dc410d65e5def8fea815e431aeb3f2079b9f502d0634
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*