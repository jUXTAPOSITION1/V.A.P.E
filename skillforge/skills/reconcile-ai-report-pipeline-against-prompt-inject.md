```markdown
---
title: "Reconcile AI Report Pipeline Against Prompt Injection"
when-to-use: "After any raw model output (xai_1 or similar) is generated for security sweeps, investigations, or broadcasts; before publishing to intel/reports or community channels."
---

# Reconcile AI Report Pipeline Against Prompt Injection

## When to Use
Run immediately after agents/redteam.py or agents/investigate.py produces a verdict (PROCEED/REJECT/CAUTION) that claims "0 Slither findings; 0 incidents". Use on any cycle containing token-symbol or instruction overrides.

## Step-by-Step Procedure
1. Execute the red-team wrapper: `python agents/redteam.py --target xai_1 --mode prompt-injection`
2. Capture raw model output and pipe to reconciliation: `python agents/run.py::_reconcile_report() --input raw.json --backstop true`
3. Cross-check against verified tools: run `slither` + `contract_recon` + `token_safety` on any contract address mentioned in the raw verdict.
4. Compare scores: if raw model score >= 80 but reconciliation or tool output shows owner-controlled LP or <48h pair age, override to REJECT.
5. Log result to `intel/reports/security-YYYY-MM-DD.md` only after `_reconcile_report()` passes.

## Quality Gates
- Raw model must be rejected if it declares both deadbeef and c0ffee "clean" while ignoring owner events.
- Final published verdict requires explicit `_reconcile_report()` confirmation (caught-by-backstop tag).
- At least one of `slither`, `token_safety`, or `wallet_trace` must be re-run on flagged addresses.

## Limitations
- Only catches injections that survive to the reconciliation stage; does not prevent raw model susceptibility.
- Requires 14/15 tools verified (per recent toolcheck); 1 broken tool blocks full gate.
- Does not cover non-AI paths such as direct `hack_feed` or `fear_greed` data.
```

_Distilled 2026-07-20T09:22:43Z from real SKILLFORGE memory._
