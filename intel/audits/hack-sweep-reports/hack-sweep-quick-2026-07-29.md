# VAPE Proactive HACK Sweep — QUICK

**Project:** QuickSwap ($QUICK)  
**Target:** `0xB5C064F955D8e7F38fE0460C556a72987494eE17` (chain 137)  
**Date:** 2026-07-29T05:58:13Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (74/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: LLM-drafted exploit test failed to compile
**Drafted exploit test (compile failed or not reached):**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Test.sol";
import "Quick.sol";

contract QuickTest is Test {
    address constant TARGET = 0xB5C064F955D8e7F38fE0460C556a72987494eE17;
    Quick public quick;

    function setUp() public {
        quick = Quick(TARGET);
    }

    function test_exploit_unprotected_function() public {
        // Assuming the deposit function is not properly protected
        // and can be called by anyone
        uint256 amount = 100 * 10**18;
        bytes memory depositData = abi.encode(amount);
        quick.deposit(address(this), depositData);

        // Assert that the balance of the attacker has increased
        assertGt(quick.balanceOf(address(this)), 0);
    }
}
```
```
Unable to resolve imports:
      "forge-std/Test.sol" in "/tmp/vape-foundry-exploit-oldgzkm7/test/Exploit.t.sol"
      "Quick.sol" in "/tmp/vape-foundry-exploit-oldgzkm7/test/Exploit.t.sol"
with remappings:
      
Error: Encountered invalid solc version in test/Exploit.t.sol: No solc version exists that matches the version requirement: ^0.8.0

```

---

## Vulnerability Analysis
**Project Overview**

The target is the QUICK governance token (symbol QUICK) at 0xB5C064F955D8e7F38fE0460C556a72987494eE17 on Polygon (chain 137). It is a verified, non-proxy ERC-20 implementation compiled with Solidity 0.5.16 that also implements vote delegation and checkpointing. The token supports bridge-mediated minting via a single `gateway` address (set at construction) and a `withdraw` burn path. Market data shows ~$104k liquidity on QuickSwap with 53k+ holders; the creator address holds a negligible balance and no privileged owner or modifiable fee mechanics are present.

**Executive Summary**

The simulated exploit PoC did not compile, so no on-chain impact was demonstrated. Static review of the supplied source reveals a mature, narrowly-scoped governance token with no owner, no upgradeability, no external calls in value-moving paths, and conservative 96-bit balance arithmetic. No evidence supports reentrancy, access-control bypass, oracle manipulation, or honeypot behavior. Bounded binary search in `getPriorVotes` and standard permit deadlines are the only surfaces that merit routine human confirmation.

**Access Control**

`deposit` is gated by an immutable `gateway` address supplied in the constructor; no setter exists. `withdraw` and all other mutative functions are permissionless. No role or ownership variables are present after deployment.

**Integer Overflow / Precision Loss**

All balance, allowance, and vote math uses `SafeMath` plus explicit `safe96`/`safe32` wrappers that revert on overflow. Total supply and individual balances are capped at 2^96-1 by design. No unchecked arithmetic or precision-loss patterns appear.

**Unbounded Loops / DoS**

`getPriorVotes` performs a binary search over a per-account checkpoint array. The loop bound equals `numCheckpoints[account]` (uint32), which is practically small; worst-case gas is therefore bounded and cannot be attacker-controlled.

**Front-Running / MEV Surface**

The `permit` implementation includes a `deadline` check and standard EIP-712 replay protection. Classic ERC-20 approval race conditions exist but are well-known and not exacerbated by this contract.

**Recommended Human Follow-up**

- Confirm the live `gateway` address on Polygon matches the intended Polygon bridge contract.
- Verify that the deployed bytecode hash matches the published source (no post-deployment modifications).
- Spot-check that `numCheckpoints` values remain modest in practice and that `getPriorVotes` gas usage stays acceptable for governance front-ends.

**PROCEED** — no exploitable findings surfaced in the verified source or recon data.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-10] Owner not renounced (0xa6fa4fb5f76172d178d61b04b0ecd319c5d1c0aa) — can still act on the contract
- [-8] Top 9 non-LP/burn holders control 69% of supply — meaningful concentration
- [-8] No pair-creation timestamp available — cannot establish track record length

**Positive Signals**
- 53844 holders — reasonably distributed
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