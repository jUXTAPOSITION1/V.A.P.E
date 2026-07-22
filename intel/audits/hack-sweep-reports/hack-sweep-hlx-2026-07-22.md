# VAPE Proactive HACK Sweep — HLX

**Project:** Helix Token ($HLX)  
**Target:** `0x28D4e499C4CdE621e1Cea7c9CBf9D43bf75a9525` (chain 1)  
**Date:** 2026-07-22T05:55:36Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (70/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
HelixToken (HLX) is a minimal ERC-20 token deployed at `0x28D4e499C4CdE621e1Cea7c9CBf9D43bf75a9525` on Ethereum. Its verified source consists solely of the standard OpenZeppelin ERC20 implementation plus a constructor that mints the entire 100 billion token supply to `msg.sender`. The creator address (`0x71eba6651d6d889442c90d5276575b557bd705b3`) currently holds <0.001 % of supply. Liquidity exists on Uniswap V3 (two pools) and Uniswap V4 (two pools) with no taxes, no ownership controls, and no external calls present in the contract.

**Executive Summary**  
The contract contains no custom logic beyond the OpenZeppelin ERC20 base. All requested vulnerability classes were examined against the actual source; none are present. GoPlus token-security data corroborates the absence of hidden ownership, modifiable fees, or transfer restrictions. The token can be considered a plain, non-upgradable ERC-20 with no on-chain attack surface.

**Reentrancy**  
No external calls exist in `_transfer`, `_update`, `_mint`, or `_approve`. The standard OZ implementation therefore cannot be re-entered.

**Access Control (owner/role gating)**  
The contract defines no owner, no roles, and no privileged functions. After deployment the token is fully decentralized.

**Oracle Manipulation / Price Feed Trust**  
No oracles or price feeds are referenced.

**Integer Overflow / Precision Loss**  
Solidity 0.8.24 provides built-in overflow checks. All arithmetic in `_update` uses `unchecked` blocks only after explicit bounds checks that guarantee no overflow is possible.

**Upgrade / Proxy Risk**  
Etherscan verification explicitly marks the contract as “proxy: False” and the source contains no proxy or initializer patterns.

**Unbounded Loops / DoS**  
No loops of any kind are present in the contract.

**Front-running / MEV Surface**  
No functions expose ordering-dependent state changes beyond ordinary ERC-20 transfers and approvals.

**Honeypot / Rug Mechanics**  
GoPlus flags confirm `anti_whale_modifiable=0`, `buy_tax=0`, `hidden_owner=0`, `can_take_back_ownership=0`. The source matches these flags exactly.

**Recommended Human Follow-up**  
- Verify that the two largest holders (`0xf166767f064cabc8ef6548fbbe8f8f1554fa4f9f` and `0x19022e81d4f505782bfef6436e37d9e3b9ba0028`) are known liquidity or vesting contracts rather than single-entity cold wallets.  
- Confirm the current Uniswap V3/V4 pool configurations match the liquidity figures reported by DexScreener before relying on market-depth assumptions.

**PROCEED**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-8] Low holder count (159)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default
- [capped at 70] Only 1 positive legitimacy signal(s) found — score capped even though few explicit red flags triggered

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