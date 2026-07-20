# WUSD.fi/Glove — Threat Analysis

**Date:** 2026-05-25  
**Loss:** $0.2M  
**Chains:** Ethereum  
**Analysis by:** VAPE  
**Generated:** 2026-07-19T20:39:36Z

---

**WUSD.fi / Glove – Sybil Abuse Incident (Ethereum, 25 May 2026)**

**Loss:** ≈ $200 k  
**Classification:** Sybil Abuse (per DeFiLlama feed)

### What is known
On 25 May 2026 the WUSD.fi / Glove deployment on Ethereum suffered a $0.2 M loss attributed to Sybil Abuse. No on-chain transaction hashes, attacker addresses, or post-mortem have been publicly linked in the sources reviewed during this cycle. No independent write-ups, Twitter threads, or protocol disclosures were returned.

### Root cause
Unknown. The DeFiLlama label indicates the loss resulted from an attacker controlling multiple identities to exploit an incentive or distribution mechanism, but no contract-level details (e.g., flawed airdrop claim logic, repeated reward claims, or governance vote manipulation) are available from public records.

### Why the incident matters
Even at modest size, the event confirms that Sybil vectors remain effective against protocols that rely on unverified or lightly gated on-chain actions. The absence of any public forensic data after the fact limits the ability of other teams to learn concrete patterns or signatures.

### Take-away for protocol teams
Until a detailed breakdown is published, the only verifiable signal is that whatever anti-Sybil controls (or lack thereof) were in place on 25 May 2026 proved insufficient. Teams should treat this as a reminder to instrument and monitor identity-weighted actions rather than assuming existing heuristics will hold. No further technical mitigations can be derived from currently available information.
