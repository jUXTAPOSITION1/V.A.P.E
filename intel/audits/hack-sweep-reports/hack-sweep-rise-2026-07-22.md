# VAPE Proactive HACK Sweep — RISE

**Project:** RISE TOKEN ($RISE)  
**Target:** `0x431F2f58Ab87D9Fe8aCeF48b17e43A0f8d7e1eB2` (chain 137)  
**Date:** 2026-07-22T05:55:18Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (63/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
RISE TOKEN (symbol: RISE) is an ERC-20 token deployed at `0x431F2f58Ab87D9Fe8aCeF48b17e43A0f8d7e1eB2` on Polygon (chain 137). It is a verified `DropERC20` contract from the thirdweb framework (Solidity 0.8.23), using the `Drop`, `PermissionsEnumerable`, `PrimarySale`, `PlatformFee`, and `ContractMetadata` extensions. The token uses a multi-phase claim-condition system for distribution. It has ~28.7k holders, with the top two addresses (Uniswap V3 pool `0x03e01022f0f0a5ddfc080261de876a49e2851262` and creator `0xcbf0e9ccb0b1f6a0edc098c156259739798e8b4d`) controlling >99.6% of supply. Liquidity is thin (~$157k on Uniswap V3, 0.3% fee) with negligible 24h volume.

**Executive Summary**  
The contract is a standard thirdweb `DropERC20` implementation. No reentrancy, access-control bypass, oracle, integer-overflow, proxy-upgrade, or unbounded-loop issues are present in the supplied source. GoPlus flags no buy/sell restrictions, hidden owner, or modifiable taxes. The only material observations are (1) extreme holder concentration and (2) the inherent admin-controlled nature of claim conditions, both expected for this contract pattern. No evidence of honeypot or rug mechanics.

**Access Control**  
The contract inherits `PermissionsEnumerable` and `Permissions`. All privileged functions (`setClaimConditions`, `setContractURI`, `setPrimarySaleRecipient`, `setPlatformFeeInfo`, etc.) are gated behind `_canSet*` virtual functions that resolve to role checks (typically `DEFAULT_ADMIN_ROLE`). Role management follows the standard OpenZeppelin-style pattern with proper `onlyRole` and `hasRoleWithSwitch` modifiers. No unauthorized paths or role-escalation vectors are visible.

**Reentrancy**  
`claim` performs state updates (`supplyClaimed`, `supplyClaimedByWallet`) before external calls (`_collectPriceOnClaim`, `_transferTokensOnClaim`). The thirdweb `Drop` base follows checks-effects-interactions ordering. No payable fallback or external call before state changes exists in the provided code.

**Unbounded Loops / DoS**  
`setClaimConditions` iterates over the supplied `_conditions` array and performs bounded deletions of old phases. `getActiveClaimConditionId` and role-enumeration helpers iterate over a small, admin-controlled number of phases or members. No attacker-controlled unbounded loops are present.

**Other Classes**  
- No oracles or price feeds.  
- No proxy / upgradeable storage layout.  
- No integer-overflow or precision-loss patterns beyond standard Solidity 0.8 checked arithmetic.  
- No front-running or MEV surface beyond normal claim-condition timing (expected for a drop contract).  
- GoPlus and Dexscreener data show zero buy/sell taxes and no hidden-owner or anti-whale flags.

**Recommended Human Follow-up**  
1. Verify the exact `_canSetClaimConditions`, `_canSetPrimarySaleRecipient`, and `_canSetPlatformFeeInfo` implementations in the final `DropERC20` bytecode to confirm they are restricted to `DEFAULT_ADMIN_ROLE`.  
2. Confirm the current admin address(es) and whether the role has been renounced.  
3. Review the active claim condition(s) on-chain (especially `merkleRoot`, `pricePerToken`, and `maxClaimableSupply`) before any large purchase.  
4. Monitor the creator wallet (`0xcbf0e9cc…`) for large transfers given its 22.87% holding.

**Verdict: PROCEED**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-12] Mintable supply (dilution risk)
- [-15] Pair only 2.8 days old (extreme fresh-launch risk)
- [note] address has no contract code (EOA or not deployed)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

### Positive Signals
- 28695 holders — reasonably distributed
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