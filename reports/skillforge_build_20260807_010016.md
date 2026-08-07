# VAPE SKILLFORGE Build — ethereum reverse mev honeypot tracer

**Justification:** The JaredFromSubway MEV Bot opportunity (defillama-hack, fit 89, $7,500,000 exploit) is explicitly listed as "Reverse MEV Honeypot on Ethereum. Lead for incident response + forensics." No matching detector exists in the ALREADY BUILT list (the closest are oracle manip, private-key, composable pools, layerzero oft, and unlimited approvals — none cover MEV honeypot reversal or the specific churn/poisoning pattern described).

**Spec:** Python CLI in agents/ that ingests an Ethereum tx hash or victim address, pulls full trace via web3.py or etherscan, identifies the honeypot contract deployment + reversal logic (fake profit calls followed by drain), extracts the attacker-controlled addresses and fund flow, and emits a JSON report with the exact call sequence and tainted assets. Use only stdlib + web3.py; output matches the style of existing arbitrum tracers but targets this uncovered MEV pattern. Single-file script, runnable as `python agents/mev_honeypot_tracer.py --tx 0x...`.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
