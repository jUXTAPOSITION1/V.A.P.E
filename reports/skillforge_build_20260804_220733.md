# VAPE SKILLFORGE Build — evm address poisoning detector for vault churn

**Justification:** "THORChain DEX (exploit $10,000,000) (defillama-hack, fit 95, $10,000,000): Vault Churn Address Poisoning on Bitcoin,Ethereum,Base,BSC. Lead for incident response + forensics." This is the only remaining top-95 fit whose technique (address poisoning via vault churn) has no matching entry in ALREADY BUILT; all other 95/90-fit items map directly to existing detectors (arbitrum oracle manip tracer, arbitrum private key compromised detecto, layerzero oft bridge exploit detector, etc.).

**Spec:** Python stdlib CLI (agents/ style) that ingests an EVM tx list or block range, flags address-poisoning patterns where a near-identical vanity address receives churned vault funds within N blocks of a legitimate target, outputs JSON report with tx hashes, poisoned addresses, and fund-flow graph. Inputs: chain (ethereum|base|arbitrum|bsc), start_block or tx_csv, optional vanity distance threshold. No new deps; uses only stdlib + optional web3.py if already in env. Single-pass script that can later feed the existing incident-response playbook.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
