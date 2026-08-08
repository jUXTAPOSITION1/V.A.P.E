# skills/bsc-token-risk-investigation.md

## When to use
Run on any BSC token address (chain 56) showing thin distribution, fresh pair, or anonymous deployer signals before any on-chain interaction or capital allocation.

## Step-by-step procedure
1. `contract_recon 0xTARGET --chain 56` — confirm proxy status, implementation address, and ownership state.
2. `token_safety 0xTARGET --chain 56` — extract holder count, top-2 non-LP concentration, and liquidity USD value.
3. `market_data 0xTARGET --chain 56` — retrieve pair age and 24h volume.
4. `wallet_trace 0xTARGET --chain 56 --depth 1` — identify deployer and any prior rejected contracts.
5. `hack_feed 0xTARGET` — check for linked CVE or known malicious patterns.
6. Aggregate scores: subtract 20 for <3 holders, 15 for >95% top-2 control, 25 for liquidity <$10k, 15 for pair <1 day, 10 for no audit, 8 for upgradeable proxy. Output verdict (REJECT ≤20, CAUTION 21-60, ACCEPT >60).

## Quality gates
- All tool calls must return non-empty JSON; retry once on timeout.
- Final report must cite at least three independent signals from the list above.
- Confidence field populated only when holder and liquidity data both present.

## Limitations
- Does not replace manual Slither/aderyn review of verified source.
- False negatives on tokens with fake liquidity or hidden mint functions.
- Relies on public RPC data; mev-protected or private pools invisible.

_Distilled 2026-08-08T06:59:24Z from real SKILLFORGE memory._
