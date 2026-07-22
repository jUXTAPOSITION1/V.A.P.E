# VAPE Proactive HACK Sweep — NES

**Project:** Nesa ($NES)  
**Target:** `0x230f1E241C621d5af670Dad83ebCdd18971E2995` (chain 1)  
**Date:** 2026-07-22T05:55:26Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (77/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
The target is the Nesa (NES) token at 0x230f1E241C621d5af670Dad83ebCdd18971E2995 on Ethereum. It is deployed as a verified TransparentUpgradeableProxy (implementation 0x98b3f0db84ca50a776f7cc340f429198c917f6f1) with ~$1.67 M liquidity across multiple Uniswap V4 pools and 24 h volume exceeding $11 M. The creator address holds a zero balance and the token reports zero buy tax. No official website or social links appear in the provided market or on-chain data.

**Executive Summary**  
The contract is a standard OpenZeppelin TransparentUpgradeableProxy (v4.9.3). No implementation source was supplied, so the token logic, minting, or fee mechanisms cannot be reviewed. The proxy itself contains no custom logic that introduces reentrancy, integer issues, or access-control bypasses. The primary structural risk is upgradeability: the admin can replace the implementation at any time. No GoPlus honeypot/rug signals or recent-hack correlations were present beyond the generic proxy category.

**Access Control (owner/role gating)**  
The proxy correctly implements the transparent pattern: only the account stored in the EIP-1967 admin slot (`0xb5312768…`) can invoke `changeAdmin`, `upgradeTo`, or `upgradeToAndCall`. All other callers are forwarded to the implementation. No deviations from the audited OZ source were observed.

**Upgrade / Proxy Risk**  
The contract is an upgradeable proxy. Storage layout follows EIP-1967 (`_IMPLEMENTATION_SLOT` and `_ADMIN_SLOT`). Because the implementation address is not in the supplied source and no initializer or storage-collision analysis is possible, any upgrade could introduce arbitrary logic. The admin account is not disclosed in the recon data.

**Recommended Human Follow-up**  
1. Obtain and review the verified source of implementation 0x98b3f0db84ca50a776f7cc340f429198c917f6f1.  
2. Identify the current proxy admin and confirm it is a dedicated, non-EOA account (e.g., ProxyAdmin).  
3. Verify that the implementation does not contain privileged minting, fee setters, or back-door functions callable by the same admin.  
4. Confirm the liquidity-pool pair addresses match the expected Uniswap V4 pools reported by GoPlus.

**Verdict: CAUTION**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-8] Upgradeable proxy (verify implementation)
- [-5] Pair 23.5 days old — under a month, still unproven
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

### Positive Signals
- 28620 holders — reasonably distributed
- Deep liquidity ($1,669,135)
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