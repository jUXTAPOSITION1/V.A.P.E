# VAPE self-directed build — Arbitrum Transaction Tracer for Defillama-Hack Incidents

**Justification:** The presence of multiple high-value exploits on Arbitrum, such as Ostium ($18,000,000), AFX Bridge ($24,150,000), and others, indicates a strong need for a specialized tool to trace and analyze transactions on this chain, particularly in the context of incident response and forensics. As quoted, these incidents are labeled as "defillama-hack" with high fit values, suggesting a specific type of vulnerability or attack vector that VAPE could target with a new capability.

**Spec:** This tool would be a Python script utilizing the Arbitrum API to trace transactions related to known defillama-hack incidents. It would take incident IDs or contract addresses as input and output a detailed transaction graph, including relevant wallet addresses, transaction hashes, and timestamps. The script would be designed to work within VAPE's existing Python stdlib-first approach for agents. To build this, I would start by researching the Arbitrum API and its capabilities for transaction tracing, then design a data model to represent the transaction graph. The script would be implemented in a modular fashion, allowing for easy integration with existing VAPE tools and workflows. By focusing on Arbitrum and defillama-hack incidents, this tool would directly address a high-priority, high-value opportunity for VAPE to provide incident response and forensics leadership.

**Security review:** clean

This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation signals (see the PR description) — not applied automatically. A human reviews this PR and decides whether/how/where to integrate it.

## Files
- `arbitrum_transaction_tracer.py`

## Generated-file verification (real compile/syntax check, not just pattern-matching)

- [OK] `arbitrum_transaction_tracer.py` — py_compile OK
