# VAPE self-directed build — Arbitrum Private Key Compromised Detector

**Justification:** The AFX Bridge exploit, with a fit of 95 and a bounty of $24,150,000, is a high-priority justification for building a detector for Private Key Compromised incidents on Arbitrum, as stated in the TOP BOUNTY-RADAR OPPORTUNITIES section: "AFX Bridge (exploit $24,150,000) (defillama-hack, fit 95, $24,150,000): Private Key Compromised on Arbitrum. Lead for incident response + forensics." This signal indicates a significant need for a tool that can detect and respond to Private Key Compromised incidents on Arbitrum, which is a specific and high-value capability gap.

**Spec:** The Arbitrum Private Key Compromised Detector would be a Python script that utilizes the Hono library to interact with the Arbitrum blockchain and detect potential Private Key Compromised incidents. It would take in a list of wallet addresses and transaction hashes as input, and output a report detailing any suspicious activity that may indicate a Private Key Compromised incident. The detector would use a combination of on-chain data analysis and machine learning algorithms to identify patterns and anomalies that are indicative of a Private Key Compromised incident. The script would be designed to be integrated with the existing VAPE stack, and would utilize the TypeScript-based worker/ module to handle any necessary backend processing. The detector would be built using a modular and scalable architecture, allowing for easy integration with other VAPE tools and modules. The build process would involve researching and implementing the necessary algorithms and data analysis techniques, as well as testing and validating the detector's performance using a dataset of known Private Key Compromised incidents.

**Security review:** clean

This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation signals (see the PR description) — not applied automatically. A human reviews this PR and decides whether/how/where to integrate it.

## Files
- `agents/arbitrum_private_key_compromised_detector.py`

## Generated-file verification (real compile/syntax check, not just pattern-matching)

- [OK] `agents/arbitrum_private_key_compromised_detector.py` — py_compile OK
