<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — IBNAi

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![55/100](https://img.shields.io/badge/SAFETY_SCORE-55%2F100-E4BE2D?style=flat-square)

- **Target:** `0xFdcD8be9DD37CF982472d30eeeE4ec50A0296953`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-17T18:34:51Z
- **Verdict:** CAUTION (55/100)

---

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x0f5f60ad3e43839d6b9d4a6d1d8eded24db73c32) — can still act on the contract
- [-10] Violent 24h move +1460% (volatility/manipulation)
- [-15] Pair only 0.2 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

AGREE:
This token launched under a day ago on Uniswap and immediately attracted heavy volume that drove a 1460% price spike on roughly $265k liquidity, while the verified custom contract shows clean GoPlus flags (no mint, no tax, no honeypot) and already reached 430 holders. The sole remaining control point is the unrenounced owner at 0x0f5f60ad3e43839d6b9d4a6d1d8eded24db73c32, which can still execute privileged functions on a contract that has otherwise been left in its initial state. The combination points to a rapid-distribution launch that has not yet passed the window where the deployer could still alter economics or drain liquidity.

Monitor the owner address for any direct calls to the token contract or liquidity-pool approvals over the next 48 hours.

## Market & Liquidity (DexScreener)
- Symbol/Name: IBNAi / Investor Brand Network Ai
- Price: $0.0005407
- Liquidity: $264838.49
- 24h Volume: $1845046.15
- 24h Change: 1460%
- DEX: uniswap

## Token Security (GoPlus)
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
- holder_count: `430`
- owner_address: `0x0f5f60ad3e43839d6b9d4a6d1d8eded24db73c32`

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 3295 bytes

## Contract Verification
- Verified: True
- Name: InvestorBrandNetworkAi · Compiler: v0.8.20+commit.a1b79de6
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*