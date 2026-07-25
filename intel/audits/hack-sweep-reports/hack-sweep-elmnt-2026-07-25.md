# VAPE Proactive HACK Sweep — ELMNT

![ELMNT logo](https://cdn.dexscreener.com/cms/images/f2d2118b33f034751bbb512f88161dccd073375946d3f7636a07eeaf0e703337?width=800&height=800&quality=95&format=auto)

**Project:** Element 280 ($ELMNT) — https://element280.win/ · https://docs.helios-hlx.win/element280 · https://x.com/Element280 · https://t.me/Helios_HLX/33670  
**Target:** `0xe9A53C43a0B58706e67341C4055de861e29Ee943` (chain 1)  
**Date:** 2026-07-25T05:47:39Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (65/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: scaffolded project does not compile
```
iswapV2Router02.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
  --> src/contracts/Element280.sol:10:1:
   |
10 | import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error (6275): Source "@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
ParserError: Source "@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
  --> src/contracts/Element280.sol:11:1:
   |
11 | import "@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol";
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error (6275): Source "@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
ParserError: Source "@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
  --> src/contracts/Element280.sol:12:1:
   |
12 | import "@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol";
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error (6275): Source "@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
ParserError: Source "@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol" not found: File not found. Searched the following locations: "/tmp/vape-foundry-exploit-4syvwku0".
  --> src/contracts/Element280.sol:13:1:
   |
13 | import "@uniswap/v3-periphery/contracts/interfaces/ISwapRouter.sol";
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error (
```

---

## Vulnerability Analysis
**Project Overview**  
Element 280 (symbol ELMNT) is an ERC-20 token deployed at `0xe9A53C43a0B58706e67341C4055de861e29Ee943` on Ethereum mainnet. The contract is verified on Etherscan under the name “Element280” (Solidity 0.8.24, non-proxy). Public references include https://element280.win/, https://docs.helios-hlx.win/element280, Twitter @Element280 and a Telegram channel. On-chain data shows ~746 holders, ~$8.3 k liquidity on Uniswap, and a reported 3.99 % buy tax via GoPlus.

**Executive Summary**  
No simulated attack PoC was executed; the scaffolded Foundry project failed to compile. Full source for the token’s custom logic was not supplied—only standard OpenZeppelin libraries (ERC20, Ownable2Step, SafeERC20, etc.). GoPlus flags no hidden owner, no modifiable anti-whale mechanics, and no external-call or cannot-sell-all issues. The token therefore presents a standard fee-bearing ERC-20 profile with no immediately visible rug or honeypot signals from the available recon data.

**Access Control**  
The contract inherits `Ownable2Step` from OpenZeppelin. Ownership transfer requires a two-step process (`transferOwnership` then `acceptOwnership`), and the initial owner is set at deployment. No evidence of privileged mint/burn or fee-setting functions is visible in the provided library code.

**Fee / Tax Mechanics**  
GoPlus reports a 3.99 % buy tax. No sell-tax figure or tax-modification functions appear in the supplied data. The tax is therefore presumed to be either immutable or gated behind the two-step ownership mechanism.

**Liquidity & Holder Distribution**  
Top holders are a mix of contracts and EOAs; the largest single holder controls ~15.9 % of supply. No locked-liquidity or locked-token flags are present in the GoPlus output.

**Recommended Human Follow-up**  
1. Retrieve and review the complete verified source on Etherscan for fee, mint, and ownership logic.  
2. Confirm whether ownership has been renounced or remains with the deployer (`0xdc0364230f2552734384fa346e82904f49633ff2`).  
3. Test tax behavior on a local fork with realistic buy/sell transactions.  
4. Verify liquidity-lock status and any vesting contracts referenced in the docs.

**Verdict: CAUTION**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-25] Very low liquidity $8,300 (rug/illiquid)
- [-10] Low liquidity $8,300

**Positive Signals**
- Ownership renounced
- 746 holders — reasonably distributed
- Trading 651+ days without a known incident in this scan
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