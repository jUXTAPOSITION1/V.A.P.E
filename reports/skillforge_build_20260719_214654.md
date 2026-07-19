# VAPE SKILLFORGE Build — arbitrum-oracle-manip-tracer

**Justification:** "Ostium (exploit $18,000,000) (defillama-hack, fit 95, $18,000,000): Price Oracle Manipulation on Arbitrum. Lead for incident response + forensics." (top signal in opportunities.json, also echoed by Kelp/Hyperbridge/Balancer entries on Arbitrum/Base/Ethereum)

**Spec:** Python stdlib-only script (agents/oracle_tracer.py) that takes an Arbitrum tx hash + optional block range, walks the trace via eth_getTransactionReceipt + eth_getLogs for known oracle addresses (Chainlink/AggregatorV3Interface, custom feeds), extracts pre/post price values and update txs, flags anomalous deltas or stale rounds, and emits a compact JSON report with call graph and USD impact estimate. Run as `python -m agents.oracle_tracer 0x... --chain arbitrum`; output directly consumable by incident-response playbooks. Fits existing agents/ layout with zero new deps.

## Files generated
- `agents/oracle_tracer.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/227
