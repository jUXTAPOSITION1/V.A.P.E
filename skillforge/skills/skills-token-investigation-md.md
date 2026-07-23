# skills/token_investigation.md

## Title
Base Token Safety Investigation via investigate.py

## When-to-use
Run on any Base (8453) token address flagged by base_sweep.py, virtuals_sweep.py, macro_sweep.py, or bounty-cycle reports when holder count <200, liquidity <$10k, or prior deployer verdicts exist.

## Step-by-step procedure
1. Execute `agents/investigate.py --target <address> --chain 8453`.
2. Capture output fields: score, verdict, metadata.report path, and all penalty lines (e.g., "[-30] Same deployer...", "[-25] Very low liquidity").
3. Cross-check against hack_feed and token_safety for matching prior CAUTION/REJECT entries on same deployer.
4. Write verdict and full penalty list to intel/investigations/investigation-*.md.
5. If score <50 or liquidity <$5k, mark REJECT and halt further analysis.

## Quality gates
- Must produce numeric score + explicit verdict (REJECT/CAUTION).
- All penalties must reference verifiable on-chain data (holders, liquidity, deployer history).
- Report path must be created under intel/investigations/.

## Limitations
- Heuristics under-weight verified institutional wrappers (e.g., cbBTC).
- Scores drift over time; re-run required after 7 days.
- Cannot detect off-chain team identity or future mint events.

_Distilled 2026-07-22T08:35:07Z from real SKILLFORGE memory._
