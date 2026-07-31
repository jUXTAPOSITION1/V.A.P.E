# VAPE self-directed build — Arbitrum Private Key Compromised Detector

**Justification:** The AFX Bridge exploit, with a bounty of $24,150,000 and a fit of 95, is a high-priority justification for this build. As stated in the signal, "Private Key Compromised on Arbitrum" is the nature of the exploit, and having a detector for such incidents would be highly valuable for incident response and forensics. This is a specific signal that justifies building a capability to detect private key compromises on Arbitrum, which is not already covered by the existing builds.

**Spec:** The Arbitrum Private Key Compromised Detector would be a Python script that analyzes transaction data on Arbitrum to identify potential private key compromises. It would take in transaction data as input, potentially from a data scraper or an API, and output a list of potentially compromised addresses. The script would utilize the Python stdlib and potentially libraries such as web3.py for interacting with the Ethereum blockchain. The approach to building this detector would involve researching and implementing algorithms to identify suspicious transaction patterns that may indicate a private key compromise, such as unusual transaction volumes or frequencies. The detector would be designed to be used as part of VAPE's incident response and forensics toolkit, providing valuable insights into potential security incidents on Arbitrum.

**Security review:** clean

This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation signals (see the PR description) — not applied automatically. A human reviews this PR and decides whether/how/where to integrate it.

## Files
- `arbitrum_private_key_compromised_detector.py`

## Generated-file verification (real compile/syntax check, not just pattern-matching)

- [OK] `arbitrum_private_key_compromised_detector.py` — py_compile OK
