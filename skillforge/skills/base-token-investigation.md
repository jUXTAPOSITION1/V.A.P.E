# Base Token Investigation

## When to Use
Run on any Base (8453) contract address flagged by hack_feed or community broadcast before wallet interaction or liquidity provision.

## Step-by-Step Procedure
1. Execute `agents/investigate.py` with target contract and chain flag:  
   `python agents/investigate.py --target 0x87c6c398F811A462d623D24cAfEcaf0F0E553b08 --chain 8453`
2. Pipe output through `token_safety` and `contract_recon` wrappers for holder/liquidity cross-check.
3. Feed results to `market_data` and `fear_greed` for macro context.
4. Record verdict in `intel/investigations/investigation-*.md` using the template from broadcast-2026-07-24-14.md.
5. If score ≤ 43, emit REJECT tag and update permanent record via `agents/broadcast.py`.

## Quality Gates
- 16/16 toolcheck passes (verified daily).
- Score calculation must include all four penalties: holder count, liquidity < $2k, unaudited status, mintable supply.
- Final verdict matches observed thresholds: 35/100 or 43/100 = REJECT.

## Limitations
- Only processes Base chain data; no cross-chain coverage.
- Relies on public liquidity and holder snapshots at runtime.
- Default REJECT for any unaudited/anonymous contract.

_Distilled 2026-07-25T08:11:52Z from real SKILLFORGE memory._
