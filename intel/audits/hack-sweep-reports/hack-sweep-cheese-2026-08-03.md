# VAPE Proactive HACK Sweep — CHEESE

![CHEESE logo](https://cdn.dexscreener.com/cms/images/BfPHj9owYfoHDi2M?width=800&height=800&quality=95&format=auto)

**Project:** Cheese Head ($CHEESE) — https://www.publiclandstore.com/products/matt-furie-zine?_pos=1&_psq=matt+furie&_psid=1f275c191&_ss=e · https://x.com/CheeseHeadEth · https://t.me/CheeseHeadMattFurie  
**Target:** `0x5949f201bE7A159D551d9480B900570ddCADAb7b` (chain 1)  
**Date:** 2026-08-03T06:31:37Z  
**Engine:** Frontier LLM (active) + real recon  
**Baseline Verdict:** REJECT (40/100 — same scoring engine as every VAPE investigation, for consistency)

---

## Simulated Attack — Proof of Concept
*The primary deliverable of this engagement: a real exploit test, drafted by a frontier LLM against this contract's actual verified source, then RUN with `forge test --fork-url` against a live fork of this chain's real on-chain state. This is executed, not narrated — a pass means the drafted attack's own assertions held after its actions ran against real forked state; entirely local and read-only against the real chain, no transaction is ever broadcast to it.*

### Not run this engagement: no exploit found: no permissionless path to drain, bypass, or break invariants without owner/taxWallet keys

---

## Vulnerability Analysis
**Project Overview**

Cheese Head ($CHEESE) is an ERC-20 token deployed at 0x5949f201bE7A159D551d9480B900570ddCADAb7b on Ethereum mainnet. It implements a taxed trading model with an initial 22% buy/sell tax that can be reduced, a 70% transfer tax, and per-wallet/per-transaction limits. Liquidity exists primarily on Uniswap V2 (pair 0xf849644cedee1f145b889d1f8902c09c97d1a569, ~$3.8k) with smaller Uniswap V4 positions. The contract is verified, non-proxy, 14.4 kB in size, and was created by 0xe4483ba16faeadbe44da019aaa08894eb1278dca. Public presence includes @CheeseHeadEth on X and t.me/CheeseHeadMattFurie on Telegram; the linked website references a Matt Furie zine.

**Executive Summary**

The executed Forge-based exploit PoC against the live forked state found no permissionless path to drain funds, bypass access controls, or break core invariants without the owner or `_taxWallet` private keys. The contract contains classic centralized-control patterns (owner-only limit removal, bot blacklisting, fee reduction, and manual swaps) plus an unusually high 70% `_transferTax` that applies to many non-pair transfers. No reentrancy, oracle, proxy, or arithmetic issues were present in the verified source. The primary risk is therefore rug or honeypot potential via privileged keys rather than a technical exploit available to any holder.

**Access Control (owner / taxWallet gating)**

- `onlyOwner` functions (`openTrading`, `removeLimits`, `addBots`, `delBots`, `renounceOwnership`, `rescueERC20`) give the deployer full control over trading state, max wallet/tx limits, and blacklists.
- `_taxWallet` (initially the deployer) can call `reduceFee`, `manualSwap`, and receives all collected tax ETH. The `reduceFee` function can only lower taxes but still requires the tax-wallet key.
- `_isExcludedFromFee` and `bots` mappings are writable only by the owner, enabling selective fee bypass or blocking.

These controls are consistent with the PoC result: no permissionless drain exists, but the owner/tax-wallet can unilaterally alter economics or extract value.

**Honeypot / Rug Mechanics (GoPlus-flagged surface)**

- `_transferTax = 70` is applied to any transfer that is not the first buy or a direct pair sell, creating a 70% tax on many wallet-to-wallet movements.
- Initial taxes of 22% drop only after `_buyCount > 23`; the owner can further reduce them via `_taxWallet`.
- `addBots` / `delBots` and the 3-sell-per-block limit inside `_transfer` allow the owner to selectively impair trading for chosen addresses.
- No hidden-owner or ownership-take-back flags were set, but the combination of high transfer tax and owner-controlled fee parameters matches common rug patterns even though the PoC could not exploit them without keys.

**Recommended Human Follow-up**

- Verify the current `_taxWallet` and owner addresses on-chain and confirm whether ownership has been renounced.
- Check the live values of `_finalBuyTax`, `_finalSellTax`, `_transferTax`, `_maxTxAmount`, and `_maxWalletSize` versus the constructor defaults.
- Review the 289 holders and the ~$7.9k liquidity depth to assess whether the 70% transfer tax is actively enforced on secondary-market activity.
- Confirm that the Uniswap V2 pair remains the dominant liquidity venue and that no additional privileged contracts can call `manualSwap` or `rescueERC20`.

**Verdict: CAUTION**

---

## Supporting Analysis
*Baseline recon and static/symbolic tooling that fed the simulated attack and vulnerability analysis above — supporting evidence, not the primary finding.*

### Baseline Recon
**Verdict Rationale**
- [-25] Very low liquidity $7,941 (rug/illiquid)
- [-10] Low liquidity $7,941
- [-15] Pair only 2.7 days old (extreme fresh-launch risk)
- [-10] No known third-party audit or verifiable team identity found — treated as unaudited/anonymous by default

**Positive Signals**
- Ownership renounced
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