# VAPE SKILLFORGE Build — Composable Stable Pools Exploit Detector for Balancer V2 on Multiple Chains

**Justification:** The signal that motivates this build is the Balancer V2 exploit (exploit $128,000,000) listed under TOP BOUNTY-RADAR OPPORTUNITIES, which mentions a Composable Stable Pools Exploit on multiple chains including Ethereum, Arbitrum, Base, Polygon, Sonic, and Optimism. This high-priority justification category indicates a real, high-fit opportunity that would require a specific capability that VAPE doesn't have yet. The fact that it's a high-value exploit with a high fit score (90) suggests that having a detector for this specific type of exploit would be highly valuable for incident response and forensics.

**Spec:** The proposed build is a detector for Composable Stable Pools Exploits on multiple chains, specifically designed for Balancer V2. The detector would take in blockchain data (e.g. transaction logs, smart contract interactions) as input and output alerts or notifications when a potential exploit is detected. The detector would need to be chain-agnostic, able to analyze data from multiple chains (Ethereum, Arbitrum, Base, etc.) and identify patterns indicative of the Composable Stable Pools Exploit. The build would utilize VAPE's existing smart-contract security capabilities, particularly static and dynamic analysis, to identify and flag suspicious activity. The detector would be implemented in Python, leveraging VAPE's stdlib-first approach for agents, and would integrate with existing tools and playbooks for incident response and forensics. The scope of the build would be limited to a single, focused detector, implementable in a single pass, with a clear set of inputs, outputs, and alerting mechanisms.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
