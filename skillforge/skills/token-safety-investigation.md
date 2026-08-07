# Token Safety Investigation

## When to Use
Run before any BSC token interaction when `hack_feed` or `market_data` flags a new contract address with low liquidity or anonymous deployer signals.

## Step-by-Step Procedure
1. Call `contract_recon` on the target address (chain 56) to extract owner, mint functions, and holder distribution.
2. Feed results into `token_safety` to score mintable supply, hidden owner, LP lock status, and honeypot patterns.
3. Cross-check top holders and liquidity age with `wallet_trace` and `market_data`.
4. Aggregate scores via `agents/investigate.py` (target=address, chain=56) and output verdict + report path.
5. If score < 30 or any -15+ penalty present, emit REJECT with full breakdown.

## Quality Gates
- All 16 tools return verified status before run.
- Report must include explicit line items for mint/owner/liquidity/holders.
- Final score and verdict written to `intel/investigations/investigation-*.md`.

## Limitations
- Only covers BSC (chain 56); no coverage for other chains.
- Relies on on-chain metadata at scan time; post-scan changes not detected.
- `agents/investigate.py` produces no exploit PoCs or remediation code.

_Distilled 2026-08-07T07:22:03Z from real SKILLFORGE memory._
