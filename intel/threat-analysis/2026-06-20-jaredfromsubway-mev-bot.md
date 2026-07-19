# JaredFromSubway MEV Bot — Threat Analysis

**Date:** 2026-06-20  
**Loss:** $7.5M  
**Chains:** Ethereum  
**Analysis by:** xai_1  
**Generated:** 2026-07-19T09:46:57Z

---

**Threat Analysis: JaredFromSubway MEV Bot – 20 June 2026**

**Incident Summary**  
On 20 June 2026 an Ethereum-based MEV bot operating under the name JaredFromSubway lost $7.5 million in a single event classified by DeFiLlama’s hacks feed as “Reverse MEV Honeypot.”

**Available Facts**  
- Chain: Ethereum only  
- Loss amount: $7.5 M (verified figure)  
- Technique label: Reverse MEV Honeypot (DeFiLlama classification)  
- Public technical write-ups: none returned in the current research cycle

No on-chain transaction hashes, contract addresses, attacker identifiers, or post-mortem statements have been located in open sources at the time of this report. Consequently, the precise execution path—whether it involved a poisoned liquidity pool, a malicious sandwich contract, a fake private relay, or another vector—remains undocumented.

**Root Cause**  
Unknown. No verified technical details have been published.

**Why the Incident Matters**  
A $7.5 M loss in a single MEV-bot operation is material even by 2026 standards. The “Reverse MEV Honeypot” label implies the attacker inverted the usual MEV extraction logic, turning the bot’s own search or execution infrastructure against it. Until concrete data appears, the event serves as a reminder that MEV tooling itself can become the target rather than merely the tool.

**Takeaways for Protocol and Bot Teams**  
With no public root-cause data available, concrete defensive recommendations cannot be derived from this incident. Teams should treat the event as an existence proof that sophisticated MEV operators are being successfully targeted and should monitor for any subsequent disclosures that may clarify the attack surface.

This report will be updated if verifiable technical details surface.
