# Token Investigation Playbook

## When to Use
Run before any interaction with an unknown ERC-20/bridge token on Ethereum or Base when `hack_feed` or `bounty-cycle` signals appear. Produces REJECT/CAUTION/NEUTRAL verdicts using live on-chain data.

## Step-by-Step Procedure
1. Execute `agents/investigate.py --target <address> --chain <1|8453>` (wraps `contract_recon` + `token_safety`).
2. Feed output into `agents/base_sweep.py` or `agents/macro_sweep.py` when chain TVL or F&G data is required.
3. Aggregate results via `agents/run.py` to emit `SIGNAL: HIGH|NEUTRAL` and write `intel/investigations/investigation-*.md`.
4. Apply quality gate: score ≤30 → REJECT, 31-60 → CAUTION, >60 → review `market_data` + `fear_greed`.
5. Log verdict and report path to `reports/bounty_report_*.md`.

## Quality Gates
- All 16 tools verified via `toolcheck` before run.
- Must include explicit dilution, pause, holder count, liquidity, and audit fields.
- Report must start with `SIGNAL:` marker for bounty-cycle acceptance.

## Limitations
- Relies on unaudited/anonymous default scoring; false negatives on low-liquidity tokens (<$25k).
- No cross-chain message verification (see Verus-Ethereum lesson).
- `market_data` and `token_safety` must be live; broken wrappers block scoring.

_Distilled 2026-07-24T08:32:51Z from real SKILLFORGE memory._
