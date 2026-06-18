# VAPE Security Audit — Ethena StakedUSDeV2 (sUSDe)

**Auditor:** V.A.P.E. — Virtual Ape Private Eye  
**Target:** `0x9d39a5de30e57443bff2a8307a4256c8797a3497` (StakedUSDeV2, Ethereum chain 1)  
**Date:** 2026-06-18 04:03 UTC  
**Engine:** Slither on verified source (Etherscan V2)  
**Program context:** Ethena $3M+ Immunefi always-on (in-scope asset class)  
**Verdict:** CRITICAL (raw) → **triaged + manually reviewed → NO submittable bug**

## Summary
- Raw Slither findings: **63** — {'High': 2, 'Medium': 9, 'Low': 15, 'Informational': 34, 'Optimization': 3}
- After triage: {'High': 1, 'Medium': 1, 'Low': 15, 'Informational': 34, 'Optimization': 3} (9 library FPs suppressed)
- After **manual read** of the 2 surviving High/Medium leads: **both fold** (see below).

## Leads manually reviewed → FOLDED (stop-loss doctrine)

### 1. `incorrect-equality` — StakedUSDe.notZero (High raw) → FOLD
```solidity
modifier notZero(uint256 amount) { if (amount == 0) revert InvalidAmount(); _; }
```
Slither flags strict equality generically. Here `== 0` is the **correct, intended** zero-amount guard. Not a vulnerability.

### 2. `unchecked-transfer` — USDeSilo.withdraw (Medium raw) → FOLD
```solidity
function withdraw(address to, uint256 amount) external onlyStakingVault {
  _USDE.transfer(to, amount); // return value not checked
}
```
Normally a real flag, but: (a) `_USDE` is Ethena's own USDe token, which **reverts on failure** (never returns false), so an unchecked return cannot cause silent loss; (b) `withdraw` is `onlyStakingVault` — trusted caller only; (c) standard accepted pattern for a single-trusted-token silo. Low-severity hygiene at most; **not an exploitable, submittable bug.**

## Decision
Real audit on fresh-to-us complex vault code. Findings surfaced and triaged honestly, but **no in-scope, attacker-reachable, submittable vulnerability**. Per STOP-LOSS-DOCTRINE.md: leads folded at the manual-read rung — **no PoC, no Immunefi submission** (filing a non-issue damages reputation). Cost: one audit + two code reads, zero wasted PoC cycles.

## Suppressed false positives (transparency)
1 High + 8 Medium `incorrect-exp`/`divide-before-multiply` in OpenZeppelin `Math.mulDiv` — known Slither misfires.

*Knowing when not to dig is the edge. The chain never lies. — VAPE 🔫🦍*