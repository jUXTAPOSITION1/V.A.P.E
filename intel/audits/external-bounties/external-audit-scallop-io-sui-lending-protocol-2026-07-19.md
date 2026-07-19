# External Bounty Engagement — Scallop Protocol (Smart Contract)

**Target repo:** `scallop-io/sui-lending-protocol` @ `main`  
**Language:** move  
**Files reviewed:** 39 (`contracts/libs/coin_decimals_registry/sources/coin_decimals_registry.move, contracts/libs/decimal/sources/decimal.move, contracts/libs/math/sources/fixed_point32.move, contracts/libs/math/sources/u128.move, contracts/libs/math/sources/u256.move, contracts/libs/math/sources/u64.move, contracts/libs/whitelist/sources/whitelist.move, contracts/libs/x/sources/ac_table.move, contracts/libs/x/sources/balance_bag.move, contracts/libs/x/sources/one_time_lock_value.move, ...`)  
**Date:** 2026-07-19T12:29Z  
**Engine:** Frontier LLM (oci_grok) — real source review, no Solidity static/symbolic tooling applies to this target's language (see module docstring for why)  

---

## AI Security Review
**Executive Summary**

The reviewed modules (coin_decimals_registry, decimal, fixed_point32_empower, u* math libs, whitelist, ac_table/wit_table/ownership, app, error, borrow_withdraw_evaluator, collateral/debt/liquidation/price/value_calculator, apm, asset_active_state, borrow_dynamics, collateral_stats, incentive_rewards, interest_model, limiter, market, market_dynamic_keys, reserve, risk_model, obligation*, borrow_referral, and test helpers) form the core of Scallop's lending protocol. They correctly leverage Move's linear types, witness/ownership patterns, and capability gating for access control. No real, attacker-reachable exploitable findings (fund loss, unauthorized state mutation, bypassable checks, or incorrect accounting) were identified. The code is defensively written with explicit assertions, epoch-delayed admin changes, and per-call liquidation caps.

**Due Diligence — Checked and Confirmed Safe**

- **Access control & ownership**: All privileged paths (AdminCap, AcTableCap, ObligationKey, Witness<T>) correctly call `ownership::assert_owner`, `whitelist::is_address_allowed`, or `obligation_access::assert_*_key_in_store`. No capability can be forged or reused across objects.
- **Obligation locking**: `lock`/`unlock` and the five boolean flags are only mutated under matching witness + key ownership; `set_lock` aborts on already-locked state.
- **Interest accrual & indices**: `accrue_all_interests` + `update_borrow_index` are idempotent per timestamp; `handle_repay` asserts the index was updated in the same tx.
- **Liquidation caps**: `max_repay_amount` enforces the 20% total-debt-value cap (or full dust-position repay) and `calculate_liquidation_amounts` proportionally scales when collateral is insufficient.
- **Market-coin price monotonicity**: `update_and_get_market_coin_price` asserts the new price ≥ previous price before writing.
- **Limiter outflow accounting**: Segment-based rolling window correctly resets on timestamp change; `add_outflow` aborts on limit breach.
- **Referral hot-potato**: `BorrowReferral` can only be created/destroyed by an authorized witness listed in `AuthorizedWitnessList`; deprecated fee fields are never touched after the v2 dynamic-field migration.
- **APM price history**: 24-slot hourly vector + min-price tracking prevents manipulation; `is_price_fluctuate` only returns true on genuine upward moves above threshold.
- **No unsafe unpack / resource duplication**: All resource types (`Obligation`, `Market`, `Reserve`, `BalanceBag`, etc.) are moved or borrowed under proper ownership; no `copy`/`drop` on value-holding structs.
- **Rounding & precision**: All divisions use explicit `mul_div` helpers or `FixedPoint32`/`Decimal` with documented direction; no unchecked integer overflow paths remain after the safe-mul checks.

**Recommended Human Follow-up**

- Run the full test suite (especially `pow_test`, `from_fixed_point32_test`, `mul_div_*_test`, `outflow_limit_test`, `apm_test`, and liquidation scenarios) under Sui Move prover or with property-based fuzzing on the decimal/liquidation math.
- Verify that the single shared `ObligationAccessStore` and `AuthorizedWitnessList` objects are initialized exactly once in production genesis.
- Confirm that the 7-epoch delay constants for model/limiter changes remain at the intended conservative value after any future re-enablement of `extend_*_change_delay`.
- Dynamic testing of the 20% liquidation cap + dust threshold under multi-debt-type obligations with concurrent price updates.

No findings warrant bounty escalation at this time.

---

## Formal Verification (Move Prover / sui-prover)
- Not run this cycle: None

---

## Methodology
1. Real source fetched directly from the target's own public GitHub repository (raw.githubusercontent.com, keyless) — byte for byte, nothing invented or paraphrased before review.
2. A frontier-tier LLM (OCI-hosted Grok 4.3 first, Vertex-tuned Gemini/Groq as fallback) reads the actual source and reasons per vulnerability class relevant to the target language/platform.
3. For Move targets: bounded formal verification via sui-prover against LLM-drafted specification properties compiled into a scaffolded package built from that same verified source — only if sui-prover is installed this run (see agents/scaffold_move_target.py's docstring for why this isn't auto-installed).
4. White-hat only: read-only source review, no on-chain interaction or exploitation attempted.

*Generated by agents/external_audit.py — VAPE's reusable external bug-bounty engagement pipeline. This report is a first-pass automated review; any finding here still needs the human verification called out above before submission.*