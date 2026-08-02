# Triage Suspicious Contracts from VAPE Broadcasts

## When-to-use
When `agents/broadcast.py` or `agents/security_sweep.py` outputs CAUTION/REJECT scores or flags recent exploits (e.g., Set Protocol malicious Set& Manager Contract, access-control incidents on Ethereum/Base), use this playbook to investigate flagged addresses before PROCEED decisions.

## Step-by-step procedure
1. Run `hack_feed` to pull the latest flagged addresses and exploit metadata from the current broadcast cycle.
2. For each flagged address, execute `contract_recon` with the contract address to retrieve deployment details, verified source, and related contracts.
3. Pipe the address into `token_safety` to score malicious patterns and known exploit signatures.
4. If deployer or related wallets appear, run `wallet_trace` on the deployer address to map prior activity and linked contracts.
5. Cross-reference any identified incidents against `hack_feed` results for matching techniques (e.g., price manipulation, access control).
6. Log all outputs with confidence scores; escalate only addresses that survive all gates to manual review.

## Quality gates
- All 4 tools (`hack_feed`, `contract_recon`, `token_safety`, `wallet_trace`) must return non-empty structured output.
- Minimum 2 independent data points (recon + safety or trace) must align on risk signals.
- No PROCEED recommendation if any tool reports confidence < 0.7 or matches a listed exploit in the last 30 findings.

## Limitations
- Relies solely on the 16 verified tools; does not cover on-chain simulation or fuzzing.
- Cannot generate PoCs or confirm zero-day issues.
- Broadcast data may lag real-time chain state by up to 6 hours.

_Distilled 2026-08-02T08:29:14Z from real SKILLFORGE memory._
