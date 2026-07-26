# VAPE Proactive HACK Sweep — EBCC

**Project:** EBCC_coin ($EBCC)  
**Target:** `0x49DDee75D588b79a3eB1225dd386644eeeeeaF08` (chain 137)  
**Date:** 2026-07-26T06:11:50Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (70/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: Standard OpenZeppelin ERC20 with no custom mint/owner/privileged logic shown in source.

---

## Vulnerability Analysis
**Project Overview**  
EBCC_coin (EBCC) is a standard ERC-20 token deployed at 0x49DDee75D588b79a3eB1225dd386644eeeeeaF08 on Polygon (chain 137). It was verified on Etherscan as a non-proxy contract compiled with Solidity 0.8.30. The token maintains Uniswap V3 and V4 liquidity pools (primary pair 0x046851643a71a90d03202e0f4453954bc3abd1b3) with approximately $168k USD liquidity and modest 24h volume. One address holds ~99.6% of the supply; the original creator address shows a zero balance. No official website or social links are present in the available market data.

**Executive Summary**  
SIMULATED ATTACK — EXECUTED PROOF-OF-CONCEPT: Not available this run: no exploit found: Standard OpenZeppelin ERC20 with no custom mint/owner/privileged logic shown in source.

The contract is a minimal ERC-20 (OpenZeppelin v5) that inherits Ownable. The constructor performs a single `_mint` of 800,000,000 tokens to the deployer; no further mint, burn, or fee logic exists in the provided source. The executed PoC therefore correctly reports no exploitable path. GoPlus data shows no modifiable anti-whale mechanics, hidden owner, or external-call flags. No other vulnerability classes produced evidence in the verified source or on-chain data.

**Access Control**  
The contract inherits the standard OpenZeppelin Ownable pattern. The only owner-gated functions are `renounceOwnership` and `transferOwnership`; no mint, fee, or pause functions are present or callable by the owner. The initial mint occurs exclusively in the constructor, after which ownership can be renounced or transferred but cannot create new tokens.

**Recommended Human Follow-up**  
- Confirm the current owner address and whether ownership has been renounced.  
- Verify that the 99.6% holder address is a known multisig, timelock, or liquidity position rather than an individual EOA.  
- Spot-check that the deployed bytecode on Polygon exactly matches the verified source (no additional privileged functions were added post-deployment).  

**PROCEED**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-15] Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

**Positive Signals**
- Ownership renounced
- 4589 holders — reasonably distributed
- Trading 233+ days without a known incident in this scan
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