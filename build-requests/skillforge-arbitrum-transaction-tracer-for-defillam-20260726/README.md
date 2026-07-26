# VAPE self-directed build — Arbitrum Transaction Tracer for Defillama-Hack Incidents

**Justification:** The top bounty-radar opportunities listed, such as Ostium, AFX Bridge, and Kelp, all involve incidents on the Arbitrum chain, with a combined exploit value of over $300,000,000. As quoted, these incidents require "Lead for incident response + forensics", which implies a need for on-chain investigation and tracing capabilities specific to Arbitrum. This is a strong signal for building a tool that can help with tracing transactions on Arbitrum, particularly in the context of defillama-hack incidents.

**Spec:** The proposed build is a Python script that utilizes the Arbiscan API or a similar data source to trace transactions on the Arbitrum chain. The script would take a transaction hash or a wallet address as input and output a graph or a report detailing the transaction flow, including any relevant smart contract interactions. The script would be designed to work within VAPE's existing Python stdlib-first approach for agents/. The approach to building this would involve researching the Arbiscan API or other relevant data sources, designing a data model to represent the transaction flow, and implementing the tracing logic using Python. The goal is to create a tool that can be used to investigate and respond to incidents on Arbitrum, such as those listed in the top bounty-radar opportunities.

**Security review:** review: 'requests.' present (advisory)

This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation signals (see the PR description) — not applied automatically. A human reviews this PR and decides whether/how/where to integrate it.

## Files
- `agents/arbitrum_transaction_tracer.py`

## Generated-file verification (real compile/syntax check, not just pattern-matching)

- [OK] `agents/arbitrum_transaction_tracer.py` — py_compile OK
