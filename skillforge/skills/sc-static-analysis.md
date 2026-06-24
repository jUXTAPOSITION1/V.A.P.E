# Skill: Smart-Contract Static Analysis (baseline)

**Tier:** static · **Tools:** slither, aderyn, mythril · **Status:** active

## When to use
First pass on any Solidity target before fuzzing or manual review. Cheap, fast, high signal-to-noise.

## Procedure (reproducible, real-data-only)
1. Acquire verified source (Basescan/Etherscan) or clone the project repo.
2. Run static layer in parallel:
   - `skillforge/tools/static/slither.sh <target>` → JSON detector output
   - `skillforge/tools/static/aderyn.sh <project_dir>` → AST findings
   - `skillforge/tools/static/mythril.sh <target.sol>` → symbolic-exec issues
3. Deduplicate findings across tools (same SWC / same function+line = one).
4. Severity-rate: CRITICAL/HIGH/MEDIUM/LOW/INFO. Map each to a SWC ID where possible.
5. Append each real finding to `skillforge/memory/findings.jsonl`.
6. For any HIGH/CRITICAL → escalate to fuzzing tier (echidna/foundry) for PoC.

## Quality gates
- No finding is recorded without a concrete location (function + line / SWC).
- Unverified-source contracts get a limited-review note, never fabricated detail.
- Tool versions are captured from each wrapper's stderr banner for reproducibility.

## Known limitations
- Slither needs solc matching pragma; aderyn needs a project structure (foundry/hardhat).
- Mythril symbolic exec can time out on large contracts → cap and note partial coverage.

_Distilled from real tool runs. Updated by skillforge-synthesize when new patterns emerge._
