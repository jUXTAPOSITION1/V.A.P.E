# VAPE Proactive HACK Sweep — AIPF

**Project:** AI Powered Finance ($AIPF)  
**Target:** `0x15e096f13f04A866C933071C85231ca590b41343` (chain 137)  
**Date:** 2026-08-01T06:04:38Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (62/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: incomplete source (only extensions shown; no DropERC20 impl or exploitable path visible)

---

## Vulnerability Analysis
**Project Overview**  
AI Powered Finance (AIPF) is an ERC-20 token deployed at 0x15e096f13f04A866C933071C85231ca590b41343 on Polygon. It uses the verified thirdweb DropERC20 implementation (v0.8.23) and maintains Uniswap V3 liquidity of ~$266k. The creator (0x6daa79dc6c4941f1df92e1197ae7b4db28b10495) holds ~24.95% of supply; no official website or social links were returned by market-data sources.

**Executive Summary**  
SIMULATED ATTACK — EXECUTED PROOF-OF-CONCEPT: Not available this run — no exploit found: incomplete source (only extensions shown; no DropERC20 impl or exploitable path visible).  

The available code consists solely of thirdweb base extensions (Drop, Permissions, ContractMetadata, PrimarySale, PlatformFee, Multicall). No core DropERC20 implementation, `_transferTokensOnClaim`, `_collectPriceOnClaim`, or `_canSet*` functions were supplied, preventing any concrete exploit construction or confirmation of the claim flow.

**Access Control**  
The Permissions and PermissionsEnumerable extensions implement role-based gating with `DEFAULT_ADMIN_ROLE` and per-role admins. All sensitive functions (`setClaimConditions`, `setContractURI`, `setPrimarySaleRecipient`, `setPlatformFeeInfo`) correctly call the corresponding `_canSet*` virtuals. No missing modifiers or public setters bypassing roles are visible in the provided fragments.

**Upgrade / Proxy Risk**  
The contract is explicitly non-proxy (`proxy: False`). No storage-collision or initializer issues apply.

**Reentrancy, Integer Overflow/Precision Loss, Oracle Manipulation, Unbounded Loops / DoS, Front-Running / MEV**  
No evidence in the supplied source fragments. The Drop logic uses standard Merkle verification and supply accounting; no price oracles, loops over unbounded arrays, or external calls that would enable reentrancy are present in the visible code.

**Honeypot / Rug Mechanics**  
GoPlus data shows zero buy/sell taxes and no “cannot buy / cannot sell all” flags. Creator tokens are not locked, but this is disclosed on-chain and does not constitute a hidden honeypot.

**Recommended Human Follow-up**  
- Obtain and review the complete DropERC20 source (especially `_transferTokensOnClaim`, `_collectPriceOnClaim`, and the three `_canSet*` implementations).  
- Confirm that `claim` cannot mint beyond `maxClaimableSupply` and that `primarySaleRecipient` / platform-fee settings cannot be changed by non-admins.  
- Verify that the active claim condition on-chain matches the intended parameters and that the Merkle root (if any) is correctly set.

**Verdict: CAUTION**  
Human reviewer must still manually verify the missing core implementation and on-chain claim-condition state before any reliance on this report.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

**Positive Signals**
- 9776 holders — reasonably distributed
- Trading 103+ days without a known incident in this scan
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