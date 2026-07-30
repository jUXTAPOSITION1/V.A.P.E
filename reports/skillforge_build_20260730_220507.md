# VAPE SKILLFORGE Build — Composable Stable Pools Exploit Detector for Balancer V2 on Multiple Chains

**Justification:** The Balancer V2 exploit ($128,000,000) is listed as a top bounty-radar opportunity, with a high fit score of 90. The exploit is specifically mentioned as a "Composable Stable Pools Exploit" on multiple chains, including Ethereum, Arbitrum, Base, Polygon, Sonic, and Optimism. This suggests that a detector for this specific type of exploit would be highly valuable for incident response and forensics. As quoted from the signal: "Balancer V2 (exploit $128,000,000) (defillama-hack, fit 90, $128,000,000): Composable Stable Pools Exploit on Ethereum,Arbitrum,Base,Polygon,Sonic,Optimism."

**Spec:** The proposed detector would be a Python script that utilizes the VAPE's existing smart-contract security capabilities to identify potential Composable Stable Pools Exploits on the specified chains. The script would take in chain-specific data as input and output a list of potential exploit instances, along with relevant transaction hashes and contract addresses. The detector would be built using VAPE's Python stdlib-first approach for agents/ and would leverage existing static and dynamic analysis tools to identify the exploit patterns. The development approach would involve analyzing the known exploit instances, identifying common patterns and characteristics, and implementing a detection algorithm that can identify similar patterns in new, unseen data. The detector would be designed to be chain-agnostic, allowing it to be easily adapted to different chains and ecosystems.

## Files generated
- `agents/composable_stable_pools_exploit_detector.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/365
