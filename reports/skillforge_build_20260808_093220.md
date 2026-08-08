# VAPE SKILLFORGE Build — evm address poisoning detector for vault churn patterns

**Justification:** The THORChain DEX opportunity (exploit $10,000,000, fit 95) explicitly flags "Vault Churn Address Poisoning on Bitcoin,Ethereum,Base,BSC" as the root cause, with lead for incident response + forensics. This is not covered by any already-built item (no poisoning, churn, or address-reuse detectors exist; the closest Arbitrum-specific tracers are for oracle manip and private-key compromise). It directly matches VAPE's Base/EVM forensics scope and the bounty-radar signal for a high-dollar incident needing chain-specific tracing.

**Spec:** Python stdlib CLI (agents/ style) that ingests a list of vault churn txs or addresses, builds a local graph of repeated recipient patterns with low-value decoy sends, flags poisoning clusters by reuse distance and timing, and outputs a JSON report of suspect addresses plus a simple text timeline. Inputs: CSV/JSON of tx hashes or addresses + optional chain RPC endpoints. Outputs: console report + artifacts/poisoning-report.json. Single-pass implementation: pure stdlib + optional requests for RPC if needed, no new deps.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
