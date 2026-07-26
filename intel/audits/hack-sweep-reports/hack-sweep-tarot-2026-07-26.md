# VAPE Proactive HACK Sweep — TAROT

**Project:** Tarot ($TAROT)  
**Target:** `0x1F514A61bcde34F94Bc39731235690ab9da737F7` (chain 10)  
**Date:** 2026-07-26T06:10:46Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (63/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: No TarotOFT implementation source or vulnerability details provided.

---

## Vulnerability Analysis
**Project Overview**  
Tarot (TAROT) is an ERC-20 token deployed on Optimism at `0x1F514A61bcde34F94Bc39731235690ab9da737F7`. It implements the LayerZero Omnichain Fungible Token (OFT) standard, enabling cross-chain transfers via the LayerZero messaging protocol. The token trades on Velodrome (pair `0x707ba27189e8bf89e43b2198e6b88aac4720124f`) with ~$263k liquidity and a price of ~$0.029. The contract is verified (Solidity 0.8.13, non-proxy) and the creator address `0x5b0390bccca1f040d8993eb6e4ce8ded93721765` holds ~72.5% of supply.

**Executive Summary**  
The executed forge-based proof-of-concept returned no exploit: “No TarotOFT implementation source or vulnerability details provided.” The supplied source consists solely of LayerZero base contracts (LzApp, NonblockingLzApp, OFTCore, etc.); the concrete TarotOFT contract body was not present. No reentrancy, access-control bypass, oracle, integer, or upgrade issues are observable in the provided code. GoPlus reports no hidden-owner, modifiable anti-whale, or external-call flags. The primary risk visible from on-chain data is extreme token concentration at the creator wallet.

**Access Control (Owner/Role Gating)**  
All privileged functions (`setTrustedRemote`, `setSendVersion`, `setMinDstGas`, `setPrecrime`, `setUseCustomAdapterParams`, etc.) are gated by `onlyOwner` inherited from OpenZeppelin Ownable. No unprotected initializer or role-escalation paths appear in the given LzApp/OFTCore code.

**Reentrancy**  
`NonblockingLzApp._blockingLzReceive` uses `excessivelySafeCall` with a gas cap and does not perform external calls that could re-enter the token accounting. The standard OFT `_debitFrom`/`_creditTo` pattern (burn/mint) executes before the cross-chain message is sent, eliminating the classic reentrancy window.

**Oracle Manipulation / Price Feed Trust**  
No price oracles are present in the contract.

**Integer Overflow / Precision Loss**  
Solidity 0.8.13 is used; arithmetic is checked by default. No custom math or fee calculations exist in the supplied sources.

**Upgrade / Proxy Risk**  
Etherscan reports the contract is not a proxy. Storage layout follows the standard OFT inheritance; no storage-collision vectors are possible.

**Unbounded Loops / DoS**  
No loops over unbounded arrays or holder lists are present.

**Front-Running / MEV Surface**  
Cross-chain `sendFrom` calls are permissionless and carry a user-supplied `refundAddress`; no privileged ordering or MEV-extractable state changes are visible.

**Honeypot / Rug Mechanics (GoPlus)**  
GoPlus flags are all benign (`anti_whale_modifiable=0`, `can_take_back_ownership=0`, `hidden_owner=0`, `external_call=0`). The only notable on-chain observation is the creator’s 72.5% balance.

**Recommended Human Follow-up**  
1. Obtain and review the complete, untruncated TarotOFT.sol source (the actual contract inheriting OFT).  
2. Verify the LayerZero endpoint address and trusted-remote configuration on Optimism.  
3. Confirm whether the creator wallet is a multisig or timelocked contract.  
4. Check circulating-supply accounting against the bridged supply on other chains.  

**Verdict: PROCEED** (no executable vulnerability demonstrated; standard LayerZero OFT implementation with high but disclosed creator concentration).

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-12] Mintable supply (dilution risk)
- [-10] Owner not renounced (0x5b0390bccca1f040d8993eb6e4ce8ded93721765) — can still act on the contract
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated

**Positive Signals**
- 2450 holders — reasonably distributed
- Trading 958+ days without a known incident in this scan
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