```markdown
# skills/base-token-verdict-override.md

## Title
Base Token Verdict Override

## When-to-use
After `agents/investigate.py` returns CAUTION/REJECT on a Base (8453) token showing violent 24h move, low holder count, or fresh pair, and `agents/base_sweep.py` has already reported the target.

## Step-by-step procedure
1. Run `agents/base_sweep.py` and capture the report path in `intel/reports/base-YYYY-MM-DD-HH.md`.
2. Execute `agents/investigate.py` on the flagged address (chain 8453) and record the generated `intel/investigations/investigation-*.md`.
3. Open the investigation report and extract the penalty list (e.g., "Very few holders", "Pair only X days old", "Contract source UNVERIFIED").
4. Manually verify: confirm ERC-20 is non-proxy, owner key burned, and source contains zero mint/fee logic using `contract_recon` + `base_rpc`.
5. Pull top-10 holder distribution and 48h funding addresses via `wallet_trace`.
6. If immutable parameters + renounced ownership are confirmed and no mint/tax flags exist, override to PROCEED and log disagreement reason in the same investigation file.
7. Update `intel/broadcasts/broadcast-*.md` with the revised verdict.

## Quality gates
- Source verified and non-template before override.
- No mint or fee logic present in bytecode.
- Owner renounced or burned.
- 24h volume vs liquidity ratio documented.

## Limitations
- Still constrained by <30 holders and <4-day pair age for price stability.
- Does not cover off-chain coordination or bridge funding patterns.
```

_Distilled 2026-07-18T07:58:46Z from real SKILLFORGE memory._
