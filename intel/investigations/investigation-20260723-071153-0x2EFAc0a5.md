<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — $checkr

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![CAUTION](https://img.shields.io/badge/VERDICT-CAUTION-FBBF24?style=flat-square) ![60/100](https://img.shields.io/badge/SAFETY_SCORE-60%2F100-CCBE37?style=flat-square)

- **Target:** `0x2EFAc0a597A37050AafcF4beC627249D533DD9f8`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-23T07:11:53Z
- **Verdict:** CAUTION (60/100)

---

## Verdict Rationale (risk factors)
- [-20] Deployed via a permissionless meme-token factory template (ClankerToken) — no team vetting by design; this pattern strongly correlates with abandoned/rugged tokens
- [-10] Low liquidity $49,983
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- 62549 holders — reasonably distributed
- Trading 491+ days without a known incident in this scan

## Expert Assessment
- Agrees with the verdict above:

AGREE:
The contract $checkr, deployed via a permissionless meme-token factory template, exhibits characteristics that justify caution, such as low liquidity and lack of known third-party audit or verifiable team identity. Despite having a reasonably distributed holder base and no known incidents in over 491 days of trading, the absence of team vetting and potential for abandonment due to its deployment method pose significant risks. The renouncement of ownership could be seen as a positive signal, but it does not outweigh the concerns associated with its deployment and operational transparency. 

Given the contract's specific risks, it's essential to monitor its liquidity and trading activity closely to watch for any signs of manipulation or sudden changes that could indicate a potential rug pull or other malicious activities.

## Market & Liquidity (DexScreener)
- Symbol/Name: $checkr / Checkr
- Price: $0.0000007282
- Liquidity: $49983.44
- 24h Volume: $169.54
- 24h Change: -1.11%
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
- holder_count: `62549`
- owner_address: `0x0000000000000000000000000000000000000000`

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 12282 bytes

## Contract Verification
- Verified: True
- Name: ClankerToken · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $7.214902878252026e-07 · confidence: 0.99 · symbol: $checkr
- First DefiLlama price: 2026-05-17T08:58:02Z (66.9 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 2 of VAPE's own $0.01 x402 market-data offerings against this token (real USDC on Base, 2 settled, $0.02 total):
  - **bridges** (settled, cdp) — error — HTTP 402
  - **chain_protocols** (settled, vapor) — count=713; protocols: 20 item(s)

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*