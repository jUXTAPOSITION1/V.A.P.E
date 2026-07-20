<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — RFI

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![65/100](https://img.shields.io/badge/SAFETY_SCORE-65%2F100-B4BD40?style=flat-square)

- **Target:** `0xA1AFFfE3F4D611d252010E3EAf6f4D77088b0cd7`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-20T00:04:16Z
- **Verdict:** CAUTION (65/100)

---

## Verdict Rationale (risk factors)
- [-25] Very low liquidity $1,181 (rug/illiquid)
- [-10] Low liquidity $1,181

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- 8129 holders — reasonably distributed
- Trading 2050+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 822+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

AGREE:
This is the original RFI reflection token from ~2019 whose contract has been inert for years: renounced ownership, fixed 1% tax, no mint or proxy, and a broad holder base that has simply stopped trading. The $1.18 k liquidity pool on Uniswap is the only live risk surface; everything else (verified custom source, 2 000+ day history, DefiLlama coverage) confirms a long-dead but non-malicious contract rather than an active rug. Low 24 h volume ($0.18) is the predictable result of that illiquidity, not evidence of new malice.

Watch the single remaining Uniswap pool for any LP-token movements or sudden removal; a burn-address check on the LP itself would confirm whether the liquidity can still be pulled.

## Market & Liquidity (DexScreener)
- Symbol/Name: RFI / reflect.finance
- Price: $0.003891
- Liquidity: $1181.23
- 24h Volume: $0.18
- 24h Change: None%
- DEX: uniswap

## Token Security (GoPlus)
- is_honeypot: `0`
- buy_tax: `0.01`
- sell_tax: `0.01`
- is_mintable: `0`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `8129`
- owner_address: `0x0000000000000000000000000000000000000000`

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 6937 bytes

## Contract Verification
- Verified: True
- Name: REFLECT · Compiler: v0.6.2+commit.bacdbe57
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- First DefiLlama price: 2024-04-18T12:06:44Z (822.5 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*