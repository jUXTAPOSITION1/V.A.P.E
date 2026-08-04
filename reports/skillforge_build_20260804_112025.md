# VAPE SKILLFORGE Build — Vault Churn Address Poisoning Detector for THORChain DEX

**Justification:** The THORChain DEX exploit ($10,000,000) is listed as a top bounty-radar opportunity, with a fit of 95. The incident involves Vault Churn Address Poisoning on multiple chains, including Bitcoin, Ethereum, Base, and BSC. This specific type of exploit is not mentioned in the already built list, and having a detector for this type of exploit would be a valuable addition to VAPE's capabilities, as it would allow for incident response and forensics.

**Spec:** The Vault Churn Address Poisoning Detector would be a Python script that analyzes blockchain data to identify potential instances of vault churn address poisoning. It would take in blockchain transaction data as input and output a list of potentially poisoned addresses. The script would utilize the Python stdlib and would be integrated into the agents/ directory. To build this detector, I would first research the specifics of vault churn address poisoning and how it is executed on different chains. Then, I would develop a set of heuristics and rules to identify potential instances of this exploit. The detector would be designed to be flexible and adaptable to different chain architectures, allowing it to be used for incident response and forensics on multiple chains.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
