# skills/base-meme-token-vetting.md

## Title
Base Meme Token Rejection Vetting

## When-to-use
Run on any fresh Base (8453) token launch flagged by base_sweep.py or hack_feed when name/symbol matches known brands (e.g., Claude, OpenAI) or deploys via Clanker-style permissionless factories.

## Step-by-step procedure
1. Execute `agents/investigate.py --target <CA> --chain 8453` to generate initial score and metadata.
2. Call `contract_recon` + `token_safety` on the target to confirm deployer history and prior verdicts (e.g., OpenAI serial pattern).
3. Run `wallet_trace` on deployer to surface linked addresses and previous REJECT 0/100 cases.
4. Query `market_data` + `base_rpc` for liquidity depth, pair age, and 24h volatility.
5. Cross-check `fear_greed` and `hack_feed` for macro context and known Clanker rug correlations.
6. Write verdict to `intel/investigations/investigation-YYYYMMDD-HHMMSS-<CA>.md` with explicit score (0/100 for impersonation + low liq + fresh pair).

## Quality gates
- Must produce SIGNAL: HIGH/NEUTRAL/REJECT header before publishing.
- All negative factors (impersonation [-35], factory template [-20], liquidity <$100, pair <2 days) must be explicitly listed with point deductions.
- Report path and timestamp must match `agents/run.py` bounty-cycle output format.

## Limitations
- Only covers Base chain 8453; no coverage for other networks.
- Relies on public on-chain data—misses off-chain team claims.
- False negatives possible on non-Clanker factories with identical risk patterns.

_Distilled 2026-07-23T08:36:19Z from real SKILLFORGE memory._
