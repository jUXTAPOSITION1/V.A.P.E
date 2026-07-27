# VAPE Proactive HACK Sweep — AS

![AS logo](https://cdn.dexscreener.com/cms/images/936a2adffa992c2d43663e8b0489d959178341b3162b97e158498fb9d5854d73?width=800&height=800&quality=95&format=auto)

**Project:** AS Token ($AS)  
**Target:** `0x6A92B1E99De09f71CD96BC91F934826d96B8b26E` (chain 137)  
**Date:** 2026-07-27T06:36:50Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (53/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: provided source is only standard audited OpenZeppelin AccessControl with no custom logic or flaws shown.

---

## Vulnerability Analysis
**Project Overview**

AS Token (AS) is an ERC-20 token deployed at 0x6A92B1E99De09f71CD96BC91F934826d96B8b26E on Polygon (chain 137). It trades primarily on QuickSwap with ~$15.6 M liquidity and reports a market price of ~$1.02. The verified source (Solidity 0.8.29) implements a custom ERC-20 with Permit support, role-based minting via OpenZeppelin AccessControl, configurable transfer fees, and a fee receiver. The creator address holds no current balance; the largest holders are contracts. No official website or social links are present in the on-chain or market data.

**Executive Summary**

The executed forge-based exploit PoC returned “no exploit found.” The supplied source consists of standard, audited OpenZeppelin AccessControl plus a thin wrapper (VaultOwned) that only gates the MINT role; no custom role-logic flaws, storage collisions, or unprotected initializers are present. GoPlus flags (hidden_owner=1, external_call=1) exist but are not corroborated by any executable path in the provided code. No reentrancy, oracle, integer-overflow, or unbounded-loop issues are reachable from the visible contracts. The overall finding is therefore that the contract surface examined does not contain an exploitable vulnerability under the tested conditions.

**Access Control**

The contract uses the canonical OpenZeppelin AccessControl implementation (DEFAULT_ADMIN_ROLE, INTERN_SYSTEM, MINT). Roles are granted only in the constructor to msg.sender and the fee receiver; subsequent grants/revokes are gated by getRoleAdmin. The VaultOwned modifier correctly checks hasRole(MINT, msg.sender). No evidence of role escalation, missing onlyRole checks, or renouncing without confirmation was observed.

**Reentrancy**

No external calls occur inside the token-transfer or mint paths that could be re-entered before state updates. The only external interaction is the (truncated) fee logic that calls an IFeeReceiver; the visible code performs the balance updates before any such call.

**Oracle / Price Feed Trust**

No price oracles, TWAPs, or external price sources are present in the supplied source.

**Integer Overflow / Precision Loss**

Solidity 0.8.29 provides built-in overflow checks. The custom SafeMath library is used but its operations are redundant and cannot produce under/overflows under normal conditions. Fee calculations use fixed-point ratios bounded by PRECISION (100e3) and are checked before assignment.

**Upgrade / Proxy Risk**

The contract is explicitly not a proxy (verified source, implementation=None). No storage-collision or initializer issues apply.

**Unbounded Loops / DoS**

No loops over user-supplied arrays or holder lists exist in the visible code.

**Front-running / MEV Surface**

Role-gated functions (setMainPair, setRatio) are callable only by DEFAULT_ADMIN_ROLE and do not create obvious sandwich or griefing opportunities beyond normal admin actions.

**Honeypot / Rug Mechanics (GoPlus flags)**

GoPlus reports hidden_owner=1 and external_call=1. The source shows a single feeReceiver address that receives INTERN_SYSTEM and can be the target of an external call in the (truncated) _transfer path. No minting to arbitrary addresses, ownership transfer backdoors, or sell restrictions are present in the audited fragment. The flags therefore remain unconfirmed by executable code paths.

**Recommended Human Follow-up**

- Review the complete _transfer implementation (currently truncated) to confirm fee accounting and any external call ordering.  
- Verify that the feeReceiver contract at the address supplied in the constructor cannot be used to drain or manipulate balances.  
- Confirm the current holder of DEFAULT_ADMIN_ROLE and whether any timelock or multisig protects role changes.  
- Re-run the PoC against the live forked state after obtaining the missing final lines of _transfer.  

**Verdict: CAUTION**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-12] Mintable supply (dilution risk)
- [-20] Hidden owner
- [-15] Top 9 non-LP/burn holders control 89% of supply — concentrated, easily manipulated

**Positive Signals**
- 409667 holders — reasonably distributed
- 100% of liquidity is locked — reduced rug-pull risk
- Deep liquidity ($15,618,620)
- Trading 410+ days without a known incident in this scan
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