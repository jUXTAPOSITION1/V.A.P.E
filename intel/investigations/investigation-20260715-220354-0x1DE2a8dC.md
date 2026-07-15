<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — DOJI

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![37/100](https://img.shields.io/badge/SAFETY_SCORE-37%2F100-FBAB3D?style=flat-square)

- **Target:** `0x1DE2a8dCBe56Abf971E9F2a9feC21082901ef0e5`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-15T22:03:54Z
- **Verdict:** REJECT (37/100)

---

## Verdict Rationale (risk factors)
- [-8] Low holder count (134)
- [-25] Very low liquidity $7,935 (rug/illiquid)
- [-10] Low liquidity $7,935
- [-10] Violent 24h move +467% (volatility/manipulation)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Trading 268+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

AGREE:
This contract is a low-float meme token that has survived nearly nine months on Uniswap with zero tax, mint, or honeypot functions and a non-templated verified source, yet its $8 k liquidity pool is now absorbing a $95 k daily volume spike that produced a 467 % price move. The combination points to a thin, organically traded name that has suddenly attracted speculative flows rather than an exit-scam deployment. The 134-holder base and lack of any third-party audit keep the surface area for manipulation high even after the long clean run.

The heuristic overweighted the static liquidity and holder thresholds while under-weighting the 268-day incident-free history and the explicit custom verification signal.

Watch the next two LP transactions on the pair for any removal or concentrated add that would change the effective float.

## Market & Liquidity (DexScreener)
- Symbol/Name: DOJI / COBIE'S DOG
- Price: $0.00001336
- Liquidity: $7934.99
- 24h Volume: $95075.08
- 24h Change: 467%
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
- holder_count: `134`

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 1764 bytes

## Contract Verification
- Verified: True
- Name: Token · Compiler: v0.8.26+commit.8a97fa7a
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 1 of VAPE's own $0.01 x402 market-data offerings against this token (real USDC on Base, 0 settled, $0.00 total):
  - **bridges** (failed) — error — HTTP 500

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*