# VAPE Proactive HACK Sweep — MV

**Project:** Metaverse (PoS) ($MV)  
**Target:** `0xA3c322Ad15218fBFAEd26bA7f616249f7705D945` (chain 137)  
**Date:** 2026-07-28T05:54:16Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (52/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: LLM-drafted exploit test failed to compile
**Drafted exploit test (compile failed or not reached):**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.6.6;

import "forge-std/Test.sol";

interface IERCProxy {
    function proxyType() external pure returns (uint256 proxyTypeId);

    function implementation() external view returns (address codeAddr);
}

contract UChildERC20ProxyTest is Test {
    address constant TARGET = 0xA3c322Ad15218fBFAEd26bA7f616249f7705D945;

    function test_exploit_proxy_owner_update() public {
        // Get the initial proxy owner
        address initialOwner = UChildERC20Proxy(TARGET).proxyOwner();

        // Try to update the proxy owner
        vm.expectRevert("NOT_OWNER");
        UChildERC20Proxy(TARGET).transferProxyOwnership(address(this));

        // Since we can't update the owner directly, we can't exploit this contract
        // However, we can test that the owner can update the implementation
        address newImplementation = address(new MockImplementation());
        UChildERC20Proxy(TARGET).updateImplementation(newImplementation);

        // Assert that the implementation has been updated
        assertEq(UChildERC20Proxy(TARGET).implementation(), newImplementation);
    }
}

contract MockImplementation {}
```
```
Unable to resolve imports:
      "forge-std/Test.sol" in "/tmp/vape-foundry-exploit-vdhu3e6b/test/Exploit.t.sol"
with remappings:
      
Compiling 2 files with Solc 0.6.6
Solc 0.6.6 finished in 2.10ms
Error: Compiler run failed:
Error: Source "forge-std/Test.sol" not found: File outside of allowed directories.
test/Exploit.t.sol:4:1: ParserError: Source "forge-std/Test.sol" not found: File outside of allowed directories.
import "forge-std/Test.sol";
^--------------------------^

```

---

## Vulnerability Analysis
**Project Overview**

Metaverse (MV) is an ERC-20 token deployed on Polygon (chain 137) at 0xA3c322Ad15218fBFAEd26bA7f616249f7705D945. It operates as a UChildERC20Proxy (verified, v0.6.6), an upgradeable proxy implementation from the Matic/Polygon child-token framework, with its logic contract at 0xca1ef4070b388faff5c40ba0261dc8cfd5150f76. Liquidity is fragmented across QuickSwap (UniV2) pairs and smaller Uniswap V3/V4 pools, totaling roughly $11.8k USD with 24h volume under $30. The creator address holds a zero balance and the token shows zero buy/sell taxes or trading restrictions in the scanned data. No official website or social links are associated with the token.

**Executive Summary**

The simulated exploit test could not be executed because the drafted Foundry test failed to compile; therefore no on-chain proof-of-concept result is available to confirm or refute an active attack path. The contract is a standard `UpgradableProxy` with a single privileged owner that can unilaterally replace the implementation contract. No reentrancy vectors, oracle dependencies, or arithmetic issues are visible in the supplied proxy source. The dominant risk is the upgrade path itself: the proxy owner can swap the logic contract at any time, which is a structural concern for any token whose value depends on immutable behavior.

**Upgrade / Proxy Risk**

The contract inherits `UpgradableProxy`, which stores the implementation address in `IMPLEMENTATION_SLOT` and the owner in `OWNER_SLOT`. Both slots are written via direct assembly `sstore` inside `setImplementation` and `setProxyOwner`. Only the address returned by `loadProxyOwner()` may call `updateImplementation`, `transferProxyOwnership`, or `updateAndCall`. Because the proxy forwards every call via `delegatecall` in its fallback, any future logic contract can arbitrarily modify storage, including balances and allowances. The original creator address currently holds zero tokens, but the proxy owner (set at deployment) is not shown to be renounced or transferred to a timelock or DAO. This leaves an open administrative path that could be used to alter token semantics without holder consent.

**Access Control**

The `onlyProxyOwner` modifier performs a single `sload` comparison against `msg.sender`. There are no role-based restrictions or multi-signature requirements. `transferProxyOwnership` allows the current owner to hand control to any non-zero address in one transaction. No other gated functions exist in the proxy itself.

**Recommended Human Follow-up**

- Query the live value at `OWNER_SLOT` (keccak256("matic.network.proxy.owner")) on 0xA3c322Ad15218fBFAEd26bA7f616249f7705D945 to identify the current proxy owner and whether it is a contract or EOA.  
- Inspect the implementation at 0xca1ef4070b388faff5c40ba0261dc8cfd5150f76 for any privileged mint, burn, or pause logic that the proxy owner could activate.  
- Verify whether the proxy owner has ever called `updateImplementation` or `transferProxyOwnership` on-chain.  
- Confirm the liquidity-pool contracts are not themselves controlled by the same owner.

**CAUTION**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 73% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time
- [-10] Low liquidity $11,842

**Positive Signals**
- 12726 holders — reasonably distributed
- Trading 1643+ days without a known incident in this scan
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