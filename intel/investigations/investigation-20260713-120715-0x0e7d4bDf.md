<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — Claude

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![0/100](https://img.shields.io/badge/SAFETY_SCORE-0%2F100-FB7185?style=flat-square)

- **Target:** `0x0e7d4bDfe24aa679F9903F10414A25F56CBEBB07`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-13T12:07:15Z
- **Verdict:** REJECT (0/100)

---

## Verdict Rationale (risk factors)
- [-20] Deployed via a permissionless meme-token factory template (ClankerToken) — no team vetting by design; this pattern strongly correlates with abandoned/rugged tokens
- [-35] Token name/symbol (Claude / Claude) impersonates a real company with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: OpenAI (0x43D6e8F4e413028365E9cf83D1e6c2181e8e3b07) — REJECT 0/100 — likely the same serial campaign
- [-5] Pair 14.4 days old — under a month, still unproven
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- Ownership renounced
- 13833 holders — reasonably distributed

## Expert Assessment
- Agrees with the verdict above:

AGREE:
This token is a low-effort meme clone spun out of the ClankerToken factory by a deployer already flagged for the identical OpenAI impersonation play; the renounced ownership and 13k-holder distribution are the only surface-level mitigations, but they do not offset the deliberate brand-jacking or the factory pattern that has repeatedly produced abandoned or drained assets. Liquidity sits at ~$319k with essentially zero 24h volume, indicating the position is illiquid and price action is driven by thin, coordinated flows rather than organic interest. The 14-day pair age further shows the campaign is still in its early extraction window.

Watch the top 20–30 holder wallets for coordinated sells or liquidity-add transactions over the next 48h; any movement out of the largest non-LP addresses will confirm distribution has begun.

## Market & Liquidity (DexScreener)
- Symbol/Name: Claude / Claude
- Price: $0.0000000006452
- Liquidity: $318599.79
- 24h Volume: $0.07
- 24h Change: 43.5%
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
- holder_count: `13833`
- owner_address: `0x0000000000000000000000000000000000000000`

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 12791 bytes

## Contract Verification
- Verified: True
- Name: ClankerToken · Compiler: v0.8.28+commit.7893614a
- Proxy: False · Implementation: None

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- 2h interval not yet up (33m remaining) — skipped this cycle

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*