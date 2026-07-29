# VAPE Proactive HACK Sweep — MegaDoge

**Project:** MegaDoge.Org ($MegaDoge)  
**Target:** `0xCBf4AB00b6Aa19B4d5D29C7c3508B393a1C01Fe3` (chain 137)  
**Date:** 2026-07-29T05:58:34Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (50/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: LLM-drafted exploit test failed to compile
**Drafted exploit test (compile failed or not reached):**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "forge-std/Test.sol";
import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/IERC20.sol";

contract MegaDogeTest is Test {
    address constant TARGET = 0xCBf4AB00b6Aa19B4d5D29C7c3508B393a1C01Fe3;
    IERC20 public megaDoge = IERC20(TARGET);

    function test_exploit_extract() public {
        // Arrange
        address attacker = address(0x1337);
        uint256 initialAttackerBalance = megaDoge.balanceOf(attacker);

        // Act
        // Since we can't directly call the extract function as it requires admin role,
        // we'll try to exploit the arbitrary function which can be used to call any function
        // on any contract, including the extract function.
        // However, this also requires admin role, so we need to become an admin first.
        // We can do this by calling the approveAdmin function, but this requires the DEV_ADDRESS.
        // Since we don't have the DEV_ADDRESS, we can't directly exploit this contract.
        // But, if we assume that we have the DEV_ADDRESS or we can become an admin somehow,
        // we can use the arbitrary function to call the extract function.
        // For the sake of this example, let's assume we have the DEV_ADDRESS.
        address devAddress = address(0x1234); // Replace with the actual DEV_ADDRESS
        megaDoge.approveAdmin(attacker);
        megaDoge.confirmAdmin();
        uint256 contractBalance = megaDoge.balanceOf(TARGET);
        megaDoge.arbitrary(TARGET, abi.encodeWithSelector(megaDoge.extract.selector));

        // Assert
        uint256 finalAttackerBalance = megaDoge.balanceOf(attacker);
        assertGt(finalAttackerBalance, initialAttackerBalance);
        assertEq(megaDoge.balanceOf(TARGET), 0);
    }
}
```
```
Unable to resolve imports:
      "forge-std/Test.sol" in "/tmp/vape-foundry-exploit-k86st8_b/test/Exploit.t.sol"
      "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/IERC20.sol" in "/tmp/vape-foundry-exploit-k86st8_b/test/Exploit.t.sol"
with remappings:
      
Compiling 2 files with Solc 0.8.7
Solc 0.8.7 finished in 3.29ms
Error: Compiler run failed:
Error (6275): Source "forge-std/Test.sol" not found: File not found.
 --> test/Exploit.t.sol:4:1:
  |
4 | import "forge-std/Test.sol";
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error (6275): Source "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/IERC20.sol" not found: File not found.
ParserError: Source "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/IERC20.sol" not found: File not found.
 --> test/Exploit.t.sol:5:1:
  |
5 | import "https://github.com/OpenZeppelin/openzeppelin-contracts/blob/v4.7.3/contracts/token/ERC20/IERC20.sol";
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

```

---

## Vulnerability Analysis
**Project Overview**

MegaDoge (symbol: MegaDoge) is a standard ERC20 token deployed on Polygon at 0xCBf4AB00b6Aa19B4d5D29C7c3508B393a1C01Fe3. It claims a 2-billion-token total supply with 1 billion allocated for airdrops to 1 million addresses and 1 billion locked in liquidity. The contract was deployed by 0x38a5f90f91f29fcf94db8f2d4250338330c7a4df, who retains ~0.0419% of supply. Liquidity exists across multiple QuickSwap and Uniswap V2 pairs on Polygon (largest ~958 USD, total visible liquidity ~2.5k USD), with current price ~0.000059 USD and 24h volume of ~21 USD. Official site is https://megadoge.org. The token is verified as a non-proxy ERC20 compiled with Solidity 0.8.7.

**Executive Summary**

The simulated exploit PoC failed to compile, so no on-chain attack result is available. Static analysis tools were unavailable. Source review of the verified contract reveals severe centralized control: the deployer (DEV_ADDRESS) and subsequently approved admins can execute arbitrary calls to any target, drain ETH or tokens held by the contract, and perform privileged airdrops. These functions lack reentrancy protection and are gated only by simple address checks. No other vulnerability classes (oracle, overflow, upgrade, unbounded loops) show active issues in the provided code. The contract is a clear high-risk centralized token.

**Access Control**

The contract implements a custom admin system on top of ERC20:
- `DEV_ADDRESS` (set to `msg.sender` in constructor) can call `approveAdmin` and `revokeAdmin`.
- Approved addresses must call `confirmAdmin` to become active admins (`isADMIN`).
- All privileged functions (`extract`, `arbitrary`, `extractToken`, `airDrop`, `airDropBulk`) use `assert(isADMIN[msg.sender])` or `assert(msg.sender == DEV_ADDRESS)`.
- `arbitrary(address target, bytes memory b)` allows any admin to perform arbitrary external calls with ETH value, including to the token itself or liquidity pools.
- No role revocation for the original DEV_ADDRESS itself; admins can be added/removed but the root remains.

This is a classic single-point-of-control pattern that enables full contract takeover or fund drainage by the deployer or any approved admin.

**Reentrancy**

The `extract` and `arbitrary` functions perform external calls (`msg.sender.call{value:bal}("")` and `target.call{value:msg.value}(b)`) without any reentrancy guard. Although the contract does not hold user funds directly, any ETH sent to it (via `receive`/`fallback`) can be drained in a reentrant manner if an attacker controls a target that re-enters. The same risk applies if `arbitrary` is used against a malicious contract.

**Honeypot / Rug Mechanics**

GoPlus data (partial) shows no modifiable anti-whale or buy/sell taxes. However, the presence of `arbitrary`, `extract`, and `extractToken` functions controlled by a small set of addresses, combined with the contract holding the entire initial 2B supply, creates a direct rug vector: an admin can drain any tokens or ETH sent to the contract at any time. Multiple low-liquidity pools increase the practical impact of such actions.

**Recommended Human Follow-up**

- Verify the current DEV_ADDRESS and list of `isADMIN` addresses on-chain.
- Check whether any liquidity has been locked or renounced (not visible in source).
- Confirm whether the deployer or any admin has used `arbitrary` or `extract` historically.
- Review the actual airdrop distribution and locked liquidity claims against on-chain balances.

**Verdict: REJECT**

The contract contains unrestricted admin-controlled arbitrary execution and fund-extraction functions that constitute a complete rug risk. No further manual verification is needed before rejecting reliance on this token.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-15] Only 5% of liquidity is locked — the deployer can pull the rest at any time
- [-25] Very low liquidity $5,990 (rug/illiquid)
- [-10] Low liquidity $5,990

**Positive Signals**
- 992055 holders — reasonably distributed
- Trading 184+ days without a known incident in this scan
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