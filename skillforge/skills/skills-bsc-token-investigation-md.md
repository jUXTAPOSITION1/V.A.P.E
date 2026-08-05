# skills/bsc-token-investigation.md

## when-to-use
Run before interacting with any BSC (chain 56) token contract when recent findings show patterns of owner-not-renounced, unlocked liquidity, or concentrated holders (e.g., targets 0x500A02a2, 0x965BA6FD, 0x000008D2, 0x02Fca66C).

## step-by-step procedure
1. Invoke `agents/investigate.py` with target address and chain=56.
2. Cross-check output against `token_safety` wrapper for honeypot/mint/liquidity signals.
3. Run `contract_recon` on the same address to confirm owner status and proxy flags.
4. Feed holder concentration and liquidity-lock data into `market_data` for liquidity age and distribution metrics.
5. Record verdict (REJECT/CAUTION) and write report to `intel/investigations/investigation-YYYYMMDD-HHMMSS-<addr>.md`.

## quality gates
- All four wrappers (`agents/investigate.py`, `token_safety`, `contract_recon`, `market_data`) must return without error.
- Score threshold: <30 triggers REJECT; 30-70 triggers CAUTION with explicit owner/liquidity notes.
- Report must list at least the top three negative factors from real findings (owner, concentration, liquidity lock).

## limitations
- Only validated on BSC chain 56; no coverage for other chains.
- Relies on public on-chain data at time of run; does not detect off-chain team actions.
- `agents/investigate.py` confidence ranges 0.75-0.9; manual review required for borderline scores.

_Distilled 2026-08-05T08:42:01Z from real SKILLFORGE memory._
