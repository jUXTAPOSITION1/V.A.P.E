# VAPE Proactive HACK Sweep — V4

![V4 logo](https://cdn.dexscreener.com/cms/images/7tbr1OIigjxUz65m?width=800&height=800&quality=95&format=auto)

**Project:** Programmable ($V4) — https://programmable.family/ · https://github.com/0xprogrammable · https://x.com/0xProgrammable  
**Target:** `0x7987f03462200b3D8A072E02C89A8A41dCB124EE` (chain 1)  
**Date:** 2026-08-04T05:54:40Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (65/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: insufficient source (BaseUERC20 + any mutable functions) to identify a concrete, callable exploit path.

---

## Vulnerability Analysis
**Project Overview**

The target at `0x7987f03462200b3D8A072E02C89A8A41dCB124EE` is the "Programmable" (symbol V4) ERC-20 token on Ethereum mainnet. It was deployed via `UERC20Factory`, mints its entire supply to a recipient at construction, and currently holds liquidity across several Uniswap V4 pools (largest ~$59k). The project lists https://programmable.family/ and https://x.com/0xProgrammable as official links; the contract is verified as `UERC20` (Solidity 0.8.28, non-proxy).

**Executive Summary**

SIMULATED ATTACK — EXECUTED PROOF-OF-CONCEPT: no exploit found — insufficient source (BaseUERC20 + any mutable functions) to identify a concrete, callable exploit path.

The provided source contains only the `UERC20` constructor (which reads parameters from the factory and performs a single `_mint`) and supporting libraries. No state-changing functions beyond construction are visible, and the inherited `BaseUERC20` implementation is absent. Consequently, no reentrancy, access-control, oracle, precision, upgrade, unbounded-loop, or front-running vectors can be confirmed or refuted from the given artifacts. GoPlus flags are all benign (no buy tax, anti-whale disabled, ownership not reclaimable). No static-analysis or symbolic-execution results were produced in this run.

**Recommended Human Follow-up**
- Obtain and review the full `BaseUERC20` source (especially any `transfer`, `approve`, `burn`, or role-gated functions).
- Confirm whether the factory or any other contract retains mint/ownership rights after deployment.
- Manually inspect the largest Uniswap V4 pool (`0xd9ca22573437a06a12d5c757b151aa1a76265c1dfdde4b76507233d7ad2b6df0`) for liquidity concentration or withdrawal mechanics.
- Verify that the on-chain bytecode matches the published constructor parameters for the reported creator address.

**PROCEED** — no exploitable path identified from available data; further review of the missing base contract is the only remaining item before relying on this assessment.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Pair 7.3 days old — under two weeks, no track record yet
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

**Positive Signals**
- 2210 holders — reasonably distributed
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