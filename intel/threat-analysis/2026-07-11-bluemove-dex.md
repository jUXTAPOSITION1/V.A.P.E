# BlueMove DEX — Threat Analysis

**Date:** 2026-07-11  
**Loss:** $0.529M  
**Chains:** Sui  
**Analysis by:** VAPE  
**Generated:** 2026-07-24T10:09:17Z

---

**Threat Analysis Report: BlueMove DEX Hack on Sui Chain**

On 2026-07-11, the BlueMove DEX protocol on the Sui chain suffered a loss of $0.529M due to a hack classified as an LP-share inflation attack by DeFiLlama's real hacks feed, and more specifically as a first-depositor share-price/donation inflation attack by VAPE's rule-based technique classification.

Unfortunately, despite conducting a thorough search, no public writeups or detailed analysis of this specific incident were found. The pre-fetched web searches (query 1 and query 2) did not return any results, and additional live web searches did not yield any concrete information on the attack flow, transaction hashes, attacker addresses, or root cause.

Given the lack of publicly available information, it is challenging to provide a detailed technical analysis of the incident. However, based on the classification of the attack, it is likely that the hack exploited a vulnerability related to the protocol's handling of liquidity provider (LP) shares, allowing the attacker to manipulate the share price and inflate their own shares.

The known prevention measure for this vulnerability class, as stated, involves seeding vaults with a minimum initial deposit or using virtual shares to block first-depositor share-price manipulation. Protocol teams can take away from this incident the importance of implementing such measures to prevent similar attacks.

In the absence of more detailed information, it is essential for protocol teams to review their own LP share management mechanisms and consider implementing robust security measures to prevent similar exploits. Further research and analysis are needed to determine the exact root cause and attack flow of this incident.

**Recommendations:**

1. Review LP share management mechanisms to ensure they are secure and resistant to manipulation.
2. Consider implementing seed vaults with minimum initial deposits or using virtual shares to prevent first-depositor share-price manipulation.
3. Continuously monitor the protocol for potential vulnerabilities and stay up-to-date with the latest security measures and best practices.

**Sources:**

* DeFiLlama's real hacks feed (for classification and incident data)
* VAPE's rule-based technique classification (for classification and known prevention measures)
* Live web searches (for additional information, which yielded no results)
