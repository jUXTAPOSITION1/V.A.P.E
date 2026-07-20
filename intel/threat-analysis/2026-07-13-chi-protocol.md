# Chi Protocol — Threat Analysis

**Date:** 2026-07-13  
**Loss:** $0.009M  
**Chains:** Ethereum  
**Analysis by:** VAPE  
**Generated:** 2026-07-19T05:15:56Z

---

**Chi Protocol Flashloan Exploit – July 13, 2026 (Ethereum)**

**Loss:** $9,000  
**Classification:** Flashloan-driven price/oracle manipulation (DeFiLlama: Flashloan Accounting Logic Exploit)

### What Happened
On 13 July 2026 a single flashloan-based attack drained approximately $9k from Chi Protocol on Ethereum. The attacker used a large flashloan to distort a spot price that the protocol accepted for collateral or liquidation calculations, then closed the position within the same block. No larger follow-on activity or repeated drains have been reported.

### Technical Root Cause
Public writeups and on-chain analysis available to VAPE at publication time are effectively absent. The only confirmed signals are the loss size, the flashloan pattern, and the protocol’s reliance on a manipulable single-block spot price for sensitive accounting. No contract addresses, specific oracle contract, or transaction hashes have surfaced in credible post-mortems.

### Why It Matters
Even a sub-$10k loss demonstrates that the classic “one-block price” anti-pattern remains live in production. The economic threshold for profitable attacks has dropped so low that any protocol still using an instantaneous spot price for collateral, debt, or liquidation math is now exposed to automated or low-skill flashloan bots.

### Takeaway for Protocol Teams
The known mitigation for this vulnerability class is unchanged: replace any single-block spot price with a TWAP (or a multi-source, manipulation-resistant oracle) for all collateral, debt, and liquidation calculations. Until that change is made, the protocol remains economically viable to attack regardless of its TVL. No other compensating controls have been shown to reliably stop this vector once a flashloan can move the reference price.
