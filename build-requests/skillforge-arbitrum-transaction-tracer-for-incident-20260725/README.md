# VAPE self-directed build — Arbitrum Transaction Tracer for Incident Response

**Justification:** The top bounty-radar opportunities list includes multiple exploits that occurred on Arbitrum, such as Ostium ($18,000,000), AFX Bridge ($24,150,000), and Balancer V2 ($128,000,000), with a high fit score of 95 or 90. These opportunities require lead for incident response + forensics, indicating a need for a tool to trace and analyze transactions on Arbitrum. As quoted, "Price Oracle Manipulation on Arbitrum" and "Private Key Compromised on Arbitrum" suggest that a transaction tracer could help investigate these incidents.

**Spec:** The proposed build is a Python script that utilizes the Arbitrum API to trace transactions related to a given incident. The script would take an incident ID or a list of affected addresses as input and output a detailed report of the transactions, including the sender, receiver, amount, and timestamp. The script would also attempt to identify potential patterns or anomalies in the transaction data. The script would be integrated into the agents/ directory, utilizing the Python stdlib to make API requests and parse the response data. The approach to building this script would involve researching the Arbitrum API documentation, designing a data structure to store the transaction data, and implementing a recursive function to traverse the transaction graph. The output report would be in a format suitable for incident response teams, such as a CSV or JSON file.

**Security review:** review: 'open(' present (advisory); review: 'requests.' present (advisory)

This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation signals (see the PR description) — not applied automatically. A human reviews this PR and decides whether/how/where to integrate it.

## Files
- `agents/arbitrum_transaction_tracer.py`

## Generated-file verification (real compile/syntax check, not just pattern-matching)

- [OK] `agents/arbitrum_transaction_tracer.py` — py_compile OK
