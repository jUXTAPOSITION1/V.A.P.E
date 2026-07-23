# VAPE Proactive HACK Sweep — SWOGE

![SWOGE logo](https://cdn.dexscreener.com/cms/images/f2ab3021fa9b31a2f7f68e105d930c6dab8058f289dcb54cca745a209137b3a8?width=800&height=800&quality=95&format=auto)

**Project:** Swole Doge ($SWOGE) — https://swoledoge.vip · https://x.com/swoledogeerc20 · https://t.me/SwoleDogeERC20  
**Target:** `0x0000C9AF57138af42f22729A4DE46c650E602EF4` (chain 1)  
**Date:** 2026-07-23T06:06:21Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** CAUTION (62/100 — same scoring engine as every VAPE investigation, for consistency)

---

## AI Deep-Dive Analysis
**Project Overview**  
SwoleDoge (SWOGE) is a Uniswap V2 ERC-20 memecoin at 0x0000C9AF57138af42f22729A4DE46c650E602EF4 on Ethereum. It claims no utility beyond the meme (KnowYourMeme link in source). The contract was deployed by 0x00a3624d57f70667b95f52fd982dbf826ef2214e (now 0 balance). Official links are https://swoledoge.vip, https://x.com/swoledogeerc20 and https://t.me/SwoleDogeERC20. Liquidity (~$43k) sits in the single UniswapV2 pair 0xbb2548978657174ecc360a7d1e033840cd8284b2; 146 holders, ~37% of supply in the LP.

**Executive Summary**  
The verified source (v0.8.26, non-proxy) implements a classic taxed token with owner-controlled parameters, a 50% transfer tax after the first buy, 24% initial buy/sell taxes that only drop after 24 buys, per-block sell caps, and bot-blacklist functionality. No reentrancy, overflow, or oracle issues exist in the supplied code. The dominant risks are centralized control and punitive transfer taxation that can trap holders. GoPlus flags align with the code (no hidden owner, modifiable taxes via owner/taxWallet).

**Access Control (Owner / TaxWallet)**  
- `Ownable` is standard; `TradeOn()`, `LimitDone()`, `addBots()`, `unkillBots()`, and `removeTransferTax()` are gated by `onlyOwner`.  
- `_taxWallet` (set to deployer) alone can call `reduceFee()` and `manualSwap()`.  
- `bots` mapping blocks transfers for any address added by owner. These controls remain live unless ownership is renounced (not visible in the provided source or recon data).

**Transfer Tax & Honeypot Mechanics**  
- `_transferTax = 50` is applied on every transfer once `_buyCount > 0` (line ~140).  
- First buy pays `_initialBuyTax = 24`; subsequent buys and all sells also pay high tax until `_buyCount > 24`.  
- `_transfer` explicitly routes tax to the contract and then to `_taxWallet` via `sendETHToFee`. Combined with the 50% transfer tax, this creates a strong economic disincentive for any post-launch movement of tokens.

**Unbounded Loops / DoS Surface**  
- `addBots(address[])` and `unkillBots(address[])` iterate the supplied array without length caps. Owner-only, so practical impact is limited, but a single large call could theoretically exceed block gas limits.

**Front-Running / MEV Surface**  
- `TradeOn()` performs the initial liquidity add and enables trading in one transaction; sandwiching or delayed execution is possible.  
- Per-block sell counter (`sellCount < 3`) and `lastSellBlock` logic adds MEV surface around the 3-sell window.

**Recommended Human Follow-up**  
1. Confirm current owner and whether `renounceOwnership()` has been called.  
2. Verify live values of `_transferTax`, `_buyCount`, `_maxTxAmount`, and `_maxWalletSize` on-chain.  
3. Check if the taxWallet has already called `reduceFee()` or `manualSwap()`.  
4. Review recent large transfers for evidence of the 50% tax being applied in practice.

---

## Baseline Recon (same checks as every VAPE investigation)
### Verdict Rationale
- [-8] Low holder count (146)
- [-10] Low liquidity $43,000
- [-10] Violent 24h move +812% (volatility/manipulation)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

### Positive Signals
- Ownership renounced
- Trading 667+ days without a known incident in this scan
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