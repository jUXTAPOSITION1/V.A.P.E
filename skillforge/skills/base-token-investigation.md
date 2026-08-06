# Base Token Investigation

## When-to-use
Run on any Base (8453) token address showing low liquidity, fresh deployment, or unverified source before any capital allocation or deeper analysis.

## Step-by-step procedure
1. Execute `agents/investigate.py` with target address and chain=8453.
2. Parse output for the five rejection signals: holder count == 0, liquidity lock == 0%, liquidity < $50k, pair age < 1 day, contract source UNVERIFIED.
3. If any two signals present, record verdict REJECT (score ≤ 15/100) and halt.
4. Cross-check deployer history via `agents/contract_recon.py` on the same address.
5. Log result to `intel/investigations/investigation-*.md` with exact score and signals.

## Quality gates
- Score ≤ 30/100 → automatic REJECT, no further steps.
- All five signals must be independently confirmed by the script output; do not override with external narrative.
- Final report must include the exact metadata fields: target, chain, score, verdict.

## Limitations
- Relies solely on on-chain data; misses unverified Twitter claims or off-chain identity (as seen in Asteroid 0x7a7C5a2d case).
- No coverage for verified contracts or liquidity > $100k.
- Wrapper `agents/investigate.py` must be current; older runs may miss fresh-launch age calculation.

_Distilled 2026-08-06T08:43:37Z from real SKILLFORGE memory._
