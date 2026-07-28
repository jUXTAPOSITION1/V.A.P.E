<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — DOGE1

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![18/100](https://img.shields.io/badge/SAFETY_SCORE-18%2F100-FB8D62?style=flat-square)

- **Target:** `0xAfB97Dd6630f1930B5cE8C542AfE7B988e40e805`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-28T14:54:01Z
- **Verdict:** REJECT (18/100)

---

## Executive Summary
**Overall: REJECT (18/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 78/100 |
| Tokenomics & Track Record | 85/100 |
| Holder Distribution & Liquidity | 65/100 |
| Transparency & Provenance | 90/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-10] Owner not renounced (0xedb43ebf3306dce578d24b0555240d07e4778afc) — can still act on the contract
- [-20] Very few holders (2) — thin, easily manipulated distribution
- [-15] Top 2 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Pair only 0.1 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 2 flag(s), 0 positive signal(s)
  - [-12] Mintable supply (dilution risk)
  - [-10] Owner not renounced (0xedb43ebf3306dce578d24b0555240d07e4778afc) — can still act on the contract
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-15] Pair only 0.1 days old (extreme fresh-launch risk)
**Holder Distribution & Liquidity** — 2 flag(s), 0 positive signal(s)
  - [-20] Very few holders (2) — thin, easily manipulated distribution
  - [-15] Top 2 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
**Transparency & Provenance** — 1 flag(s), 1 positive signal(s)
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints a picture of a freshly deployed, manually written ERC-20 (MintBurnTeamToken) that was paired on Uniswap less than three hours ago under the DOGE1 ticker. The contract's mint flag is live, the deployer/owner wallet still holds full control, and every token sits in just two addresses—almost certainly the same wallet and the liquidity pool itself. Zero volume despite $433k in liquidity is the tell: the pool was seeded but no external buyers have touched it, so the "market" is entirely synthetic. The custom (non-factory) source code is the only non-red flag, yet it does nothing to offset the fact that the same small set of keys can still expand supply or drain the pair at any moment.

The rule-based score correctly weights the combination of mintability + unrenounced ownership + two-holder concentration as decisive; those three items are not independent risks but interlocking control points that let one actor manufacture tokens and immediately sell them into the pool. The only item arguably overweighted is the "no audit" penalty, since a brand-new contract with two holders has no meaningful third-party surface to audit anyway—the real gap is the total absence of any on-chain or off-chain signal that the owner wallet has ever done anything except deploy this contract.

Next cycle or a human reviewer should pull the transaction history and token-balance deltas for the owner address (0xedb43ebf3306dce578d24b0555240d07e4778afc) over the last 48 hours to see whether any liquidity was removed or any mint calls were executed after the pair was created.

## Market & Liquidity
- Symbol/Name: DOGE1 / DOGE-1
- Price: $0.5773
- Liquidity: $433013.66
- 24h Volume: $0.23
- 24h Change: -0.08%
- DEX: uniswap

## Project Links
- No official website/social links declared for this token.

## Tokenomics (address-verified)
- Not available this cycle (no tokenomics data tracked for this exact contract address, or the token isn't indexed yet) — absence noted, not penalized.

## Token Security
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `2`
- owner_address: `0xedb43ebf3306dce578d24b0555240d07e4778afc`

## Holder Distribution & Liquidity Lock
- Top 2 non-LP/burn holders control 100.0% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 5150 bytes

## Contract Verification
- Verified: True
- Name: MintBurnTeamToken · Compiler: v0.6.12+commit.27d51765
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): _burn, _mint, burn, burnFrom, mint, renounceOwnership, transferOwnership

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
- Block explorer: https://etherscan.io/address/0xAfB97Dd6630f1930B5cE8C542AfE7B988e40e805
- Market pair: https://dexscreener.com/ethereum/0x1e1ac315392c0276463ced85da16758581f2a839
- On-chain security, contract-verification, and market-data sources were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (on-chain token-safety data, market/liquidity data, contract verification, and a cross-chain hack-incident feed) plus a real web search for public reputation signals.*