# VAPE Proactive HACK Sweep — Del404

**Target:** `0x9A27f0A9d45Dd49230C026Ebe6A344A180877C79` (chain 1)  
**Date:** 2026-07-24T05:55:01Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (72/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**

The target is the Del404 token (symbol: Del404) at 0x9A27f0A9d45Dd49230C026Ebe6A344A180877C79 on Ethereum mainnet. It is an 11 266-byte verified contract named Del404Protocol (Solidity 0.8.19, non-proxy) that trades on Uniswap. Market data shows ~$78 k liquidity, very low 24 h volume (~$160), 97 holders, and no associated websites or social links. The creator (0x36bcc86f3ff09ae379c1db8a33ad88fb117232f5) holds ~0.13 % of supply; the largest holder is a contract (~0.80 %). GoPlus reports no buy tax, no modifiable anti-whale mechanics, no hidden owner, and no external-call or honeypot flags.

**Executive Summary**

Only a fragment of the Solady `LibString` library was supplied; the core Del404Protocol logic is not available for review. Recon data (GoPlus, Etherscan, DEXScreener) shows no standard rug or honeypot signals. With only 97 holders and low liquidity the token carries typical micro-cap risks, but no concrete evidence of the examined vulnerability classes was found in the provided data.

**Access Control**  
No ownership-related flags appear in GoPlus output (hidden owner = 0, can_take_back_ownership = 0). No source-level owner or role checks could be examined.

**Honeypot / Rug Mechanics**  
GoPlus explicitly reports `cannot_buy = 0`, `cannot_sell_all = 0`, `buy_tax = 0`, and `external_call = 0`. No contradictory on-chain signals were present in the holder or market data.

**Recommended Human Follow-up**  
- Retrieve and review the complete verified source on Etherscan for any owner-gated functions, mint/burn logic, or transfer hooks.  
- Confirm the top contract holder (0x7b8cedf3f880cb2c823679c0a34967988cfcc6a4) is not a privileged router or fee collector.  
- Test buy/sell transactions on a fork with the current liquidity pool to verify absence of hidden fees or transfer restrictions.  
- Check whether the contract implements any ERC-404-style NFT mechanics that could introduce reentrancy or DoS vectors.

**Verdict: CAUTION**

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-10] Owner not renounced (0x36bcc86f3ff09ae379c1db8a33ad88fb117232f5) — can still act on the contract
- [-8] Low holder count (97)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

### Positive Signals
- Trading 886+ days without a known incident in this scan
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