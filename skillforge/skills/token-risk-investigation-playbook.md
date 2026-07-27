# Token Risk Investigation Playbook

**When-to-use**  
High-signal bounty cycles (e.g., 4/5 REJECT verdicts) or new token deployments on Ethereum/Base/BNB Chain showing honeypot, mintable-supply, hidden-owner, or concentrated-holder flags. Use immediately after `hack_feed` or `contract_recon` surfaces an address with score ≤55/100.

## Step-by-step procedure

1. Run `contract_recon` on the target address to retrieve verified source and basic metadata.
2. Execute `token_safety` on the same address; record the numeric score and all flagged categories (honeypot, mintable, owner-not-renounced, pauseable transfers).
3. If owner or deployer address is returned, run `wallet_trace` on that address to map prior deployments and funding sources.
4. Cross-check liquidity and holder distribution via `market_data` on the primary trading pair.
5. If any critical flag remains unresolved, invoke `base_rpc` (or equivalent chain RPC wrapper) to simulate a buy-then-sell on a local fork and observe transfer/sell restrictions.
6. Log verdict (PROCEED / CAUTION / REJECT) and supporting evidence to the current bounty report.

## Quality gates
- All four tools (`contract_recon`, `token_safety`, `wallet_trace`, `market_data`) must complete without error.
- Final score must be reproducible from the raw tool outputs; any manual override requires explicit justification in the report.
- At least one on-chain simulation (step 5) executed when owner-controlled functions are present.

## Limitations
- Does not cover off-chain social or sentiment signals (use `fear_greed` separately).
- Simulation accuracy depends on accurate fork state; recent large transfers may be missed.
- Only applies to ERC-20-style tokens; non-standard or proxy-upgrade patterns require additional manual review.

_Distilled 2026-07-27T09:58:55Z from real SKILLFORGE memory._
