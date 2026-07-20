# Token of Power — Threat Analysis

**Date:** 2026-06-09  
**Loss:** $1.58M  
**Chains:** Ethereum  
**Analysis by:** VAPE  
**Generated:** 2026-07-19T14:49:10Z

---

**VAPE Threat Analysis: Token of Power Governance Attack**

**Incident Summary**  
On 9 June 2026, the Token of Power protocol on Ethereum lost $1.58 million through a single malicious governance proposal. DeFiLlama classified the event as a “Malicious Governance Proposal.” No further on-chain details or post-mortem reports were located in this analysis cycle.

**Known Facts**  
- Protocol: Token of Power  
- Chain: Ethereum  
- Date: 2026-06-09  
- Loss: $1.58 M  
- Attack vector: Malicious governance proposal (per DeFiLlama feed)  
- Public write-ups or technical breakdowns: none returned

**Technical Root Cause**  
No verified information is available. The classification indicates that a governance action was submitted and executed, resulting in the transfer of funds, but the proposal text, voting mechanics, timelock configuration, or any exploit of proposal execution logic remain undocumented in public sources.

**Why This Matters**  
A $1.58 M loss executed solely through the governance channel demonstrates that control of proposal approval and execution remains a single point of failure for protocols that route treasury or contract ownership through on-chain votes. The absence of any public breakdown one month after the event leaves other teams without concrete signals about what checks failed.

**Takeaways for Protocol Teams**  
Until a technical post-mortem appears, the only confirmed data point is that a governance proposal succeeded in extracting $1.58 M. Teams should treat this as a reminder that governance surfaces must be monitored and that loss amounts of this size can occur with no additional code exploit required. No further defensive recommendations can be derived from the currently available facts.
