# Bonzo Lend — Threat Analysis

**Date:** 2026-07-11  
**Loss:** $10.05M  
**Chains:** Hedera  
**Analysis by:** xai_1  
**Generated:** 2026-07-19T05:16:06Z

---

**Bonzo Lend – Hedera Incident (2026-07-11)**

**Loss:** $10.05 million  
**Classification:** Flashloan-driven price oracle manipulation (DeFiLlama feed and VAPE rule-based match)

### What is known
On 2026-07-11, Bonzo Lend on Hedera lost approximately $10.05 million in a single incident tagged by multiple feeds as price-oracle manipulation executed via flashloan. No further on-chain details, attacker addresses, transaction hashes, or post-mortem have appeared in public sources during this collection cycle.

### Technical root cause
No public writeup or on-chain analysis is currently available. The classification alone indicates the attacker was able to move a reported price in a single block (or narrow window) that was then used for collateral valuation or liquidation logic. This is the classic pattern when a lending market reads a spot price that can be temporarily skewed with borrowed liquidity.

### Why it matters
Lending protocols that accept a manipulable price for borrowing power or liquidation thresholds create an immediate, high-value attack surface. On lower-liquidity chains or assets the cost of moving that price is often far below the extractable value, turning the oracle into the cheapest part of the exploit.

### Protocol takeaway
The only reliable mitigation for this class remains architectural: replace any single-block spot price with a TWAP (or multi-source, multi-block aggregate) for all collateral and liquidation calculations. Anything narrower re-creates the exact condition that produced the $10.05 M loss on Bonzo Lend.

No additional technical specifics are confirmed at this time.
