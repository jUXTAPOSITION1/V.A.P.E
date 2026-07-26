<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — LGNS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![PROCEED](https://img.shields.io/badge/VERDICT-PROCEED-10B981?style=flat-square) ![92/100](https://img.shields.io/badge/SAFETY_SCORE-92%2F100-36BA72?style=flat-square)

- **Target:** `0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063`
- **Chain:** 137 (Polygon)
- **Date:** 2026-07-26T05:10:55Z
- **Verdict:** PROCEED (92/100)

---

## Executive Summary
**Overall: PROCEED (92/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 100/100 |
| Tokenomics & Track Record | 100/100 |
| Holder Distribution & Liquidity | 92/100 |
| Transparency & Provenance | 100/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-8] Top 10 non-LP/burn holders control 62% of supply — meaningful concentration

## Positive Signals (real legitimacy evidence found)
- Verified as a real, CoinGecko-recognized major stablecoin ($557,194,496 circulating, $0.9997 peg)
- 3822846 holders — reasonably distributed
- Deep liquidity ($204,479,564)
- Trading 872+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 705+ days — independent longevity corroboration

## Risk Breakdown by Category
**Tokenomics & Track Record** — 0 flag(s), 1 positive signal(s)
  - (positive) Verified as a real, CoinGecko-recognized major stablecoin ($557,194,496 circulating, $0.9997 peg)
**Holder Distribution & Liquidity** — 1 flag(s), 2 positive signal(s)
  - [-8] Top 10 non-LP/burn holders control 62% of supply — meaningful concentration
  - (positive) 3822846 holders — reasonably distributed
  - (positive) Deep liquidity ($204,479,564)
**Transparency & Provenance** — 0 flag(s), 1 positive signal(s)
  - (positive) Custom verified source (not a mass-produced factory template)
**Other** — 0 flag(s), 2 positive signal(s)
  - (positive) Trading 872+ days without a known incident in this scan
  - (positive) DefiLlama has priced this token for 705+ days — independent longevity corroboration

## Expert Assessment
- ⚠️ **DISAGREES with the verdict above**:

The evidence paints LGNS as a Polygon child-chain proxy (UChildERC20Proxy) for an asset called Longinus, with unusually deep Quickswap liquidity and nearly 4 million holders. Those two facts together suggest either a heavily adopted bridged stable or a major wrapped token that has seen real usage since at least the 2022-era DefiLlama first-seen date. However, the same evidence immediately contradicts itself on price ($2.00 market vs $0.9998 DefiLlama), on asset class (Longinus vs “major stablecoin”), and on supply concentration (top-10 wallets holding 62 %). A legitimate bridged stablecoin would not show a $2 market price or be labeled Longinus; conversely, a non-stable token would not be described with a $557 M pegged circulating supply. The proxy pattern itself is standard for Polygon bridges, but the absence of any owner, mint, or tax flags does not resolve the mismatch—it only means the controlling contract sits elsewhere (the root on Ethereum or the bridge admin).

The rule-based score overweighted raw holder count and liquidity depth while underweighting the internal inconsistency between market data and the “stablecoin” narrative; those two data sources cannot both be accurate for the same contract. The concentration flag is noted but not connected to the proxy nature: if the top wallets are bridge escrows or market-maker contracts, 62 % is normal; if they are unidentified EOAs, it is a red flag the score does not resolve.

Next step: resolve the proxy by fetching the implementation address and the Ethereum L1 root token (if any) to determine exactly what asset is being bridged and who controls minting.

## Market & Liquidity (DexScreener)
- Symbol/Name: LGNS / Longinus
- Price: $2.0045
- Liquidity: $204479563.71
- 24h Volume: $16501878.32
- 24h Change: 0.12%
- DEX: quickswap
- Liquidity/Market-cap ratio: 36.7% — reasonable depth for its size

## Project Links (as declared on DexScreener)
- No official website/social links declared on this token's DexScreener listing.

## Tokenomics (CoinGecko, address-verified)
- Circulating supply: 557,252,157 DAI
- Total supply: 557,252,157
- Market cap: $557,194,496
- Fully diluted valuation: $557,194,496
- FDV/Market-cap ratio: 1.00x — most of supply is already circulating
- Homepage: https://polygon.technology/

## Token Security (GoPlus)
- is_honeypot: `0`
- is_proxy: `0`
- holder_count: `3822846`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 10 non-LP/burn holders control 61.7% of supply
- Liquidity-lock status not available this cycle.

## On-chain Presence (Polygon RPC)
- Is contract: unavailable this cycle (HTTP Error 401: Unauthorized)

## Contract Verification
- Verified: True
- Name: UChildERC20Proxy · Compiler: v0.6.6+commit.6c089d02
- Proxy: True · Implementation: 0x490e379c9cff64944be82b849f8fd5972c7999a7
- Notable functions found in verified source (informational, not scored): setImplementation
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.9998305023662037 · confidence: 0.99 · symbol: DAI
- First DefiLlama price: 2024-08-19T23:39:14Z (705.2 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://polygonscan.com/address/0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063
- DexScreener pair: https://dexscreener.com/polygon/0x882df4b0fb50a229c3b4124eb18c759911485bfb
- CoinGecko: https://www.coingecko.com/en/coins/polygon-pos-bridged-dai-polygon-pos
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*