# VAPE SKILLFORGE Build — thorchain vault-churn address-poisoning tracer

**Justification:** The THORChain DEX (exploit $10,000,000) entry in opportunities.json is the only top bounty-radar item whose root cause ("Vault Churn Address Poisoning on Bitcoin,Ethereum,Base,BSC") has no matching detector or tracer in the already-built list; all other high-fit Arbitrum/Ethereum/LayerZero/approval/pool cases are already covered by existing tools.

**Spec:** Python CLI (agents/ style, stdlib + web3.py) that ingests a list of churned vault addresses + poisoned recipient lists, walks EVM chains (Base/Eth first) for inbound transfers to those addresses within a configurable block window, flags any that match known poisoning patterns (identical low-value transfers from multiple victims, same calldata prefix), and emits a compact JSON report with tx hashes, victim addresses, and value moved. Inputs: JSON file or CLI args for vault list + start block; output: stdout JSON + optional markdown summary. Single-pass script, no new deps beyond what's already used for on-chain forensics.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
