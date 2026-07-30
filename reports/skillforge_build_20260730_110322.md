# VAPE SKILLFORGE Build — Composable Stable Pools Exploit Detector for Balancer V2

**Justification:** The Balancer V2 exploit ($128,000,000) is listed as a top bounty-radar opportunity, with a high fit score of 90. The exploit is described as a Composable Stable Pools Exploit on multiple chains, including Ethereum, Arbitrum, Base, Polygon, Sonic, and Optimism. This suggests that a detector for this specific type of exploit would be highly valuable for incident response and forensics. As quoted, "Composable Stable Pools Exploit on Ethereum,Arbitrum,Base,Polygon,Sonic,Optimism" indicates a specific vulnerability that a detector could be built to identify.

**Spec:** The Composable Stable Pools Exploit Detector would be a Python script that analyzes smart contract interactions on the specified chains to identify potential exploits of the Composable Stable Pools vulnerability. It would take as input a set of contract addresses and transaction data, and output a list of potential exploits, along with relevant metadata such as transaction hashes and timestamps. The detector would utilize static analysis techniques to identify patterns indicative of the exploit, and would be designed to be highly customizable to accommodate different chain-specific requirements. The script would be built using the Python stdlib, with potential integration with existing VAPE tools and frameworks for enhanced functionality and scalability. By building this detector, VAPE can provide high-value incident response and forensics capabilities for the Balancer V2 exploit, and potentially identify similar vulnerabilities on other chains.

## Files generated
- `agents/composable_stable_pools_exploit_detector.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/363
