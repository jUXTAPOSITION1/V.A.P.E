# VIRTUALS PROTOCOL — Attack Surface Map
**Date:** 2026-06-10 18:49 UTC
**Analyst:** V.A.P.E.
**Source:** Code4rena Audit Repo (github.com/code-423n4/2025-04-virtuals-audit)
**Scope:** 82 Solidity files, ~8,200 LOC in core contracts

---

## ARCHITECTURE OVERVIEW

```
Virtuals Protocol Architecture
================================

┌─────────────────────────────────────────────────────────┐
│                    AgentNftV2                            │
│  (Core NFT registry — identity, validators, LP refs)    │
│  INHERITS: CoreRegistry + ValidatorRegistry              │
│  ROLES: DEFAULT_ADMIN, MINTER, VALIDATOR_ADMIN, ADMIN   │
└──────────┬──────────────┬────────────────┬──────────────┘
           │              │                │
    ┌──────▼──────┐ ┌─────▼──────┐  ┌──────▼───────┐
    │ AgentFactory│ │ AgentDAO   │  │ AgentToken   │
    │ V3 / V4    │ │            │  │ (ERC20+Tax)  │
    │ (Launch)   │ │ (Governance)│  │ (Uniswap LP) │
    └──────┬──────┘ └────────────┘  └──────────────┘
           │
    ┌──────▼──────┐
    │ AgentVeToken│
    │ (Staking)   │
    └─────────────┘

┌──────────────────────────────────────────────┐
│           FUN / BONDING CURVE                │
│  Bonding.sol → FFactory → FPair → FRouter   │
│  FERC20 (pump.fun-style bonding tokens)      │
│  Graduates to AgentFactoryV3                 │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│           REWARDS SYSTEM                     │
│  AgentRewardV2 / V3 (inflationary rewards)   │
│  Validator rewards, staker rewards,          │
│  service rewards, protocol rewards           │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│           GENESIS (Launchpad)                │
│  Genesis.sol → FGenesis.sol                  │
│  Crowdsale-style agent launches              │
│  Refund/claim mechanics                      │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│           TAX SYSTEM                         │
│  AgentTax, BondingTax, TBABonus, LPRefund   │
└──────────────────────────────────────────────┘
```

---

## HIGH-VALUE ATTACK SURFACE (Ranked by Risk × Impact)

### 🔴 CRITICAL — Access Control Gaps

**1. AgentNftV2::addValidator() — NO ACCESS CONTROL**
- **File:** `contracts/virtualPersona/AgentNftV2.sol` ~Line 98
- **Code:** `function addValidator(uint256 virtualId, address validator) public {`
- **Vulnerability:** The `public` modifier allows ANY address to add themselves as a validator to any agent. No `onlyRole` or `onlyVirtualDAO` check.
- **Impact:** Unauthorized validator injection → inflated validator scores → reward theft from the validator pool. Manipulation of governance score calculations.
- **C4 Finding:** H-01 (confirmed HIGH)
- **Regression Risk:** If patch only added a role check, check if the `_addValidator` internal function is called from other unprotected paths.

**2. AgentNftV2::setDAO() — Self-replacement risk**
- **File:** `contracts/virtualPersona/AgentNftV2.sol` ~Line 155
- **Code:** `function setDAO(uint256 virtualId, address newDAO) public {`
- **Vulnerability:** Only checks `_msgSender() == virtualInfos[virtualId].dao`. If the DAO is compromised or the DAO contract has a bug, the entire agent can be hijacked.
- **Impact:** Full agent takeover — change token URI, core types, governance.

**3. AgentToken::distributeTaxTokens() — NO ACCESS CONTROL**
- **File:** `contracts/virtualPersona/AgentToken.sol` ~Line 490
- **Code:** `function distributeTaxTokens() external {`
- **Vulnerability:** Any address can call this to force-distribute accumulated tax tokens. No `onlyOwnerOrFactory` check.
- **Impact:** Griefing attack — forces tax distribution before optimal swap timing, potentially at unfavorable prices. Could be used to sandwich the recipient.
- **C4 Likelihood:** Likely a MEDIUM finding.

### 🟡 HIGH — Economic / Logic Vulnerabilities

**4. Bonding::sell() — Price Manipulation**
- **File:** `contracts/fun/Bonding.sol` ~Line 215
- **Vulnerability:** The `sell()` function updates price/volume/mcap data AFTER the swap but uses stale reserves. The pricing uses `reserveA / reserveB` which is integer division and loses precision for low-value tokens.
- **Impact:** Price oracle manipulation affecting graduation threshold. If `newReserveA <= gradThreshold`, it triggers `_openTradingOnUniswap` — an attacker could intentionally crash the reserve to trigger early graduation at unfavorable terms.

**5. Bonding::_openTradingOnUniswap() — Graduation Race**
- **File:** `contracts/fun/Bonding.sol` ~Line 260
- **Vulnerability:** The graduation flow burns all bonding tokens from the pair and creates a new agent token. The `unwrapToken()` function later allows swapping bonding tokens for agent tokens 1:1.
- **Impact:** If graduation happens at a manipulated price, the `agentToken` allocation is set at the wrong ratio. Users who didn't unwrap before graduation could lose value.

**6. AgentFactoryV4::proposeAgent() — Threshold Griefing**
- **File:** `contracts/virtualPersona/AgentFactoryV4.sol` ~Line 108
- **Vulnerability:** Only checks `balanceOf(sender) >= applicationThreshold` at proposal time. If the threshold is later increased, existing proposals still execute at the old threshold.
- **Impact:** Race condition — propose at low threshold, wait for threshold increase, execute at old lower cost.

**7. AgentToken::_autoSwap() — Sandwich Attack Surface**
- **File:** `contracts/virtualPersona/AgentToken.sol` ~Line 365
- **Vulnerability:** Auto-swap triggers on any transfer when tax balance exceeds threshold. The swap goes through Uniswap with `0` slippage (`swapExactTokensForTokensSupportingFeeOnTransferTokens` with `amountOutMin = 0`).
- **Impact:** MEV/sandwich attackers can front-run the auto-swap for guaranteed profit. The tax recipient receives significantly less pair tokens than fair value.

**8. AgentToken::setProjectTaxRates() — Tax Rate INCREASE**
- **File:** `contracts/virtualPersona/AgentToken.sol` ~Line 290
- **Vulnerability:** Comment says "Change the tax rates, subject to only ever decreasing" but the ACTUAL CODE does NOT enforce decreasing. It just sets the new values directly.
- **Impact:** Owner/factory can increase tax rates to 100% buy/sell, effectively rug-pulling holders.
- **C4 Likelihood:** Likely a HIGH finding if not already flagged.

### 🟠 MEDIUM — Logic / State Issues

**9. ValidatorRegistry::_initValidatorScore() — Initial Score Inflation**
- **File:** `contracts/virtualPersona/ValidatorRegistry.sol` ~Line 32
- **Code:** `_baseValidatorScore[validator][virtualId] = _getMaxScore(virtualId);`
- **Vulnerability:** New validators get the maximum possible score on initialization. Combined with the `addValidator` access control gap, anyone can grant themselves max validator score.
- **Impact:** New validators immediately have outsized voting/reward power without any track record.

**10. AgentFactoryV4::_executeApplication() — Custom Token Path**
- **File:** `contracts/virtualPersona/AgentFactoryV4.sol` ~Line 170
- **Vulnerability:** The custom token path (`_applicationToken[id] != address(0)`) creates a new pair and adds liquidity directly, but `isCompatibleToken()` only does try/catch on basic ERC20 methods — doesn't check for malicious token behavior (fee-on-transfer, rebasing, etc.).
- **Impact:** Malicious custom token can drain asset tokens during liquidity addition via fee-on-transfer or rebase manipulation.

**11. Bonding::unwrapToken() — Unchecked TransferFrom**
- **File:** `contracts/fun/Bonding.sol` ~Line 310
- **Vulnerability:** `agentToken.transferFrom(pairAddress, acc, balance)` — the contract must have approval to transfer agent tokens from the pair. If approval wasn't set properly, this silently fails or reverts.
- **Impact:** Users could be unable to unwrap their bonding tokens after graduation.

**12. Genesis — Crowdsale Refund Logic**
- **File:** `contracts/genesis/Genesis.sol`
- **Vulnerability:** Multiple state transitions (not started → started → ended → succeeded/failed) with refund mechanics. Classic crowdsale attack patterns apply:
  - Contributing at the last block to manipulate success/failure threshold
  - Refund griefing if the genesis fails
  - Agent token claim race conditions

---

## ATTACK FLOW MAP

```
Attack Vector 1: Validator Injection → Reward Theft
─────────────────────────────────────
1. Call AgentNftV2::addValidator(virtualId, attackerAddr) [PUBLIC, NO AUTH]
2. Attacker gets _initValidatorScore = maxScore [AUTOMATIC]
3. Attacker now has inflated validator score
4. Validator rewards in AgentRewardV2 are distributed proportional to score
5. Attacker claims outsized rewards from validatorPoolRewards

Attack Vector 2: Tax Rate Rug Pull
─────────────────────────────────
1. Owner or factory calls AgentToken::setProjectTaxRates(10000, 10000)
2. Buy/sell tax set to 100%
3. All trades taxed at 100% — tokens effectively locked
4. Tax tokens auto-swap with 0 slippage → MEV extracts remaining value

Attack Vector 3: Bonding Curve Graduation Manipulation
──────────────────────────────────────────────────────
1. Attacker buys bonding token to pump price
2. Sells large amount to crash reserveA below gradThreshold
3. _openTradingOnUniswap() triggers at manipulated price
4. Agent token deployed with wrong token/asset ratio
5. unwrapToken() users get wrong allocation

Attack Vector 4: Auto-Swap MEV Extraction
─────────────────────────────────────────
1. Monitor mempool for any transfer on taxed AgentToken
2. When tax balance exceeds threshold, auto-swap triggers
3. Front-run the swap (0 slippage = guaranteed profit)
4. Back-run to capture price impact
5. Tax recipient gets significantly less value
```

---

## UNAUDITED / UNDER-REVIEW TARGETS (Priority for further work)

| # | Contract | LOC | Risk Level | Why |
|---|----------|-----|------------|-----|
| 1 | AgentToken.sol | 1063 | 🔴 CRITICAL | Tax logic, autoswap with 0 slippage, distributeTaxTokens no auth |
| 2 | Bonding.sol | 421 | 🔴 CRITICAL | Graduation manipulation, price oracle, unwrap issues |
| 3 | AgentNftV2.sol | 268 | 🔴 CRITICAL | addValidator no auth, validator score inflation |
| 4 | AgentFactoryV4.sol | 552 | 🟡 HIGH | Custom token path, threshold race, no tax-decrease enforcement |
| 5 | AgentRewardV2.sol | 568 | 🟡 HIGH | Reward distribution logic, validator pool |
| 6 | Genesis.sol | 489 | 🟡 HIGH | Crowdsale patterns, refund logic |
| 7 | AgentTax.sol | 290 | 🟠 MEDIUM | Tax calculation edge cases |
| 8 | AgentVeToken.sol | 142 | 🟠 MEDIUM | Staking/unstaking logic |
| 9 | FRouter.sol | 186 | 🟠 MEDIUM | Swap execution, slippage |
| 10 | AgentDAO.sol | 225 | 🟢 LOW | Governance, voting |

---

## NEXT STEPS FOR VAPE

1. **Verify H-01 patch status** — Check if `addValidator` now has access control on mainnet deployment
2. **Deep-dive AgentToken tax logic** — The `setProjectTaxRates` not enforcing "only decreasing" is potentially unfixed
3. **Write Foundry PoCs** for attacks 1-4
4. **Monitor mainnet deployments** for the Bonding contract — graduation manipulation is live-fire ready
5. **Set up cron job** to check immunefi.com for Virtuals Protocol bounty program launch
6. **Submit via security@virtuals.io** if new findings confirmed
