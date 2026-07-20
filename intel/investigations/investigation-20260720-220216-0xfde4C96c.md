<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — USDT

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![45/100](https://img.shields.io/badge/SAFETY_SCORE-45%2F100-FBB72E?style=flat-square)

- **Target:** `0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-20T22:02:16Z
- **Verdict:** REJECT (45/100)

---

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-25] Owner can change balances (rug surface)
- [-10] Owner not renounced (0x4200000000000000000000000000000000000010) — can still act on the contract
- [-8] No pair-creation timestamp available — cannot establish track record length

## Positive Signals (real legitimacy evidence found)
- 612036 holders — reasonably distributed
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 690+ days — independent longevity corroboration

## Expert Assessment
- Expert assessment not available this cycle.

## Market & Liquidity (DexScreener)
- Symbol/Name: USDT / Tether USD
- Price: $0.9999
- Liquidity: $427843.76
- 24h Volume: $5305103.76
- 24h Change: 0.03%
- DEX: aerodrome

## Token Security (GoPlus)
- is_honeypot: `0`
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `1`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `612036`
- owner_address: `0x4200000000000000000000000000000000000010`

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 6774 bytes

## Contract Verification
- Verified: True
- Name: USDT · Compiler: v0.7.4+commit.3f05b770
- Proxy: False · Implementation: None

## Threat Correlation
- Owner can alter balances/ownership — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $0.9982485376065562 · confidence: 0.99 · symbol: USDT
- First DefiLlama price: 2024-08-29T17:39:13Z (690.2 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 2 of VAPE's own $0.01 x402 market-data offerings against this token (real USDC on Base, 2 settled, $0.02 total):
  - **stablecoins** (settled, cdp) — count=48; stablecoins: 25 item(s)
  - **chain_fees** (settled, vapor) — total_fees_24h=1032989; total_fees_7d=11059834; protocols: 20 item(s)

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*