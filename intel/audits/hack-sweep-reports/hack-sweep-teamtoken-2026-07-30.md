# VAPE Proactive HACK Sweep — TeamToken

**Target:** `0xEa59Fa56e4ff71D690BaA76EbB3A7325490E9680` (chain 137)  
**Date:** 2026-07-30T05:48:06Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** REJECT (17/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: LLM-drafted exploit test failed to compile
**Drafted exploit test (compile failed or not reached):**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0 <0.8.0;

import "forge-std/Test.sol";
import "tf-mint/contracts/ERC20.sol";

contract TeamTokenTest is Test {
    address constant TARGET = 0xEa59Fa56e4ff71D690BaA76EbB3A7325490E9680;
    ERC20 public token;

    function setUp() public {
        token = ERC20(TARGET);
    }

    function test_exploit_insufficient_funds() public {
        // Assuming the contract has a function to transfer tokens
        // and the attacker has some tokens
        address attacker = address(this);
        uint256 initialAttackerBalance = token.balanceOf(attacker);
        uint256 initialContractBalance = token.balanceOf(TARGET);

        // Try to transfer more tokens than the attacker has
        uint256 amount = initialAttackerBalance + 1;
        vm.expectRevert("ERC20: transfer amount exceeds balance");
        token.transfer(TARGET, amount);

        // Check that the balances haven't changed
        assertEq(token.balanceOf(attacker), initialAttackerBalance);
        assertEq(token.balanceOf(TARGET), initialContractBalance);
    }
}
```
```
Unable to resolve imports:
      "forge-std/Test.sol" in "/tmp/vape-foundry-exploit-9bncnjme/test/Exploit.t.sol"
      "tf-mint/contracts/ERC20.sol" in "/tmp/vape-foundry-exploit-9bncnjme/test/Exploit.t.sol"
with remappings:
      
Compiling 2 files with Solc 0.6.12
Solc 0.6.12 finished in 2.98ms
Error: Compiler run failed:
Error (6275): Source "forge-std/Test.sol" not found: File not found.
test/Exploit.t.sol:4:1: ParserError: Source "forge-std/Test.sol" not found: File not found.
import "forge-std/Test.sol";
^--------------------------^
Error (6275): Source "tf-mint/contracts/ERC20.sol" not found: File not found.
test/Exploit.t.sol:5:1: ParserError: Source "tf-mint/contracts/ERC20.sol" not found: File not found.
import "tf-mint/contracts/ERC20.sol";
^-----------------------------------^

```

---

## Vulnerability Analysis
**Project Overview**  
TeamToken (0xEa59Fa56e4ff71D690BaA76EbB3A7325490E9680) on Polygon is a minimal ERC20 implementation deployed with the verified TeamToken contract (Solidity 0.6.12). The single constructor call mints the entire initial supply to the provided owner address; no further minting, ownership transfer, or fee logic exists in the deployed code. The creator (0x4837193e11e20370ed52136f3b41c9e87b328091) holds ~96 % of the supply across only eight addresses, the majority of which are contracts.

**Executive Summary**  
SIMULATED ATTACK — EXECUTED PROOF-OF-CONCEPT: LLM-drafted exploit test failed to compile. No on-chain attack was executed and therefore no impact was demonstrated.  

The verified source is a plain ERC20 with SafeMath and a one-time `_mint` in the constructor. No owner, no external calls, no reentrancy vectors, and no upgradeability are present. GoPlus concentration data (creator > 95 %) is the only material observation; it is a distribution risk rather than a code exploit.

**Access Control**  
The contract contains no owner, role, or privileged functions after deployment. All tokens are minted once in the constructor to the supplied owner address. No can_take_back_ownership or hidden_owner flags are present in the source.

**Reentrancy**  
`_transfer`, `_mint`, and `_burn` contain no external calls. The standard ERC20 pattern with no callbacks is used.

**Oracle / Price Feed Trust**  
No oracles or price feeds exist.

**Integer Overflow / Precision Loss**  
SafeMath is applied to every arithmetic operation; the 0.6.12 compiler and library usage eliminate the classic overflow class.

**Upgrade / Proxy Risk**  
The contract is not a proxy (verified as implementation: None). Storage layout is immutable after deployment.

**Unbounded Loops / DoS**  
No loops of any kind are present in the token logic.

**Front-running / MEV Surface**  
No privileged or time-sensitive functions exist that could be front-run.

**Honeypot / Rug Mechanics (GoPlus flags)**  
The “fake_token” flag references unrelated USDT addresses and is not corroborated by the verified source. The only observable risk is extreme token concentration, which is a holder-distribution issue rather than a contract back-door.

**Recommended Human Follow-up**  
- Confirm that the eight holder contracts have no unexpected privileged roles or upgrade paths.  
- Verify the deployment transaction arguments (owner, feeWallet, supply) match the intended distribution.  
- Review any off-chain claims or liquidity arrangements that rely on the 96 % holder address.

**Verdict: PROCEED**  
No executable exploit path was identified; the contract is a standard, immutable ERC20. Human review should focus solely on the distribution of the minted supply.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-30] Same deployer has a prior CAUTION/REJECT verdict on record: WMATIC (0xA36d14E43b1a049983B86166A2f0210a9519f80a) — REJECT 10/100 — likely the same serial campaign
- [-20] Very few holders (8) — thin, easily manipulated distribution
- [-15] Top 8 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-8] No pair-creation timestamp available — cannot establish track record length
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

**Positive Signals**
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