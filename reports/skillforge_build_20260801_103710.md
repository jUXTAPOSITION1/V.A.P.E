# VAPE SKILLFORGE Build — Composable Stable Pools Exploit Detector for Balancer V2 on Multiple Chains

**Justification:** The Balancer V2 exploit ($128,000,000) is listed as a top bounty-radar opportunity, with a high fit score of 90. The exploit involves Composable Stable Pools on multiple chains, including Ethereum, Arbitrum, Base, Polygon, Sonic, and Optimism. As quoted, "Composable Stable Pools Exploit on Ethereum,Arbitrum,Base,Polygon,Sonic,Optimism" is a specific signal that justifies building a detector for this type of exploit. Given the high value of the exploit and the multiple chains involved, a detector for this specific exploit would be a valuable addition to VAPE's capabilities.

**Spec:** The Composable Stable Pools Exploit Detector would be a Python script that takes in blockchain data from the affected chains and detects potential Composable Stable Pools exploits. The script would utilize VAPE's existing smart-contract security capabilities, such as static and dynamic analysis, to identify vulnerabilities in the Composable Stable Pools contracts. The detector would output a report indicating potential exploits, including the chain, contract address, and transaction hash. The script would be designed to be chain-agnostic, allowing it to be easily adapted to detect exploits on multiple chains. The detector would be built using Python's standard library, with potential integration with Hono/TypeScript for worker/ components. The approach to building this detector would involve analyzing the Composable Stable Pools contracts, identifying potential vulnerabilities, and developing a detection algorithm to identify exploits. The detector would be designed to be efficient, scalable, and easy to maintain, allowing VAPE to quickly respond to potential exploits and provide incident response and forensics support.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
