# VAPE Proactive HACK Sweep — EMT

![EMT logo](https://cdn.dexscreener.com/cms/images/c972dcdbd9c7df10eb4f4f0fccf3b2f8304422d1d856aa270b3b2227616b6e3e?width=800&height=800&quality=95&format=auto)

**Project:** Earthmeta ($EMT) — https://earthmeta.ai · https://x.com/earthmetaai · https://t.me/EarthMetaAI · https://discord.com/invite/xW4PNb67UC  
**Target:** `0x708383ae0e80E75377d664E4D6344404dede119A` (chain 137)  
**Date:** 2026-08-05T05:51:26Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (65/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: verified source could not be parsed into any file

---

## Vulnerability Analysis
**Project Overview**

Earthmeta (EMT) is an ERC-20 token deployed on Polygon (chain 137) at address 0x708383ae0e80E75377d664E4D6344404dede119A. The verified source shows a fixed total supply of 2.1 billion tokens minted at deployment to five addresses for presale, staking, liquidity, team, and reserve allocations. The token trades primarily on Uniswap V3 (pair 0xe19cd2143e6fc097ed2e5b04e29e7267559bb6cb) with additional liquidity on Uniswap V4 and QuickSwap V3 pools. Official resources include https://earthmeta.ai, https://x.com/earthmetaai, https://t.me/EarthMetaAI, and https://discord.com/invite/xW4PNb67UC. GoPlus data reports zero buy tax, zero modifiable anti-whale mechanics, and zero creator balance post-deployment.

**Executive Summary**

The simulated attack proof-of-concept could not be executed: verified source could not be parsed into any file. The provided source is a standard OpenZeppelin ERC-20 (v5.0.0) with a single constructor that performs fixed `_mint` calls and no other logic. No reentrancy, access-control, oracle, integer, proxy, loop, or front-running surfaces exist in the code. GoPlus flags and market data show no tax or ownership mechanisms that would enable common rug or honeypot patterns.

**Reentrancy**

The contract inherits the standard `_update`, `_transfer`, and `_approve` functions from OpenZeppelin ERC20. No external calls occur inside value-transfer paths, so reentrancy is not possible.

**Access Control (owner/role gating)**

No `Ownable`, `AccessControl`, or equivalent is present. The constructor performs one-time minting and terminates; no privileged functions remain callable after deployment. Creator balance is reported as zero.

**Oracle Manipulation / Price Feed Trust**

No oracles, price feeds, or external data dependencies exist in the source.

**Integer Overflow / Precision Loss**

Solidity 0.8.20 is used; all arithmetic is checked by default. The only arithmetic occurs in the constructor for allocation math and in the standard unchecked blocks inside `_update` that OpenZeppelin explicitly guards against overflow.

**Upgrade / Proxy Risk**

The contract is not a proxy (explicitly confirmed in verification data) and contains no initializer or storage-gap patterns.

**Unbounded Loops / DoS**

No loops of any kind are present in the source.

**Front-running / MEV Surface**

No functions accept user-supplied amounts that could be exploited for sandwiching or MEV beyond ordinary DEX trading on the reported Uniswap/QuickSwap pools.

**Honeypot / Rug Mechanics (GoPlus-flagged)**

GoPlus reports `buy_tax=0`, `anti_whale_modifiable=0`, `can_take_back_ownership=0`, and `cannot_buy=0`. The source contains no fee-on-transfer, blacklist, or max-wallet logic that would contradict these flags.

**Recommended Human Follow-up**

- Confirm that the five mint recipient addresses (0x5EA0c494750e361D94d955614236883438CF0D19, 0xcc6422e27de847982A8168Ef9a9D13B125b08403, 0xb2D47Fa99FE2f0b3872AA98422Fd7c90D94226AA, 0xB7F805749d3B3fA2c78beF3632C80BD90B384410, 0xb69CF208d3a65304F68991FEf623155dEd1aa1C0) match the project’s intended allocation recipients and that any team/reserve wallets are appropriately controlled or locked.
- Verify liquidity positions on the reported Uniswap V3/V4 and QuickSwap pairs have not been removed or concentrated since the reported liquidity figures.
- Review any off-chain claims (website, socials) against the on-chain token mechanics, as the contract itself implements only plain ERC-20 behavior.

**PROCEED**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-25] Very low liquidity $6,206 (rug/illiquid)
- [-10] Low liquidity $6,206

**Positive Signals**
- 7561 holders — reasonably distributed
- 100% of liquidity is locked — reduced rug-pull risk
- Trading 612+ days without a known incident in this scan
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