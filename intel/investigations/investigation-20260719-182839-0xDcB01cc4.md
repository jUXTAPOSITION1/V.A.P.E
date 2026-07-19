<img src="https://raw.githubusercontent.com/jUXTAPOSITION1/V.A.P.E/main/docs/assets/vape-avatar.jpg" width="56" height="56" align="left" style="border-radius:10px;margin-right:14px" alt="VAPE" />

# Investigation — YLD

![autonomous system](https://img.shields.io/badge/VAPE-autonomous_system-8B5CF6?style=flat-square)

<br clear="left"/>

![REJECT](https://img.shields.io/badge/VERDICT-REJECT-FB7185?style=flat-square) ![8/100](https://img.shields.io/badge/SAFETY_SCORE-8%2F100-FB7D75?style=flat-square)

- **Target:** `0xDcB01cc464238396E213a6fDd933E36796eAfF9f`
- **Chain:** 1 (Ethereum)
- **Date:** 2026-07-19T18:28:39Z
- **Verdict:** REJECT (8/100)

---

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)
- [-25] Owner can change balances (rug surface)
- [-20] Hidden owner
- [-25] Very low liquidity $1,885 (rug/illiquid)
- [-10] Low liquidity $1,885

## Positive Signals (real legitimacy evidence found)
- 1148 holders — reasonably distributed
- Trading 2048+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)
- DefiLlama has priced this token for 2048+ days — independent longevity corroboration

## Expert Assessment
- Agrees with the verdict above:

AGREE:
The contract is a 2020-era token whose verified source still exposes mint and arbitrary balance-write functions, yet ownership has been renounced (GoPlus owner=None) and the holder base has remained stable at 1,148 addresses with no recorded exploits across more than five years. Current on-chain activity is essentially nil—$0.18 daily volume against $1.9 k liquidity—so the practical attack surface is limited to a dormant rug that holders have already priced in by walking away. The rule-based score therefore correctly treats the combination of mintable supply plus balance-mutation capability as unacceptable regardless of age.

One concrete next step is to diff the verified source against a standard ERC-20 to confirm whether the balance-mutation and mint paths contain any remaining modifiers or are unconditionally callable by anyone.

## Market & Liquidity (DexScreener)
- Symbol/Name: YLD / Yield
- Price: $0.2411
- Liquidity: $1884.98
- 24h Volume: $0.18
- 24h Change: None%
- DEX: uniswap

## Token Security (GoPlus)
- is_honeypot: `0`
- buy_tax: `0`
- sell_tax: `0`
- is_mintable: `1`
- is_proxy: `0`
- can_take_back_ownership: `0`
- owner_change_balance: `1`
- hidden_owner: `1`
- cannot_sell_all: `0`
- transfer_pausable: `0`
- holder_count: `1148`

## On-chain Presence (Ethereum RPC)
- Is contract: True
- Code size: 4215 bytes

## Contract Verification
- Verified: True
- Name: Token · Compiler: v0.5.17+commit.d19bba13
- Proxy: False · Implementation: None

## Threat Correlation
- Owner can alter balances/ownership — no directly matching technique in the 25 most recent tracked incidents, but this remains a structural risk category.

## Public Web Signals
- No unambiguous scam/rug mentions found in the top web search results.

## DefiLlama Cross-Source (independent oracle)
- First DefiLlama price: 2020-12-10T04:08:10Z (2047.6 days ago) — independent longevity source

## Data Agent Intel (VAPE's own x402 spend)
- cdp: data agent only wired for Base (8453) investigations; vapor: data agent only wired for Base (8453) investigations

## Deployer Network (skillforge/memory/graph.py)
- No other tokens from this deployer on record yet.

## Critic Self-Audit (agents/critic.py)
- No structural inconsistencies found — reasons, positive signals, verdict and score all agree with the raw evidence and score()'s own invariants.

---

*V.A.P.E. — investigation conducted with keyless, real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed & price oracle) plus a real web search for public reputation signals.*