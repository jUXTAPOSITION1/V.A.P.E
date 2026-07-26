# VAPE Proactive HACK Sweep — AIPF

![AIPF logo](https://cdn.dexscreener.com/cms/images/2afc1b42fcaa663bcdee7e62a6591a3cd2f2bc9be2993411665cb042df4d5579?width=800&height=800&quality=95&format=auto)

**Project:** AI Powered Finance ($AIPF) — https://aip.finance/ · https://docs.aip.finance/ · https://x.com/AIPF_official · https://t.me/aipf_official  
**Target:** `0x2c72D25530191EBD244Eb6325E1892480b0e6E28` (chain 137)  
**Date:** 2026-07-26T06:11:11Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (73/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: LLM-drafted exploit test failed to compile
**Drafted exploit test (compile failed or not reached):**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "./AIPF.sol";

contract AIPFTest is Test {
    address constant TARGET = 0x2c72D25530191EBD244Eb6325E1892480b0e6E28;
    AIPF public aipf;

    constructor() {
        aipf = AIPF(TARGET);
    }

    function test_exploit_mint() public {
        // Given that the _hgl and _qem addresses are hardcoded in the contract,
        // an attacker cannot directly exploit the mint function.
        // However, if an attacker can manipulate the _hgl or _qem addresses,
        // they can exploit the mint function to mint arbitrary amounts of tokens.

        // Assume the attacker has manipulated the _hgl address to their own address.
        address attacker = address(this);
        uint256 amountToMint = 1000 * (10 ** 18);

        // The attacker calls the mint function to mint tokens to their own address.
        vm.prank(attacker);
        aipf.mint(attacker, amountToMint);

        // Assert that the attacker's balance has increased.
        assertGt(aipf.balanceOf(attacker), 0);
    }
}
```
```
Unable to resolve imports:
      "forge-std/Test.sol" in "/tmp/vape-foundry-exploit-nrpsh706/test/Exploit.t.sol"
      "./AIPF.sol" in "/tmp/vape-foundry-exploit-nrpsh706/test/Exploit.t.sol"
with remappings:
      contracts/=/tmp/vape-foundry-exploit-nrpsh706/src/contracts/
Compiling 6 files with Solc 0.8.20
Solc 0.8.20 finished in 4.02ms
Error: Compiler run failed:
Error (6275): Source "forge-std/Test.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-nrpsh706".
ParserError: Source "forge-std/Test.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-nrpsh706".
 --> test/Exploit.t.sol:4:1:
  |
4 | import "forge-std/Test.sol";
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error (6275): Source "test/AIPF.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-nrpsh706".
ParserError: Source "test/AIPF.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-nrpsh706".
 --> test/Exploit.t.sol:5:1:
  |
5 | import "./AIPF.sol";
  | ^^^^^^^^^^^^^^^^^^^^

```

---

## Vulnerability Analysis
**Project Overview**  
AI Powered Finance (AIPF) is an ERC-20 token deployed at `0x2c72D25530191EBD244Eb6325E1892480b0e6E28` on Polygon (chain 137). It maintains ~$8.28 M liquidity primarily on Uniswap V2 (`0x124fcfd1b923485c8ccf275afbee4bf557b232d6`) with smaller Uniswap V4 positions. The token claims to be “AI Powered Finance,” with official links at https://aip.finance/, https://docs.aip.finance/, https://x.com/AIPF_official and https://t.me/aipf_official. The contract is verified (Solidity 0.8.20), non-proxy, and the creator address holds zero tokens.

**Executive Summary**  
The simulated exploit PoC did not compile, so no on-chain attack was executed. Static analysis of the verified source reveals two material issues: (1) unrestricted minting by two hardcoded addresses (`_hgl`, `_qem`) and (2) a 5 % sell fee that can be toggled on any address by the owner. No reentrancy, oracle, upgrade, or integer-overflow vectors are present. GoPlus flags are clean. Overall risk is moderate; the token is not a classic honeypot but contains privileged mint and fee controls that warrant manual review.

**Access Control**  
- `mint(address,uint256)` is callable by anyone who controls `0x14F0D3603774B4ca4d0A052896691FE20C11a975` or `0xe2Dc5E8F9c80Db6baF644BA05DF800D04fb9667F`. These addresses are set once in the constructor and cannot be changed.  
- `setPairAddress(address,bool)` is gated by `onlyOwner`, allowing the owner to designate any address as a taxed pool.  
- Standard `Ownable` functions (`renounceOwnership`, `transferOwnership`) are present and correctly implemented.  
No other role-gated functions exist.

**Fee / Tax Mechanics**  
`_transfer` applies a 5 % (`_sellFee = 50`, `_bps = 1000`) fee only when the recipient is marked as a pool and the sender is not `_feeReceiver`. The fee is sent to the immutable `_feeReceiver` (`0xc7E482d02C579b9F36EeAAc849BbF699A4D5044B`). Buy-side transfers incur zero tax. The owner can add or remove taxed pairs at any time, creating a potential front-running surface if the owner or a privileged actor marks a new pool.

**Other Classes**  
- Reentrancy: absent; all state updates occur before external calls and no external calls are made inside `_transfer`.  
- Oracle / price feed: none present.  
- Integer overflow / precision: uses SafeMath on top of Solidity 0.8 checked arithmetic; no issues.  
- Upgrade / proxy: contract is not a proxy and contains no initializer pattern.  
- Unbounded loops / DoS: no loops in any user-facing function.  
- Honeypot / rug flags: GoPlus reports `buy_tax=0`, `anti_whale_modifiable=0`, `cannot_sell_all=0`; creator balance is zero.

**Recommended Human Follow-up**  
1. Verify the two mint-authorized addresses (`_hgl`, `_qem`) are controlled by reputable parties or multisigs.  
2. Confirm `_feeReceiver` is a trusted multisig or DAO and cannot be changed.  
3. Check whether the owner has renounced or transferred ownership since deployment.  
4. Review any off-chain minting policy or emission schedule published in the docs.  
5. Re-run a compiled Foundry test against a Polygon fork to confirm the 5 % sell fee behaves as described on the live pair.  

**Verdict: CAUTION**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-12] Mintable supply (dilution risk)
- [-15] Top 10 non-LP/burn holders control 106% of supply — concentrated, easily manipulated

**Positive Signals**
- Ownership renounced
- 36633 holders — reasonably distributed
- 100% of liquidity is locked — reduced rug-pull risk
- Deep liquidity ($8,282,592)
- Trading 249+ days without a known incident in this scan
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