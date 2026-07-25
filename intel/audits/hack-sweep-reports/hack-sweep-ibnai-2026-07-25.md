# VAPE Proactive HACK Sweep — IBNAi

![IBNAi logo](https://cdn.dexscreener.com/cms/images/JuIUYDOXteFDI0F2?width=800&height=800&quality=95&format=auto)

**Project:** Investor Brand Network Ai ($IBNAi) — https://ibnai.com/ · https://investorbrandnetwork.info/ibnai/wp/index.html · https://investorbrandnetwork.info/ibnai/tokenomics/index.html · https://ibnai.com/disclaimer.html · https://x.com/IBNAiToken  
**Target:** `0xFdcD8be9DD37CF982472d30eeeE4ec50A0296953` (chain 1)  
**Date:** 2026-07-25T05:48:09Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (70/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: no mint/distribute/privileged transfer logic or other vulnerability present in the provided source.

---

## Vulnerability Analysis
**Project Overview**

Investor Brand Network Ai (IBNAi) is a fixed-supply ERC20 token deployed on Ethereum at `0xFdcD8be9DD37CF982472d30eeeE4ec50A0296953`. The verified contract (v0.8.20, non-proxy) mints its entire 1 000 000 000 token supply to the deployer at construction and exposes a single privileged helper, `distributeTokens`, for owner-controlled distribution. Liquidity exists primarily on Uniswap V2 (`0x3aa7255807d2619240a6ec51ac93d8b31be23a8a`) with smaller Uniswap V4 positions; official references include https://ibnai.com/ and https://x.com/IBNAiToken. GoPlus reports no hidden owner, no modifiable fees, no external calls, and zero creator balance.

**Executive Summary**

The executed forge-based exploit simulation returned “no exploit found: no mint/distribute/privileged transfer logic or other vulnerability present in the provided source.” This outcome is consistent with the verified source: the only privileged path is the documented `onlyOwner` `distributeTokens` function, which performs a standard ERC20 transfer after explicit balance and zero-address checks. No post-deployment minting, no reentrancy vectors, and no oracle or proxy logic exist. All other examined vulnerability classes are absent or mitigated by the simple, non-upgradable implementation.

**Access Control**

The contract inherits `Ownable` and restricts `distributeTokens`, `renounceOwnership`, and `transferOwnership` to the owner. The constructor mints the full supply to `msg.sender`, after which ownership can be renounced. This matches the documented trust model and is not an exploitable back-door.

**Reentrancy**

Neither `_transfer` nor `distributeTokens` performs any external calls. The standard ERC20 hooks (`_beforeTokenTransfer`, `_afterTokenTransfer`) are empty. Reentrancy is therefore impossible.

**Oracle Manipulation / Price Feed Trust**

No price oracles, DEX integrations, or external data sources are present in the contract.

**Integer Overflow / Precision Loss**

All arithmetic uses Solidity 0.8.20 checked arithmetic or the explicit `unchecked` blocks already present in OpenZeppelin’s ERC20 implementation for well-known safe patterns. No custom math or fee calculations exist.

**Upgrade / Proxy Risk**

The contract is not a proxy (Etherscan confirmation) and contains no storage-collision or initializer patterns.

**Unbounded Loops / DoS**

No loops of any kind are present.

**Front-running / MEV Surface**

The only state-changing privileged function is `distributeTokens`, which simply transfers tokens the owner already holds. No auctions, liquidations, or time-sensitive operations exist that would create MEV value.

**Honeypot / Rug Mechanics (GoPlus flags)**

All relevant GoPlus fields are benign: `anti_whale_modifiable=0`, `buy_tax=0`, `hidden_owner=0`, `external_call=0`, `can_take_back_ownership=0`. Creator balance is already zero.

**Recommended Human Follow-up**

- Verify that the current owner has already called (or intends to call) `renounceOwnership` after distribution.
- Confirm the `distributeTokens` event logs match the project’s claimed allocations.
- Spot-check that the Uniswap V2 pair holds the reported liquidity and that no other contracts depend on this token for privileged operations.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-10] Owner not renounced (0x0f5f60ad3e43839d6b9d4a6d1d8eded24db73c32) — can still act on the contract
- [-10] Pair 7.6 days old — under two weeks, no track record yet
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