# New Market Trading — Threat Analysis

**Date:** 2026-05-25  
**Loss:** $3.98M  
**Chains:** Ethereum, Base, Arbitrum  
**Analysis by:** xai_1  
**Generated:** 2026-07-19T20:39:45Z

---

**New Market Trading — $3.98 M Access-Control Exploit (25 May 2026)**

On 25 May 2026 the protocol New Market Trading recorded a $3.98 million loss across its deployments on Ethereum, Base and Arbitrum. DeFiLlama’s hack feed classified the incident as an Access Control Exploit.

No contemporaneous public post-mortem, on-chain analysis, or credible third-party write-up has surfaced in the current data cycle. Consequently the precise technical root cause—whether a missing role check, an improperly initialized owner, a proxy-upgrade path, or another vector—remains undocumented in open sources.

### Why the incident still matters
- The loss figure is material and occurred on three major EVM chains simultaneously, indicating the same control-surface was exposed in multiple deployments.
- Absence of any public disclosure more than a week after the event leaves downstream integrators, liquidity providers and auditors without actionable signals.

### Take-away for protocol teams
Until a verified technical breakdown is published, the only confirmed fact is that an access-control failure on at least one privileged function allowed extraction of roughly $3.98 M. Teams should treat the incident as an existence proof that their own role-management code paths require explicit verification rather than relying on the eventual appearance of a public report.
