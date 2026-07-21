# VAPE Proactive HACK Sweep — RISE

**Project:** RISE Token ($RISE)  
**Target:** `0xCFB287565201763743A77c556dcA44A673d0a777` (chain 137)  
**Date:** 2026-07-21T05:56:17Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (70/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
RISE Token (RISE) is an ERC-20 token deployed at 0xCFB287565201763743A77c556dcA44A673d0a777 on Polygon. It implements a UniswapV2-style liquidity pair (0x55e4151499e9dba3a74cc4ba9c711f8bcc1ef565) with ~$5.51 M liquidity and ~34.8 k holders. The contract (RISEToken, v0.8.28, non-proxy) integrates an external `IGSCStorage` contract that controls buy/sell flags, fees, staking, slippage vault, and privileged addresses. Core logic includes dynamic sell fees based on daily price deviation, auto-enabling of buys after holder-count or deflation thresholds, staking-driven liquidity addition/removal, and POL (WMATIC) routing via a swap relay. Creator address is 0x04266e043df2489644b95c90459f9b8b838003f4; no official website or social links are present in the provided data.

**Executive Summary**  
The contract is a complex, storage-gated token with multiple external-call surfaces and price-derived fee logic. No classic reentrancy, integer-overflow, or proxy-storage-collision issues were identified in the supplied source. However, the design concentrates critical control in an external `gscStorage`/`gscStaking` pair, uses LP-reserve pricing for dynamic fees, and contains several privileged paths that can alter trading behavior or extract value. GoPlus flags external calls, consistent with the observed architecture. Overall risk profile warrants caution pending verification of the storage/staking contracts and privileged key management.

**Access Control (Owner / Role Gating)**  
- `Ownable.transferOwnership` is callable by the deployer and can hand over the contract to any address.  
- The majority of privileged operations (`recycle`, `depositToPool`, `externalRemoveLiquidity`, `setBuyLimitForAddress`, etc.) are gated by `_checkGscStaking()`, which requires `msg.sender == IGSCStorage(gscStorage).gscStaking()`. If the staking contract is compromised or misconfigured, these functions become attacker-controlled.  
- `systemAddresses` mapping bypasses the `_dispatchAction` guard in `receive`/`fallback`; any address added here can trigger fund routing without restriction.

**Oracle Manipulation / Price Feed Trust**  
- `getCurrentPrice()` and `_getPolAmountFromGsc()` read reserves directly from the Pancake-style pair via `IPancakePair.getReserves()`.  
- `calculateDynamicSlippage()` uses the ratio of `dailyBasePrice` vs. this spot price to apply 2–32 % sell fees. An attacker who can move the pool price (flash-loan, large swap, or sandwich) can therefore trigger or suppress the dynamic burn/fee path on the next sell.  
- `checkAndResetDailyPrice()` and `updateRealTimePrice()` are called inside `_transfer`, creating a direct on-chain price dependency for fee calculation.

**External Call / Reentrancy Surface**  
- `receive()` / `fallback()` → `_dispatchAction()` performs external calls to `IGSCStaking.handleMain`, multiple `_transferTo` (native ETH sends), and `_call` (which itself calls the router). A reentrancy guard (`_inSwap`) exists only for the swap/liquidity paths; the staking call occurs before state updates in several branches.  
- `ISwapRelay.forwardERC20` / `forwardETH` and `ISlippageFeeVault.swapAndDistribute` are called from multiple points without additional reentrancy protection.  
- GoPlus correctly flags `external_call = 1`.

**Other Observations (No Actionable Finding)**  
- No unbounded loops, proxy upgrade risk, or classic integer-overflow patterns appear in the provided code.  
- The `_transfer` override contains many early returns and fee-skipping conditions (`isExcludedFromFees`, `dailyPoolAddress`, etc.); these are intentional design choices rather than bugs.

**Recommended Human Follow-up**  
1. Verify the deployed `gscStorage` and `gscStaking` contract addresses and their own access-control / upgradeability status.  
2. Confirm that `systemAddresses` and the initial owner key are under trusted control and that ownership has not been transferred.  
3. Review the exact parameters returned by `IGSCStorage` (buy/sell flags, fee vault, slippage settings) on-chain.  
4. Test whether a flash-loan-driven price move can materially alter `calculateDynamicSlippage` outcomes for large sells.  
5. Examine the `ISwapRelay` and `ISlippageFeeVault` implementations for reentrancy or unauthorized fund movement.

**Verdict: CAUTION**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-20] High sell tax 10%
- [-10] Owner not renounced (0x000000000000000000000000000000000000dead) — can still act on the contract
- [note] address has no contract code (EOA or not deployed)

### Positive Signals
- 34818 holders — reasonably distributed
- Deep liquidity ($5,514,189)
- Trading 103+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Static Analysis (Slither)
- Not run this cycle: slither not installed in this environment this run

## Symbolic Testing (Halmos)
- Not run this cycle: halmos not installed in this environment this run

## Static Analysis (Mythril)
- Not run this cycle: mythril (myth) not installed in this environment this run

## Static Analysis (Aderyn)
- Not run this cycle: no scaffolded Foundry project available this run (symbolic testing didn't reach the scaffolding stage)

## Methodology
1. Real keyless recon: GoPlus token security, DexScreener liquidity, Base RPC on-chain presence, DeFiLlama hack-technique correlation, public web search for reputation flags — identical pipeline to every open-source VAPE investigation.
2. Etherscan V2 contract verification + full verified source (when available).
3. Slither static analysis, real tool output, only if pre-installed this run.
4. Halmos bounded symbolic testing against LLM-drafted check_* properties compiled into a scaffolded Foundry project built from that same verified source — only if forge and halmos are both installed this run.
5. Mythril symbolic-execution scan of the deployed bytecode on-chain by address, via the target chain's real public RPC — only if pre-installed this run.
6. Aderyn static AST analysis of that same scaffolded Foundry project — only if pre-installed this run and step 4's scaffolding stage was reached.
7. A frontier-tier LLM reads the actual verified source and reasons per vulnerability class — this is VAPE's deepest automated pass, still followed by the human-verification list above.
8. White-hat only: read-only analysis, no exploitation attempted.

*This report was generated proactively by VAPE's own daily HACK sweep (agents/hack_sweep.py) — not a paid engagement.*