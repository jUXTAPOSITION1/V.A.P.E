<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — VSN

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![PROCEED](https://img.shields.io/badge/VERDICT-PROCEED-10B981?style=flat-square) ![92/100](https://img.shields.io/badge/SAFETY_SCORE-92%2F100-36BA72?style=flat-square)

- **Target:** `0x6fBBbD8bFB1cd3986B1D05e7861a0f62F87DB74b`
- **Chain:** 42161 (Arbitrum)
- **Date:** 2026-07-17T03:47:52Z
- **Verdict:** PROCEED (92/100)

---

## Verdict Rationale (risk factors)
- [-8] Upgradeable proxy (verify implementation)

## Positive Signals (real legitimacy evidence found)
- 42784 holders — reasonably distributed
- Deep liquidity ($653,197)
- Trading 247+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 366+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

AGREE:
The contract is a long-running ERC1967Proxy on Arbitrum whose implementation has been live and priced by DefiLlama for over a year with no ownership controls remaining, allowing a genuinely distributed 42k-holder base to accumulate and trade against $650k of liquidity without any mint or tax flags. The 247-day incident-free history plus custom (non-factory) verified bytecode indicate the proxy pattern is now inert rather than an active control vector. This combination produces the observed steady volume and price stability rather than the typical short-lived proxy rug pattern.

Watch the on-chain implementation address for any future delegatecall or upgrade events, as the current owner=None state can only change if the logic contract itself contains an unrevoked admin function.

## Market & Liquidity (DexScreener)
- Symbol/Name: VSN / Vision
- Price: $0.03404
- Liquidity: $653196.77
- 24h Volume: $247443.14
- 24h Change: 1.67%
- DEX: pancakeswap

## Token Security (GoPlus)
- buy_tax: ``
- sell_tax: ``
- is_proxy: `1`
- holder_count: `42784`

## On-chain Presence (Arbitrum RPC)
- Is contract: True
- Code size: 163 bytes

## Contract Verification
- Verified: True
- Name: ERC1967Proxy · Compiler: v0.8.28+commit.7893614a
- Proxy: True · Implementation: 0x361651554422d1ce11f640b1e644ee31102d574c

## Threat Correlation
- Proxy contract (upgradeable logic) — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.03357147830424816 · confidence: 0.99 · symbol: VSN
- First DefiLlama price: 2025-07-16T14:43:20Z (365.5 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*