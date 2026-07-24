<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — PHAR

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![43/100](https://img.shields.io/badge/SAFETY_SCORE-43%2F100-FBB432?style=flat-square)

- **Target:** `0xAAAB9D12A30504559b0C5a9A5977fEE4A6081c6b`
- **Chain:** 43114 (Avalanche)
- **Date:** 2026-07-24T15:40:54Z
- **Verdict:** REJECT (43/100)

---

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-10] Owner not renounced (0xaaa823aa799bda3193d46476539bcb1da5b71330) — can still act on the contract
- [-25] Very low liquidity $1,919 (rug/illiquid)
- [-10] Low liquidity $1,919
- [note] address has no contract code (EOA or not deployed)

## Positive Signals (real legitimacy evidence found)
- 11238 holders — reasonably distributed
- Trading 937+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 914+ days — independent longevity corroboration

## Expert Assessment
- Expert assessment not available this cycle.

## Market & Liquidity (DexScreener)
- Symbol/Name: PHAR / PHARAOH
- Price: $45.43
- Liquidity: $1919.14
- 24h Volume: $32.57
- 24h Change: 1.23%
- DEX: pharaoh

## Token Security (GoPlus)
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
- holder_count: `11238`
- owner_address: `0xaaa823aa799bda3193d46476539bcb1da5b71330`

## On-chain Presence (Avalanche RPC)
- Is contract: False
- Code size: 0 bytes

## Contract Verification
- Verified: True
- Name: EmissionsToken · Compiler: v0.8.22+commit.4fc1097e
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- Price: $46.69703806982943 · confidence: 0.99 · symbol: PHAR
- First DefiLlama price: 2024-01-23T04:32:15Z (913.5 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*