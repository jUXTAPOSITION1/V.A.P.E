# VAPE Proactive HACK Sweep — AIPF

**Project:** AI Powered Finance ($AIPF)  
**Target:** `0xE5D66322db2922dA6f8cc878d56430b1585f351F` (chain 137)  
**Date:** 2026-08-02T06:08:35Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (62/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: insufficient contract source (only partial base extensions shown; no DropERC20 impl or exploitable entrypoint visible)

---

## Vulnerability Analysis
**Project Overview**  
The contract at 0xE5D66322db2922dA6f8cc878d56430b1585f351F on Polygon (chain 137) is the verified DropERC20 implementation “AI Powered Finance” (symbol AIPF). It was deployed with the thirdweb DropERC20 template (Solidity 0.8.23) and holds a Uniswap V3 liquidity pool at 0x14eb5a91165f21922d314dd728219d9569ea0f47 containing roughly $116 k USD. The creator (0x46dd5eea1cd2dac0a248730d60a65370bc7d7c28) retains ~19.8 % of the supply; the pool itself holds ~80 %. No official website or social accounts are recorded in the on-chain or market data.

**Executive Summary**  
The simulated attack PoC returned “no exploit found: insufficient contract source (only partial base extensions shown; no DropERC20 impl or exploitable entrypoint visible)”. All analysis below is therefore limited to the supplied thirdweb extension fragments. No concrete, executable attack path was demonstrated against the live forked state.

**Access Control (Permissions / Roles)**  
The supplied Permissions and PermissionsEnumerable contracts implement standard role-based gating (`DEFAULT_ADMIN_ROLE`, `onlyRole` modifier, `hasRoleWithSwitch`). Role changes emit events and are protected by admin-role checks. No missing or mis-configured modifiers are visible in the provided fragments. The `Drop.setClaimConditions` function correctly requires `_canSetClaimConditions` (implemented in the missing DropERC20 body).

**Drop / Claim Mechanics**  
The `Drop` base exposes `claim`, `verifyClaim`, `setClaimConditions`, and Merkle-proof allow-listing. All critical state updates (supplyClaimed, supplyClaimedByWallet) occur after the price-collection and transfer hooks. Because the concrete `_collectPriceOnClaim` and `_transferTokensOnClaim` implementations are absent, reentrancy or price-manipulation vectors cannot be confirmed or ruled out from the given source.

**Upgrade / Proxy Risk**  
CONTRACT VERIFICATION explicitly states `proxy: False`. No proxy or initializer patterns appear in the supplied code.

**Integer Overflow / Precision**  
Solidity 0.8.23 is used; arithmetic is checked by default. No custom math libraries that could introduce precision loss are present in the fragments.

**Unbounded Loops / DoS**  
View functions such as `getRoleMemberCount` and `getRoleMember` iterate over role-member arrays. These are read-only and therefore only a theoretical gas-DoS vector for off-chain indexers, not an on-chain exploit.

**Front-Running / MEV Surface**  
`setClaimConditions` and `claim` are public and permissioned only by roles or Merkle proofs. No obvious sandwich or griefing vectors are identifiable without the full claim-condition storage layout.

**Honeypot / Rug Mechanics**  
GoPlus data shows zero buy/sell tax and an unlocked creator balance of ~19.8 %. Liquidity is modest (~$116 k) and 24 h volume is near zero. These facts are consistent with a low-liquidity token but do not constitute a proven honeypot from the supplied data.

**Recommended Human Follow-up**  
1. Obtain the complete, verified DropERC20 source (especially the concrete implementations of `_collectPriceOnClaim`, `_transferTokensOnClaim`, and `_canSetClaimConditions`).  
2. Re-run the exploit PoC with the full contract to confirm absence of reentrancy or access-control bypass.  
3. Verify that the active claim condition(s) on-chain match the intended parameters and that the Merkle root (if any) is correctly configured.  
4. Confirm the creator wallet’s operational security and any planned liquidity actions.

**Verdict: CAUTION**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

**Positive Signals**
- 17112 holders — reasonably distributed
- Trading 122+ days without a known incident in this scan
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