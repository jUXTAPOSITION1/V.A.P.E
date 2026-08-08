# VAPE Proactive HACK Sweep — AS

**Project:** AS Token ($AS)  
**Target:** `0x58e0893DC6d7E875547Bc1f6D034FF443d9F2F52` (chain 137)  
**Date:** 2026-08-08T04:14:45Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (52/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: insufficient source (only partial abstracts) to identify concrete, callable exploit path in deployed contract.

---

## Vulnerability Analysis
**Project Overview**  
AS Token (symbol: AS) is an ERC20 token deployed at `0x58e0893DC6d7E875547Bc1f6D034FF443d9F2F52` on Polygon (chain 137). The contract is a verified, non-proxy `DropERC20` implementation compiled with Solidity 0.8.23 and authored via thirdweb tooling. It uses the standard thirdweb `Drop`, `Permissions`, `PrimarySale`, `PlatformFee`, and `ContractMetadata` extensions to support claim-condition-based token distribution. On-chain data shows ~9.8k holders, ~80% of supply in a Uniswap V3 pool (`0x4321fcffde80510dc2f1e19a99083d23abae4bae`), and the creator address holding ~20%. No official website or social links are present in market or token-security records. Liquidity is low (~$30k USD) with negligible 24h volume.

**Executive Summary**  
SIMULATED ATTACK — EXECUTED PROOF-OF-CONCEPT: Not available this run: no exploit found: insufficient source (only partial abstracts) to identify concrete, callable exploit path in deployed contract.

The provided source consists only of thirdweb interface and extension abstracts (IERC20, Drop, Permissions, Multicall, etc.). No complete `DropERC20` implementation or custom overrides were available, preventing identification of any callable exploit path. No evidence of reentrancy, missing access-control checks, oracle usage, integer issues, or upgrade risks appears in the supplied fragments. The contract follows the standard thirdweb Drop pattern with role-gated claim-condition updates and per-wallet claim limits.

**Access Control**  
The `Permissions` and `PermissionsEnumerable` extensions implement role-based gating (DEFAULT_ADMIN_ROLE and others) with `onlyRole` modifiers and `hasRoleWithSwitch` checks. `Drop.setClaimConditions` and `ContractMetadata.setContractURI` both require the corresponding `_canSet*` virtual functions to return true. No evidence of unprotected public setters or role misconfiguration is visible in the given code.

**Recommended Human Follow-up**  
- Obtain and review the full, untruncated `DropERC20` source (including any custom `_transferTokensOnClaim`, `_collectPriceOnClaim`, and `_canSet*` implementations) to confirm the exact claim logic and fee recipients.  
- Verify that the live deployment’s admin roles are held only by expected multisig or DAO addresses.  
- Confirm the current claim conditions on-chain (via `getClaimConditionById` / `getActiveClaimConditionId`) match the intended distribution schedule.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $30,310

**Positive Signals**
- 9809 holders — reasonably distributed
- Trading 101+ days without a known incident in this scan
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