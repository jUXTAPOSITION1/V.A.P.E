# VAPE SKILLFORGE Build — ethereum reverse mev honeypot tracer

**Justification:** "JaredFromSubway MEV Bot (exploit $7,500,000) (defillama-hack, fit 89, $7,500,000): Reverse MEV Honeypot on Ethereum. Lead for incident response + forensics." — this is the only high-fit bounty-radar opportunity whose exact technique (reverse MEV honeypot) has no matching detector in the already-built list, unlike the oracle manip, private-key, layerzero, unlimited-approval, and composable-stable cases that are already covered.

**Spec:** Python stdlib CLI (agents/ style) that takes an Ethereum tx hash or address list, fetches traces via eth RPC, flags honeypot patterns (reverted victim txs followed by attacker profit extraction in same block, selective revert-on-victim logic in contract bytecode), outputs a compact JSON report with involved addresses, profit calc, and call graph. Single-file, no external deps beyond stdlib + optional web3.py shim if already present; run as `python -m agents.mev_honeypot_tracer 0x...`.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
