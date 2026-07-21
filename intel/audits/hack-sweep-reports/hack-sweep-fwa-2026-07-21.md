# VAPE Proactive HACK Sweep — FWA

![FWA logo](https://cdn.dexscreener.com/cms/images/YEFggtEx_Tq-hpge?width=800&height=800&quality=95&format=auto)

**Project:** Fake World Assets ($FWA) — https://fwa.fun · https://fwa.fun/docs · https://x.com/token_works  
**Target:** `0xa0Df17B5aC76ABaBA36E1450E2cbCd18A620C845` (chain 1)  
**Date:** 2026-07-21T05:56:55Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** REJECT (30/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
FWAToken (symbol FWA, “Fake World Assets”) is a fixed-supply ERC-20 deployed at `0xa0Df17B5aC76ABaBA36E1450E2cbCd18A620C845` on Ethereum. It bootstraps activity via a single-sided Uniswap V4 ETH/FWA pool (fee 0 / tick spacing 60) whose liquidity is burned to the dead address on launch. The token implements a strict transfer lock that only permits mint/burn, owner, registered distributors, and the V4 PoolManager (via a transient allowance bumped by the hook). It also contains a permissionless, rate-limited `buyback()` that swaps contract ETH for tokens and routes the proceeds. Official links surfaced in market data are https://fwa.fun and https://x.com/token_works. The contract is not a proxy, was compiled with 0.8.30, and its creator (0x019817ad02a31b990433542097be29d97613e8cb) retains a 20 % balance and owner privileges.

**Executive Summary**  
No critical or high-severity vulnerabilities were identified in the supplied source. The contract correctly uses Solady’s `ReentrancyGuard`, `Ownable`, and `SafeTransferLib`; the transfer lock is intentionally restrictive and is bypassed only for the V4 pool path via transient storage. All owner-controlled parameters (distributors, route splits, buyback price floor) are gated and emit events. Integer arithmetic is performed in Solidity ≥0.8 with explicit sum-to-10_000 checks. GoPlus reports no hidden-owner, ownership-renounce, or anti-whale-modifiable flags. The only items a human reviewer should still examine are the yet-to-be-deployed hook and any distributor contracts that will receive `setDistributor` rights.

**Reentrancy**  
`launch()` and `buyback()` are both protected by `nonReentrant`. The `unlockCallback` path only calls trusted V4 contracts and uses `SafeTransferLib.forceSafeTransferETH` for the caller bounty. No reentrancy vectors were found.

**Access Control (owner/role gating)**  
All privileged functions (`setDistributor`, `setPool`, `setRouteSplit`, `setBuybackSqrtPriceLimitX96`, `launch`) are guarded by Solady’s `onlyOwner`. The owner can add arbitrary distributors that bypass the transfer lock; this is by design but should be reviewed once the rewards/claim contracts are known.

**Oracle Manipulation / Price Feed Trust**  
No external price oracles are used. Buybacks are bounded by an owner-set `buybackSqrtPriceLimitX96` that is enforced inside the V4 swap; the limit itself is a protocol constant, not caller-supplied slippage.

**Integer Overflow / Precision Loss**  
All arithmetic occurs under Solidity 0.8.26+. BPS splits are validated to sum exactly to `TOTAL_BIPS` (`setRouteSplit`). Liquidity math uses Uniswap’s `LiquidityAmounts.getLiquidityForAmount1`, which rounds down. No overflow or truncation issues were observed.

**Upgrade / Proxy Risk**  
The contract is not a proxy (Etherscan verification confirms `proxy: False`). Storage layout is flat; no initializer or delegatecall patterns exist.

**Unbounded Loops / DoS**  
No unbounded loops or user-controlled iteration exist in the supplied code.

**Front-running / MEV Surface**  
`buyback()` is permissionless and rate-limited to one call per block, paying a 0.5 % caller bounty. The launch window is protected by transient storage (`tstore(1,1)`) that is only live inside the single `launch()` transaction, preventing front-running of pool initialization. No additional MEV exposure was identified.

**Honeypot / Rug Mechanics**  
GoPlus reports `hidden_owner=0`, `can_take_back_ownership=0`, and `anti_whale_modifiable=0`. The transfer lock is the only mechanism that could appear honeypot-like, but it is explicitly documented and required for the V4 hook to function. Liquidity is burned to `DEAD_ADDRESS` on launch, eliminating the classic rug vector.

**Recommended Human Follow-up**  
- Inspect and verify the hook contract referenced in the constructor.  
- Confirm that `launch()` has been executed exactly once and that the resulting LP NFT is owned by `DEAD_ADDRESS`.  
- Review any contracts that will be granted `isDistributor` rights before they receive large token allocations.  
- Verify that the three route-BPS values continue to sum to 10 000 after any owner updates.

**Verdict: PROCEED**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-10] Owner not renounced (0x019817ad02a31b990433542097be29d97613e8cb) — can still act on the contract
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: FWA (0x47883e389BB6be3650B0C0935b300b50a95fc072) — REJECT 35/100 — likely the same serial campaign
- [-10] Violent 24h move +636% (volatility/manipulation)
- [-10] Pair 4.5 days old — under two weeks, no track record yet
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

### Positive Signals
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