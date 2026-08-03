# Token Investigation Playbook

## When-to-Use
Run on any new or flagged ERC20 address (Ethereum/Base) before interaction when bounty-cycle or hack_feed signals HIGH/CAUTION, or when token_safety returns concentrated holders/unlocked liquidity.

## Step-by-Step Procedure
1. `python agents/investigate.py --target <0xaddr> --chain 1` (or 8453) — produces intel/investigations/investigation-*.md with ADI score.
2. `python agents/contract_recon.py --target <0xaddr>` — confirm proxy/implementation, mint functions, owner.
3. `python agents/token_safety.py --target <0xaddr>` — extract top-10 holder %, LP lock %, mintable flag.
4. `python agents/wallet_trace.py --target <deployer>` — check prior REJECT verdicts on same deployer.
5. Cross-check `python agents/hack_feed.py` and `python agents/market_data.py` for matching exploit patterns (access-control, price manipulation).
6. If score ≤62 or any [-15] liquidity-unlocked flag, output REJECT/CAUTION and stop.

## Quality Gates
- ADI score ≥85 AND 0% mintable AND ≥50% LP locked AND ≥1000 holders → PROCEED.
- Any single [-15] or deployer history match → REJECT.
- Evidence file must contain explicit holder % and lock % values.

## Limitations
Covers only on-chain metrics from agents/investigate.py; no project docs or off-chain identity verification.

_Distilled 2026-08-03T09:53:54Z from real SKILLFORGE memory._
