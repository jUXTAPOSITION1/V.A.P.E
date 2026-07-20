# Secret Network — Threat Analysis

**Date:** 2026-06-19  
**Loss:** $4.67M  
**Chains:** Secret  
**Analysis by:** VAPE  
**Generated:** 2026-07-19T09:47:51Z

---

**Secret Network — Unbacked Mint via ICS-20 (2026-06-19)**

**Loss:** $4.67 M  
**Chain:** Secret  
**Classification:** Unbacked Mint via ICS-20

### What is known
VAPE’s pipeline recorded a single incident on Secret Network on 19 June 2026 in which $4.67 M was extracted through an unbacked mint that used the ICS-20 IBC transfer path. No public post-mortem, on-chain analysis, or incident report was located in this scan cycle.

### Technical root cause
Unknown. The classification “Unbacked Mint via ICS-20” indicates that the attacker was able to create Secret-wrapped tokens without corresponding backing on the source chain, but no transaction hashes, contract addresses, or exploit details have been published or independently verified.

### Why it matters
ICS-20 is the standard IBC token-transfer packet format used by the Cosmos ecosystem. Any flaw that allows an unbacked mint on the receiving chain (whether through mis-configured escrow logic, packet replay, or a chain-specific mint hook) can be replicated across other IBC-connected chains that implement the same pattern. Secret’s use of encrypted state adds an extra verification challenge: observers cannot easily inspect the mint logic or the state of the escrow account in real time.

### Take-away for protocol teams
Until a public write-up or on-chain reconstruction appears, the only actionable signal is the classification itself: any ICS-20 receive path that can trigger a mint must be reviewed for:
- strict escrow accounting that ties minted supply 1:1 to locked tokens,
- replay protection on incoming packets,
- correct handling of denom traces when the receiving chain uses a custom token-factory or encrypted module.

No further technical detail is available from the current data set.
