# VAPE Proactive HACK Sweep — HLX

![HLX logo](https://cdn.dexscreener.com/cms/images/31a428523f8ccdcf9814bbd13e2288381f71f35d802e1dd88fe1e1c5fbf87b3b?width=800&height=800&quality=95&format=auto)

**Project:** HELIOS ($HLX) — https://app.helios.win/ · https://docs.helios-hlx.win/helios · https://x.com/Helios_HLX · https://t.me/Helios_HLX/1  
**Target:** `0x2614f29C39dE46468A921Fd0b41fdd99A01f2EDf` (chain 1)  
**Date:** 2026-07-24T05:54:44Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (53/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
HELIOS (HLX) is an ERC-20 token at 0x2614f29C39dE46468A921Fd0b41fdd99A01f2EDf on Ethereum that implements a daily-updating mint/burn/staking system with 22/69/420-day payout cycles, share-rate mechanics, burn amplifiers, and treasury/buy-and-burn fee splits. The contract (Solidity 0.8.10, verified, non-proxy, 23 877 bytes) inherits OpenZeppelin ERC20 + ReentrancyGuard and custom BurnInfo/GlobalInfo modules. Creator holds a negligible balance (~0.000006 %); GoPlus reports zero buy tax, no hidden owner, and no modifiable anti-whale mechanics. Official links: https://app.helios.win/, https://docs.helios-hlx.win/helios, @Helios_HLX on X, t.me/Helios_HLX.

**Executive Summary**  
The audited fragment shows standard ERC-20 + ReentrancyGuard usage and careful unchecked arithmetic. The only material surface-level risk is a potentially unbounded `for` loop inside `_dailyUpdate` when many days have elapsed without interaction. No reentrancy, access-control, oracle, or proxy issues are visible in the supplied code. No honeypot or rug signals appear in the GoPlus or on-chain data. Overall the contract appears low-risk for the classes examined, but the loop and any unshown owner-gated functions require manual review.

**Reentrancy**  
The contract inherits OpenZeppelin `ReentrancyGuard` and applies the `nonReentrant` modifier to functions that call external code. The supplied `ReentrancyGuard` implementation matches the audited v4.9 version. No reentrancy vectors are present in the visible logic.

**Access Control (owner/role gating)**  
No `Ownable`, `AccessControl`, or privileged mint/burn functions appear in the provided source. Creator balance is negligible and GoPlus flags `can_take_back_ownership = 0` and `hidden_owner = 0`. No evidence of owner-controlled balance manipulation in the given code.

**Integer Overflow / Precision Loss**  
All arithmetic uses Solidity 0.8 checked math except for a few explicitly `unchecked` blocks that the comments justify (capped totals, balance adjustments). The daily-update loop and burn-amplifier calculations stay within `uint256` bounds. No classic overflow or precision-loss patterns observed.

**Unbounded Loops / DoS**  
`_dailyUpdate` contains:  
```solidity
for (uint256 i; i < dayDifference; i++) { ... }
```  
`dayDifference` is derived from `block.timestamp` and can grow arbitrarily if the contract is untouched for months. Although each iteration performs only cheap arithmetic and the values are capped, an extremely large `dayDifference` could still push a single call past the block gas limit, creating a temporary DoS on any function using the `dailyUpdate` modifier.

**Recommended Human Follow-up**  
1. Inspect the full contract for any owner-only or privileged functions not present in the truncated source.  
2. Measure worst-case gas of `_dailyUpdate` when `dayDifference` ≥ 365.  
3. Verify that all external calls (if any) are protected by `nonReentrant` and that the payout-cycle logic cannot be front-run to the detriment of other stakers.  
4. Confirm the deployed bytecode hash matches the verified source on Etherscan.

**PROCEED**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-12] Mintable supply (dilution risk)
- [-25] Owner can change balances (rug surface)
- [-10] Low liquidity $18,329

### Positive Signals
- 632 holders — reasonably distributed
- Trading 486+ days without a known incident in this scan
- Custom verified source (not a mass-produced factory template)

## Static Analysis (Slither)
- Not run this cycle: slither not installed in this environment this run

## Symbolic Testing (Halmos)
- Not run this cycle: halmos not installed in this environment this run

## Static Analysis (Mythril)
- Not run this cycle: mythril (myth) not installed in this environment this run

## Static Analysis (Aderyn)
- Not run this cycle: no scaffolded Foundry project available this run (symbolic testing didn't reach the scaffolding stage)

## Methodology
1. Real keyless recon: GoPlus token security, DexScreener liquidity, Base RPC on-chain presence, DeFiLlama hack-technique correlation, public web search for reputation flags — identical pipeline to every open-source VAPE investigation.
2. Etherscan V2 contract verification + full verified source (when available).
3. Slither static analysis, real tool output, only if pre-installed this run.
4. Halmos bounded symbolic testing against LLM-drafted check_* properties compiled into a scaffolded Foundry project built from that same verified source — only if forge and halmos are both installed this run.
5. Mythril symbolic-execution scan of the deployed bytecode on-chain by address, via the target chain's real public RPC — only if pre-installed this run.
6. Aderyn static AST analysis of that same scaffolded Foundry project — only if pre-installed this run and step 4's scaffolding stage was reached.
7. A frontier-tier LLM reads the actual verified source and reasons per vulnerability class — this is VAPE's deepest automated pass, still followed by the human-verification list above.
8. White-hat only: read-only analysis, no exploitation attempted.

*This report was generated proactively by VAPE's own daily HACK sweep (agents/hack_sweep.py) — not a paid engagement.*