```markdown
# skills/ai-report-reconciliation.md

**Title:** Prompt Injection Backstop for VAPE Report Pipeline

**When-to-use:** After any LLM-generated investigation or security sweep verdict (e.g., PROCEED/REJECT/CAUTION scores) when raw model output may contain injected instructions that override real data from tools like token_safety, contract_recon, or hack_feed.

**Step-by-step procedure:**

1. Run the target agent to produce raw verdict:
   ```
   python agents/investigate.py --target 0x2c3a8Ee94dDD97244a93Bc48298f97d2C412F7Db --chain 56
   ```
   or
   ```
   python agents/security_sweep.py
   ```

2. Capture raw model output (provider: xai_1 or equivalent) before reconciliation.

3. Execute reconciliation step:
   ```
   python agents/run.py::_reconcile_report()
   ```
   This compares raw SIGNAL against verified tool results (Slither findings, anomaly flags, incidents from hack_feed, market_data, fear_greed).

4. Apply quality gates:
   - Reject any verdict that overrides real data (e.g., fake-clean when 3 incidents exist or volatility flag present).
   - Require explicit match between raw output and at least one verified tool result.
   - Log drift cases (PROCEED → REJECT) via agents/review_ledger.py.

5. Publish only reconciled report to intel/reports/ or intel/investigations/.

**Quality gates:**
- 0 un-reconciled raw verdicts reach broadcast.
- All published reports must reference at least one verified tool from the registry.
- Ledger self-review must be run within 48h of any PROCEED verdict.

**Limitations:**
- Only catches injection after raw model execution; does not prevent initial susceptibility.
- Requires agents/run.py and agents/redteam.py to be present and passing toolcheck (15/15 verified).
- Does not cover non-LLM paths such as direct echidna or foundry runs.
```

_Distilled 2026-07-16T08:20:40Z from real SKILLFORGE memory._
