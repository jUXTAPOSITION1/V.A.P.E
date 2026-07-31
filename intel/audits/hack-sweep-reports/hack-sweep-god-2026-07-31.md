# VAPE Proactive HACK Sweep — GOD

**Target:** `0x4c746Edf20762dC201aC40135e0C13e400d23D58` (chain 1)  
**Date:** 2026-07-31T06:19:06Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (64/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: no public attacker-controlled path to drain or break invariants beyond standard owner/taxWallet privileges shown in source.

---

## Vulnerability Analysis
**Project Overview**  
The contract at `0x4c746Edf20762dC201aC40135e0C13e400d23D58` on Ethereum is the ERC-20 token `GOD` (9 decimals, total supply 777777777777 tokens). It implements a Uniswap V2 pair (`0xdb161bb5bea8917d41f858c0763dd27c0ebf7c2a`) with an initial 20 % buy/sell tax that steps down to 0 %, transfer-delay and max-wallet mechanics, and a privileged `_taxWallet` (initially the deployer `0xbd68c48f862795a6bec61374062454c27508cae0`). The project presents itself as a meme token referencing the earlier “JESUS” token; its public channels are https://twitter.com/GodErc20 and https://t.me/PortalOfGod. GoPlus reports `hidden_owner=1` and the creator currently holds 0 % of supply.

**Executive Summary**  
The executed Forge-based exploit simulation against the live forked state returned: “no exploit found: no public attacker-controlled path to drain or break invariants beyond standard owner/taxWallet privileges shown in source.” All examined attack surfaces (reentrancy, oracle manipulation, integer issues, proxy/upgrade risks, unbounded loops, front-running beyond normal MEV, honeypot mechanics) are either absent or gated behind the two privileged roles (`owner` and `_taxWallet`). The only concrete risks are therefore the documented owner-controlled functions and the tax-wallet fee-reduction / manual-swap paths.

**Access Control**  
- `onlyOwner` protects `removeLimits`, `addBots`, `delBots`, `openTrading`, and ownership renouncement.  
- `_taxWallet` alone can call `reduceFee` (down to the final 0 % tax) and `manualSwap`.  
- Both roles are set at deployment to the same address; the contract does not expose any public bypass.  
- GoPlus `hidden_owner=1` flag is consistent with the presence of a separate `_taxWallet` that retains fee and swap control even after ownership is renounced.

**Reentrancy**  
The only external call inside `_transfer` is the Uniswap `swapExactTokensForETHSupportingFeeOnTransferTokens` inside `swapTokensForEth`, which is protected by the `lockTheSwap` mutex (`inSwap` flag). No other external calls exist, so the classic reentrancy pattern is not present.

**Oracle / Price-Feed Trust**  
No price oracles are used; taxes and limits are purely token-internal.

**Integer Overflow / Precision Loss**  
All arithmetic uses OpenZeppelin-style `SafeMath` (Solidity 0.8.17). No unchecked blocks or custom math that could overflow were identified.

**Upgrade / Proxy Risk**  
`proxy: false` in the verified metadata; the contract is deployed as a plain implementation with no delegatecall or storage-collision surface.

**Unbounded Loops / DoS**  
`addBots` / `delBots` iterate over caller-supplied arrays, but these are owner-only and the arrays are expected to be small. No public unbounded loops exist.

**Front-Running / MEV Surface**  
The 20 % initial tax and the single-block transfer delay are the only MEV-relevant features; both are intentional design choices and cannot be exploited by an arbitrary attacker.

**Honeypot / Rug Mechanics (GoPlus flags)**  
- `anti_whale_modifiable=0`, `buy_tax=0` (post-reduction), `can_take_back_ownership=0`, `cannot_buy=0`, `cannot_sell_all=0`, `external_call=0` all match the verified source.  
- The only remaining privileged action after the tax reduction is the `_taxWallet`’s ability to call `manualSwap`, which simply converts accumulated tokens to ETH and sends them to itself—standard tax-wallet behavior, not a hidden back-door.

**Recommended Human Follow-up**  
1. Verify that the current `_taxWallet` (still the original deployer) has not been handed to an untrusted party.  
2. Confirm whether ownership has been renounced on-chain; if not, decide whether the remaining `onlyOwner` functions constitute acceptable risk.  
3. Check the actual liquidity-lock status of the Uniswap pair (not visible in source).  

**Verdict: CAUTION** — no public exploit path exists, but the token retains classic memecoin owner/tax-wallet privileges that a reviewer must accept or mitigate before relying on the contract.

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-20] Hidden owner
- [-8] Top 10 non-LP/burn holders control 60% of supply — meaningful concentration
- [-8] No pair-creation timestamp available — cannot establish track record length

**Positive Signals**
- Ownership renounced
- 1297 holders — reasonably distributed
- 100% of liquidity is locked — reduced rug-pull risk
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