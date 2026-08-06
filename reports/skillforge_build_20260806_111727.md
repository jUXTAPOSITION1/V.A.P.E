# VAPE SKILLFORGE Build — Vault Churn Address Poisoning Detector for THORChain DEX

**Justification:** The signal that motivates this proposal is the THORChain DEX exploit opportunity listed in the TOP BOUNTY-RADAR OPPORTUNITIES section, which mentions "Vault Churn Address Poisoning on Bitcoin, Ethereum, Base, BSC" with a fit of 95 and a bounty of $10,000,000. This specific exploit type is not mentioned in the ALREADY BUILT list, and the high fit and bounty values indicate a strong need for a detector that can identify such exploits.

**Spec:** The Vault Churn Address Poisoning Detector for THORChain DEX would be a Python script that analyzes transaction data on the THORChain DEX to identify potential vault churn address poisoning exploits. It would take as input a dataset of transactions and wallet addresses, and output a list of potentially poisoned addresses along with supporting evidence. The script would utilize the Python stdlib and potentially integrate with existing VAPE tools for data ingestion and analysis. The approach to building this detector would involve researching the specifics of vault churn address poisoning exploits, developing a set of heuristics to identify suspicious patterns in transaction data, and testing the detector against a dataset of known exploits and legitimate transactions to refine its accuracy. The detector would be designed to be extensible to support multiple chains, including Bitcoin, Ethereum, Base, and BSC.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
