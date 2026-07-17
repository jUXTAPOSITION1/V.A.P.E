```markdown
# skills/ledger-drift-review.md

**Title:** Ledger Drift Review

**When-to-use:** After new investigation reports or security_sweep.py runs show score changes on previously PROCEED/CAUTION targets; triggered by review_ledger.py findings where verdicts worsened (e.g., 90→70, 88→73, 70→35).

**Step-by-step procedure:**
1. Run `agents/review_ledger.py` to scan recent verdicts against current `agents/investigate.py` outputs.
2. For each drifted address (e.g., 0x31A626996E36a302b06b27283C561d5926db6b7c), execute `agents/investigate.py --target <address> --chain <id>` and compare new score to stored metadata.old_score.
3. Cross-reference with `agents/security_sweep.py` report (intel/reports/security-*.md) and `hack_feed` for matching exploits (e.g., Ostium-style oracle issues).
4. Apply `token_safety` and `contract_recon` wrappers on the address to quantify factors: mintable supply, owner privileges, liquidity.
5. Update verdict in ledger only if new score meets quality gate; log to intel/investigations/.

**Quality gates:**
- Drift threshold: ≥15-point drop from prior score.
- Minimum data sources: investigate.py + security_sweep.py + token_safety.
- Require explicit metadata fields (old_verdict, new_verdict, old_score, new_score) before commit.

**Limitations:**
- Relies solely on existing agent outputs; no new static analysis (slither/aderyn) or on-chain calls beyond listed wrappers.
- Drift detection only; does not prevent initial false PROCEED verdicts.
```

_Distilled 2026-07-17T08:16:44Z from real SKILLFORGE memory._
