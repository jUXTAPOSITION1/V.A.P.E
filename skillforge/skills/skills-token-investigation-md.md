# skills/token_investigation.md

**title**: Ethereum Token Safety Assessment via agents/investigate.py

**when-to-use**: Before any interaction, approval, or position in a new/low-cap ERC20 on chain 1 when holder distribution, liquidity lock status, or pair age are unknown.

**step-by-step procedure**:
1. Execute `python agents/investigate.py --target <contract> --chain 1` (example targets: 0x31fcdee0aEa658E0F7A3D275fD126f6faf3b6D82, 0x851F679A5eDfb16E7cF1ad157C6995b7E7F333F2).
2. Capture the generated report at `intel/investigations/investigation-*.md` and the numeric score/verdict.
3. Apply thresholds directly from observed runs: score 0 = REJECT, 52 = CAUTION, 100 = PROCEED.
4. Cross-check any non-zero risk factors listed in the report content (holder count, top-10 concentration, liquidity lock %, pair age, audit status).
5. Re-run the identical command on the same target after 24 h if initial verdict is CAUTION.

**quality gates**:
- Report must contain explicit score and verdict fields.
- All automated checks listed in content must be present; missing fields trigger re-execution.
- Only accept PROCEED when score = 100 and content states “clean across automated checks”.

**limitations**:
- Limited to chain 1; no coverage for other networks.
- Snapshot is time-bound (pair age and liquidity values change rapidly).
- Does not replace manual review of upgradeability or proxy implementation.

_Distilled 2026-07-31T08:55:31Z from real SKILLFORGE memory._
