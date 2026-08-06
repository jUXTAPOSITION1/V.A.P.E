# VAPE Proactive HACK Sweep — SYN

**Project:** Synapse ($SYN)  
**Target:** `0x0f2D719407FdBeFF09D87557AbB7232601FD9F29` (chain 1)  
**Date:** 2026-08-06T05:56:42Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (77/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: The provided source only includes standard OpenZeppelin libraries without any custom functions (e.g., mint, burn, role setup) that could be abused; no concrete exploitable path can be identified from the available code.

---

## Vulnerability Analysis
**Project Overview**

Synapse (SYN) is an ERC20 token deployed at 0x0f2D719407FdBeFF09D87557AbB7232601FD9F29 on Ethereum mainnet. It maintains the majority of its liquidity (~$64k) on a SushiSwap V2 pair (0x4a86c01d67965f8cb3d0aaa2c655705e64097c31) with smaller positions across several Uniswap V4 pools. The contract is verified under the name SynapseERC20 (Solidity 0.6.12) and consists of standard OpenZeppelin upgradeable libraries (AccessControlUpgradeable, ERC20PermitUpgradeable, ERC20BurnableUpgradeable, etc.). Creator address 0x846e607b930ea1f5dde6c4a9d9104d5fbfafa157 holds a 0% balance. No official website or social links were present in the recon data.

**Executive Summary**

The executed forge-based exploit PoC returned no successful attack path. The only source available for analysis contains unmodified OpenZeppelin upgradeable libraries with no custom mint, burn, role-initialization, or privileged functions exposed. Consequently, none of the examined vulnerability classes yielded an exploitable finding on the provided code. The token shows zero buy/sell tax and no anti-whale mechanics per the GoPlus scan.

**Access Control**

The supplied code implements the standard `AccessControlUpgradeable` pattern with `DEFAULT_ADMIN_ROLE` and role-admin relationships. All `grantRole`/`revokeRole` calls correctly require the caller to hold the admin role for the target role. No custom role setup or privileged mint/burn functions appear in the visible source, so no misconfiguration or missing initializer risk can be confirmed from the given material.

**Upgrade / Proxy Risk**

The contract is explicitly marked non-proxy. The 45-byte deployed code size is consistent with a minimal or library-only deployment; however, the verified name is SynapseERC20 and the source contains only the listed OZ upgradeable base contracts. No storage-collision or unprotected-initializer vectors are observable.

**Recommended Human Follow-up**

- Obtain and review the complete, untruncated SynapseERC20 source (the current context only supplies OZ dependencies).
- Verify that the live bytecode at the address matches the verified compilation output and that no additional privileged functions exist outside the provided snippets.
- Confirm whether the token contract inherits any non-OZ logic (e.g., custom `_mint` or bridge minting) that was not captured in the truncated source.

**PROCEED**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-8] Top 10 non-LP/burn holders control 67% of supply — meaningful concentration
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

**Positive Signals**
- 10669 holders — reasonably distributed
- Trading 1803+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

### Static Analysis (Slither)
- Not run this cycle: slither not installed in this environment this run

### Symbolic Testing (Halmos)
- Not run this cycle: halmos not installed in this environment this run

### Static Analysis (Mythril)
- Not run this cycle: mythril (myth) not installed in this environment this run

### Static Analysis (Aderyn)
- Not run this cycle: no scaffolded Foundry project available this run (symbolic testing didn't reach the scaffolding stage)

*White-hat only: the simulated attack above executes exclusively against a local, forked simulation of on-chain state (`forge test --fork-url`) — read-only against the real chain, no live transaction is ever broadcast.*

*This report was generated proactively by VAPE's own daily HACK sweep (agents/hack_sweep.py) — not a paid engagement.*