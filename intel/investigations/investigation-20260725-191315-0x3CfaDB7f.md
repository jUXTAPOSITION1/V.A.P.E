<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — NTFS

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![13/100](https://img.shields.io/badge/SAFETY_SCORE-13%2F100-FB856C?style=flat-square)

- **Target:** `0x3CfaDB7f1fD7C786a98c3Fa37131ff1537E554C5`
- **Chain:** 8453 (Base)
- **Date:** 2026-07-25T19:13:15Z
- **Verdict:** REJECT (13/100)

---

## Executive Summary
**Overall: REJECT (13/100)**

| Category | Score |
|---|---|
| Security & Contract Risk | 88/100 |
| Tokenomics & Track Record | 95/100 |
| Holder Distribution & Liquidity | 70/100 |
| Transparency & Provenance | 60/100 |

*Category scores are a derived readability aid (net effect of that category's own flags against a 100 baseline) — the Overall score above, computed by the full scoring engine, is the authoritative verdict.*

## Project Overview & Narrative
- Not available this cycle (web search/LLM path unavailable, or no relevant results found) — absence noted, not fabricated.

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: USDC (0x8dB2be2bf9C90b7c7B11Af0F46bcafe4FAb6Dd88) — CAUTION 68/100 — likely the same serial campaign
- [-15] Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-5] Pair 26.0 days old — under a month, still unproven
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

## Positive Signals (real legitimacy evidence found)
- 30396 holders — reasonably distributed
- Custom verified source (not a mass-produced factory template)

## Risk Breakdown by Category
**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)
  - [-12] Mintable supply (dilution risk)
**Tokenomics & Track Record** — 1 flag(s), 0 positive signal(s)
  - [-5] Pair 26.0 days old — under a month, still unproven
**Holder Distribution & Liquidity** — 2 flag(s), 1 positive signal(s)
  - [-15] Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
  - [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
  - (positive) 30396 holders — reasonably distributed
**Transparency & Provenance** — 2 flag(s), 1 positive signal(s)
  - [-30] Same deployer has a prior CAUTION/REJECT verdict on record: USDC (0x8dB2be2bf9C90b7c7B11Af0F46bcafe4FAb6Dd88) — CAUTION 68/100 — likely the same serial campaign
  - [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
  - (positive) Custom verified source (not a mass-produced factory template)

## Expert Assessment
- Agrees with the verdict above:

The evidence paints NTFS as a low-effort Base-chain token (DropERC20 template, 44-byte verified contract) whose branding ("National Trust Fund System") deliberately echoes official-sounding financial language while exhibiting classic serial-campaign markers. The same deployer previously launched a token literally named USDC at a different address that already drew a CAUTION verdict; both share the mintable flag, zero locked liquidity, and extreme holder concentration (top 9 wallets = 100 % supply). The 30 k holder count is therefore misleading—distribution is illusory when control remains centralized and the deployer can still mint or drain the ~$317 k liquidity pool at will. Near-zero 24 h volume after only 26 days further indicates the holder base is likely bot-driven or airdrop-farmed rather than organic demand. Nothing in the on-chain or market data contradicts the pattern of repeated, lightly disguised extraction plays.

The rule-based score correctly weights the mintable + prior-campaign + concentration + unlocked LP cluster as decisive red flags. It slightly overweights the raw holder number without discounting the concentration data that directly negates it, but this does not change the overall risk picture.

Next step: pull the full transaction history of the deployer (0x address that created both the NTFS and the prior USDC contracts) and map every token it has launched, including any liquidity-add/remove events and recipient wallets of minted supply.

## Market & Liquidity (DexScreener)
- Symbol/Name: NTFS / National Trust Fund System
- Price: $0.00003728
- Liquidity: $316931.53
- 24h Volume: $0.01
- 24h Change: 0.48%
- DEX: uniswap

## Project Links (as declared on DexScreener)
- No official website/social links declared on this token's DexScreener listing.

## Tokenomics (CoinGecko, address-verified)
- Not available this cycle (CoinGecko does not track this exact contract address, or the token isn't listed there yet) — absence noted, not penalized.

## Token Security (GoPlus)
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `0`
- hidden_owner: `0`
- transfer_pausable: `0`
- holder_count: `30396`

## Holder Distribution & Liquidity Lock (GoPlus)
- Top 9 non-LP/burn holders control 100.0% of supply
- 0.0% of tracked liquidity-pool tokens are locked (across 2 LP holder(s))

## On-chain Presence (Base RPC)
- Is contract: True
- Code size: 44 bytes

## Contract Verification
- Verified: True
- Name: DropERC20 · Compiler: v0.8.23+commit.f704f362
- Proxy: False · Implementation: None
- Notable functions found in verified source (informational, not scored): __ERC20Burnable_init, __ERC20Burnable_init_unchained, _burn, _mint, burn, burnFrom, withdraw
- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).

## Threat Correlation
- No correlation to recent exploit techniques.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- DefiLlama does not price this token (obscure / not yet on the oracle) — absence noted, not penalized.

## Data Agent Intel (VAPE's own x402 spend)
- DATA AGENT hired 2 of VAPE's own $0.01 x402 market-data offerings against this token (real USDC on Base, 2 settled, $0.02 total):
  - **stablecoins** (settled, cdp) — count=50; stablecoins: 25 item(s)
  - **stablecoins** (settled, vapor) — count=50; stablecoins: 25 item(s)

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

## Sources & Verification Links
- Block explorer: https://basescan.org/address/0x3CfaDB7f1fD7C786a98c3Fa37131ff1537E554C5
- DexScreener pair: https://dexscreener.com/base/0x4aa8873fcdc1ee23a083cb7ec6d600fba1a001ab3a67e802900c2f9ac5fe46bc
- GoPlus Security, Etherscan V2 API, and DeFiLlama were queried directly for the sections above; this list only covers human-clickable pages for independent re-verification.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*