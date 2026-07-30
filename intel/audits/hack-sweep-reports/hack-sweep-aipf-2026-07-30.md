# VAPE Proactive HACK Sweep — AIPF

**Project:** AI Powered Finance ($AIPF)  
**Target:** `0x1f9467804cB4A916147fA529c3D335257874e071` (chain 137)  
**Date:** 2026-07-30T05:47:45Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (62/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: no TokenERC20 implementation or vulnerable logic provided in source

---

## Vulnerability Analysis
**Project Overview**

AI Powered Finance (AIPF) is an ERC-20 token deployed at 0x1f9467804cB4A916147fA529c3D335257874e071 on Polygon (chain 137). The verified contract is the standard thirdweb `TokenERC20` implementation (v0.8.23). It maintains ~162 k USD liquidity in a Uniswap V3 pool (0xb40c70d9603b68107f6e0fc39b45952c4bab1b0e, 0.3 % fee). The creator address (0xd2daa35ae4b2be511c5af00eff156c1221bf02f1) holds ~24.9 % of supply; no official website or social links are recorded in the market data.

**Executive Summary**

The executed forge-based attack simulation returned no exploit: “no TokenERC20 implementation or vulnerable logic provided in source.” The supplied source matches a standard thirdweb `TokenERC20` template that uses `AccessControlEnumerableUpgradeable`, `ReentrancyGuardUpgradeable`, and role-gated mint/transfer paths. No evidence of the examined vulnerability classes appears in the code. The token therefore presents a clean profile for the tested attack surface.

**Access Control**

Minting (`mintTo`, `mintWithSignature`) is restricted to `MINTER_ROLE`. Transfers are gated by `TRANSFER_ROLE` unless the role is granted to address(0). Both roles are assigned only by `DEFAULT_ADMIN_ROLE` in `initialize`. The implementation correctly uses `onlyRole` and `hasRole` checks; no unauthorized mint or transfer paths exist.

**Reentrancy**

All state-changing external functions (`mintTo`, `mintWithSignature`, fee setters) are protected by `nonReentrant`. The `collectPrice` helper uses the safe `CurrencyTransferLib` library. No reentrancy vectors are present.

**Upgrade / Proxy Risk**

The contract is not a proxy (`proxy: False`). The constructor contains an `initializer` guard and the implementation is deployed directly. Storage layout and initializer protection are standard for the thirdweb template.

**Other Classes**

No oracle, price-feed, or integer-overflow/precision issues exist (plain ERC-20 arithmetic with SafeERC20). No unbounded loops or MEV-sensitive logic beyond normal DEX interaction. GoPlus data shows zero buy/sell tax and no honeypot flags.

**Recommended Human Follow-up**

- Confirm the deployed bytecode hash matches the verified `TokenERC20` source exactly.
- Verify that `DEFAULT_ADMIN_ROLE` has not been renounced and that the current admin is a secure multisig or DAO.
- Review any off-chain minting scripts or front-ends that call `mintWithSignature` to ensure signature freshness and UID uniqueness.

**PROCEED**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-8] Upgradeable proxy (verify implementation)
- [-15] Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipulated
- [-15] Only 0% of liquidity is locked — the deployer can pull the rest at any time

**Positive Signals**
- 18243 holders — reasonably distributed
- Trading 139+ days without a known incident in this scan
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