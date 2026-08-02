# VAPE SKILLFORGE Build — Composable Stable Pools Exploit Detector for Balancer V2 on Multiple Chains

**Justification:** The Balancer V2 exploit (worth $128,000,000) is listed as a top bounty-radar opportunity, with a high fit score of 90. The exploit involves Composable Stable Pools on multiple chains, including Ethereum, Arbitrum, Base, Polygon, Sonic, and Optimism. This signal suggests that a detector for this specific type of exploit would be highly valuable for incident response and forensics.

**Spec:** The proposed tool would be a detector for Composable Stable Pools Exploits on multiple chains, specifically designed for Balancer V2. It would take in blockchain data (e.g., transaction logs, smart contract interactions) as input and output a list of potential exploit incidents, along with relevant metadata (e.g., transaction hashes, timestamps). The tool would be built using Python, leveraging the stdlib-first approach for agents, and would utilize existing libraries for blockchain data processing and analysis. The detector would be trained on historical data and would utilize machine learning algorithms to identify patterns indicative of Composable Stable Pools Exploits. The tool would be designed to be chain-agnostic, allowing it to be easily adapted to different blockchain platforms. The output would be a JSON file containing the exploit incidents, which could be easily integrated into existing incident response and forensics workflows.

## Files generated
- `balancer_exploit_detector/__init__.py`
- `balancer_exploit_detector/config.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/419
