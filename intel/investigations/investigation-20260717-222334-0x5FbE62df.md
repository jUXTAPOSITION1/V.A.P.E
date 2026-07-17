<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — TSG

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![50/100](https://img.shields.io/badge/SAFETY_SCORE-50%2F100-FBBF24?style=flat-square)

- **Target:** `0x5FbE62dfdB805E1711d36Db0c2E22a2D77195BA3`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-17T22:23:34Z
- **Verdict:** CAUTION (50/100)

---

## Verdict Rationale (risk factors)
- [-10] Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act on the contract
- [-20] Very few holders (24) — thin, easily manipulated distribution
- [-10] Low liquidity $19,285
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

AGREE:
The contract is a bare-bones, owner-controlled ERC-20 that was hand-written and verified rather than cloned from a factory, yet it still sits on a single EOA that retains full privileges while the token trades in a $19 k liquidity pool shared by only 24 wallets and <$500 daily volume. That combination produces exactly the classic “thinly distributed, admin-held micro-cap” profile: no technical backdoors are visible in the verified code, but the distribution and control surface make price or liquidity attacks trivial to execute. The rule-based score therefore correctly lands at caution rather than “safe” or “honeypot.”

One concrete next step is to watch the owner (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) for any on-chain calls to the token contract or for movements of the LP tokens it may hold.

## Market & Liquidity (DexScreener)
- Symbol/Name: TSG / the sleeping giant
- Price: $0.0000001824
- Liquidity: $19284.92
- 24h Volume: $466.21
- 24h Change: -0.84%
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
- transfer_pausable: `0`
- holder_count: `24`
- owner_address: `0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12`

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 10143 bytes

## Contract Verification
- Verified: True
- Name: DERC20 · Compiler: v0.8.26+commit.8a97fa7a
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 1 of VAPE's own $0.01 x402 market-data offerings against this token (real USDC on Base, 0 settled, $0.00 total):
  - **token_chart** (failed) — error — HTTP 500

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*