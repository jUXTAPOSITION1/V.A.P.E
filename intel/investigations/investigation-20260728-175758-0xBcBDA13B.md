<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — FERRET

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![PROCEED](https://img.shields.io/badge/VERDICT-PROCEED-10B981?style=flat-square) ![82/100](https://img.shields.io/badge/SAFETY_SCORE-82%2F100-65BB60?style=flat-square)

- **Target:** `0xBcBDA13Bd60bC0e91745186E274D1445078D6b33`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-28T17:57:58Z
- **Verdict:** PROCEED (82/100)

---

## Executive Summary
**Overall: PROCEED (82/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 82/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Top 10 non-LP/burn holders control 65% of supply — meaningful concentration
- [-10] Low liquidity $21,191

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- 2316 holders — reasonably distributed
- 100% of liquidity is locked — reduced rug-pull risk
- Trading 924+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 918+ days — independent longevity corroboration

## Risk Breakdown by Category
**Security & Contract Risk** — 0 flag(s), 1 positive signal(s)
  - (positive) Ownership renounced
**Holder Distribution & Liquidity** — 2 flag(s), 2 positive signal(s)
  - [-8] Top 10 non-LP/burn holders control 65% of supply — meaningful concentration
  - [-10] Low liquidity $21,191
  - (positive) 2316 holders — reasonably distributed
  - (positive) 100% of liquidity is locked — reduced rug-pull risk
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 924+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 918+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

The evidence paints FERRET as a long-running, low-profile token (branded Ferret AI) that has survived ~2.5 years on Uniswap without a documented rug or exploit. Renounced ownership, zero taxes, non-mintable status, and 100% locked liquidity form a consistent anti-rug profile, while the custom (non-factory) verified contract and multi-year DefiLlama pricing history add weight that this is not a fly-by-night deployment. The 2316-holder base and steady (if modest) volume further suggest organic if limited interest rather than a coordinated launch-and-dump.

That said, the 65% top-10 concentration sits in tension with the “reasonably distributed” framing; combined with only $21k liquidity, it leaves the token structurally vulnerable to a small group moving price or exiting, even if historical behavior has been quiet. The aggregator’s 2024 first-seen date clashes with the 918–924-day trading/DefiLlama records, hinting at incomplete external data rather than a new token.

The rule-based 82 score correctly credits the longevity and lock signals but may overweight raw holder count while under-weighting how concentrated ownership interacts with thin liquidity to create outsized exit risk.

Next check: pull the top-10 non-LP wallets and map their funding sources and any coordinated transfer patterns over the last 90 days.

## Market & Liquidity
- Symbol/Name: FERRET / Ferret AI
- Price: $0.00002153
- Liquidity: $21190.72
- 24h Volume: $17236.25
- 24h Change: 9.8%
- DEX: uniswap

## Project Links
- Website: https://www.ferretai.org/
- twitter: https://twitter.com/ferretaicoin
- telegram: https://t.me/ferretaitoken

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
- holder_count: `2316`
- owner_address: `0x0000000000000000000000000000000000000000`

## Holder Distribution & Liquidity Lock
- Top 10 non-LP/burn holders control 65.3% of supply
- 100.0% of tracked liquidity-pool tokens are locked (across 3 LP holder(s))

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 9474 bytes

## Contract Verification
- Verified: True
- Name: FerretAI · Compiler: v0.8.21+commit.d9974bed
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, _transferOwnership, renounceOwnership, setFeeTo, setFeeToSetter, transferOwnership, whitelistContract

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- First DefiLlama price: 2024-01-23T03:00:02Z (917.6 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://etherscan.io/address/0xBcBDA13Bd60bC0e91745186E274D1445078D6b33
- Market pair: https://dexscreener.com/ethereum/0xa8854439c8dae6b56e2c72da6b4b1ae098795caa
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*