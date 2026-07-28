# VAPE SKILLFORGE Build — Unlimited Approval Exploit Detector for Base and Ethereum

**Justification:** The signal that motivates this build is the Matcha exploit, which had a fit of 90 and a loss of $13,430,000. The exploit was caused by an unlimited approval exploit on Base and Ethereum. As stated in the signal, "Matcha (exploit $13,430,000) (defillama-hack, fit 90, $13,430,000): Unlimited Approval Exploit on Base,Ethereum. Lead for incident response + forensics." This suggests that there is a need for a tool that can detect unlimited approval exploits on these chains.

**Spec:** The Unlimited Approval Exploit Detector would be a Python script that uses the EVM on-chain investigation and forensics capabilities to analyze smart contracts on Base and Ethereum. The script would take a contract address as input and output a report indicating whether the contract has an unlimited approval vulnerability. The detector would use static analysis to identify potential vulnerabilities in the contract's code. The script would be designed to be used as part of an incident response and forensics workflow, allowing users to quickly identify and respond to potential exploits. The detector would be built using the Python stdlib and would not require any external dependencies. The approach to building this detector would involve analyzing existing unlimited approval exploits, identifying common patterns and vulnerabilities, and developing a set of rules and heuristics to detect these vulnerabilities in contracts. The detector would be tested using a set of known vulnerable contracts to ensure its effectiveness.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
