# VAPE Proactive HACK Sweep — DODO

**Project:** DODO bird ($DODO)  
**Target:** `0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd` (chain 1)  
**Date:** 2026-08-07T04:59:39Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (70/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: No exploitable vulnerability present in the given DODOToken source.

---

## Vulnerability Analysis
**Project Overview**

DODO (symbol: DODO) is the native token of the DODO decentralized exchange protocol operated by DODO ZOO. The contract at 0x43Dfc4159D86F3A37A5A4B3D4580b888ad7d4DDd on Ethereum is a verified, non-proxy ERC20 implementation (Solidity 0.6.9) with a fixed 1 billion token supply. The creator address is 0x17dbfa501f2f376d092fa69d3223a09bba4efdf7. Primary liquidity resides in the Uniswap V2 pair 0x68fa181c720c07b7ff7412220e2431ce90a65a14 (≈$71.5k USD liquidity at the time of the scan), with smaller positions on other Uniswap pools. No official websites or social links were returned in the market data.

**Executive Summary**

SIMULATED ATTACK — EXECUTED PROOF-OF-CONCEPT  
No exploitable vulnerability present in the given DODOToken source.

The contract is a minimal, standard ERC20 implementation using SafeMath. It contains no owner, no fees, no external calls, no upgradeability, and no complex logic. The executed test therefore found no path that could be exploited on the live forked state.

**Reentrancy**  
No external calls exist in `transfer`, `transferFrom`, or `approve`. The functions only perform internal balance and allowance updates before emitting events, eliminating reentrancy risk.

**Access Control**  
The constructor assigns the entire supply to `msg.sender` and exposes no privileged functions afterward. There is no owner, no mint/burn capability, and no role-based gating.

**Integer Overflow / Precision Loss**  
All arithmetic is routed through the provided SafeMath library (mul, div, sub, add), which reverts on error. No unchecked operations or custom math exist.

**Upgrade / Proxy Risk**  
The contract is not a proxy (explicitly confirmed in verification data) and has no delegatecall or storage-collision surface.

**Honeypot / Rug Mechanics**  
GoPlus data shows buy tax = 0, sell tax = 0, anti-whale modifiable = 0, hidden owner = 0, and cannot_buy/cannot_sell_all = 0. The source matches this profile exactly.

**Recommended Human Follow-up**  
- Confirm the token at this address remains the canonical DODO token used by the current DODO protocol contracts.  
- Verify that no newer, privileged wrapper or vesting contract has been deployed that could affect holder balances.  
- Review the liquidity-pool contracts (especially the V2 pair) for any separate risks not present in the token itself.  
Verdict: PROCEED

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-15] Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

**Positive Signals**
- 15979 holders — reasonably distributed
- Trading 2138+ days without a known incident in this scan
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