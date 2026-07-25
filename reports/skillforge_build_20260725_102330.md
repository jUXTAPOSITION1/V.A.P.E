# VAPE SKILLFORGE Build — Arbitrum Price Oracle Manipulation Detector

**Justification:** The Ostium exploit, with a bounty of $18,000,000, involved Price Oracle Manipulation on Arbitrum, as stated in the signal: "Ostium (exploit $18,000,000) (defillama-hack, fit 95, $18,000,000): Price Oracle Manipulation on Arbitrum." This high-priority opportunity justifies building a detector for this specific type of exploit, as it would be a valuable tool for incident response and forensics on the Arbitrum chain.

**Spec:** The Arbitrum Price Oracle Manipulation Detector would be a Python script that analyzes on-chain data to identify potential price oracle manipulation attacks. It would take in blockchain data as input, specifically focusing on price oracle interactions, and output a report highlighting suspicious activity. The script would utilize the Python stdlib to interact with the Arbitrum blockchain, leveraging libraries such as web3.py for blockchain data retrieval. To build this detector, I would start by researching the specific characteristics of price oracle manipulation attacks, such as unusual price fluctuations or suspicious transaction patterns. Then, I would design a set of heuristics to identify these patterns in the on-chain data, and implement these heuristics in the Python script. The goal would be to create a tool that can be used to detect and respond to price oracle manipulation attacks on Arbitrum, helping to prevent future exploits like the Ostium incident.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
