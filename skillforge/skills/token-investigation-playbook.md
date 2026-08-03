# Token Investigation Playbook

## When-to-Use
Run on any new or flagged ERC20 address (Ethereum/Base) before interaction when bounty-cycle or hack_feed signals HIGH/CAUTION, or when token_safety returns concentrated holders/unlocked liquidity.

## Step-by-Step Procedure
1. `python agents/investigate.py --address <0xaddr> --chain 1` (or 8453) — one run internally gathers contract_recon (proxy/implementation, mint functions, owner), token_safety (top-10 holder %, LP lock %, mintable flag), wallet_trace (prior REJECT verdicts on the same deployer), and cross-checks hack_feed + market_data for matching exploit patterns (access-control, price manipulation). Writes intel/investigations/investigation-*.md with the ADI score.
2. If score ≤62 or any [-15] liquidity-unlocked flag in the report, treat as REJECT/CAUTION and stop.

## Quality Gates
- ADI score ≥85 AND 0% mintable AND ≥50% LP locked AND ≥1000 holders → PROCEED.
- Any single [-15] or deployer history match → REJECT.
- Evidence file must contain explicit holder % and lock % values.

## Limitations
Covers only on-chain metrics from agents/investigate.py; no project docs or off-chain identity verification.

_Distilled 2026-08-03T09:53:54Z from real SKILLFORGE memory._
