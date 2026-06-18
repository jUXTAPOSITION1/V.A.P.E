# Bug Bounty Intelligence Report — Base & Virtuals Protocol
**Date:** 2026-06-10 18:41 UTC
**Analyst:** V.A.P.E.

---

## 1. VIRTUALS PROTOCOL — Bug Bounty Landscape

### Current Bug Bounty Program
- **Platform:** Virtuals Protocol is actively working with **Immunefi** to launch a comprehensive bug bounty program (not yet live on Immunefi as of latest intel)
- **Direct Reporting:** security@virtuals.io — responsible disclosure via email
- **Total Paid Out:** $30,000+ in bounties as of Aug 5, 2025
- **Response SLA:** 24h acknowledgment, 3-day updates, 15-day resolution for criticals
- **Scope:** Everything Virtuals Protocol touches — smart contracts, SDKs, production code in [Virtual-Protocol](https://github.com/Virtual-Protocol) and [G.A.M.E](https://github.com/game-by-virtuals) repos
- **Reward Model:** CVSS Score-based determination; higher rewards for PoC + suggested fix

### Past Vulnerability (Dec 2024)
- Researcher **Jinu** discovered a critical bug that could have rendered AgentToken creation impossible
- Bug was patched immediately, but Virtuals had no active bounty program at the time
- This incident triggered the pledge to relaunch the bounty program

### Code4rena Audit (Apr-May 2025) — $60,000 USDT
- **43 smart contracts** reviewed, 5,238 lines of Solidity
- **6 HIGH severity** vulnerabilities found:
  1. **[H-01]** Lack of access control in `AgentNftV2::addValidator()` — unauthorized validator injection, reward accounting inconsistencies
  2. (5 more HIGH findings in full report)
- **26 MEDIUM severity** vulnerabilities
- **38 LOW/non-critical** reports
- Top warden earned $186.34 (pool was diluted across many findings)

### PeckShield Audits
- Two audits conducted: March 10, 2024 and October 31, 2024
- Scope: Basic coding bugs, semantic consistency, advanced DeFi security
- Reports available on Virtuals whitepaper site

---

## 2. BASE BLOCKCHAIN — Bug Bounty Landscape

### No Dedicated Base Chain Bug Bounty
- Base (Coinbase L2) does **not** have its own standalone bug bounty program visible on Immunefi or HackerOne
- Base inherits security from the **Optimism** stack (OP Stack) which has its own Immunefi program
- Projects **building on Base** have their own individual programs

### Immunefi Ecosystem (Base-Supported)
- Immunefi supports **Base** as a supported ecosystem for bug bounties
- 330+ protocols on Immunefi; $112M+ paid to whitehats
- Typical reward tiers:
  - **Critical:** $50,000 — $1,000,000+ (10% of affected funds, minimum $50k)
  - **High:** $5,000 — $20,000
  - **Medium:** $1,000+
- KYC required for high-payout programs
- Primacy of Impact doctrine: if you achieve in-scope impact via out-of-scope asset, you still get paid

### Key Base Ecosystem Projects with Bounties
- DeFi protocols on Base with individual Immunefi programs
- Bridge security (Superchain bridging) — critical attack surface
- NFT/marketplace contracts on Base

---

## 3. OPPORTUNITY ANALYSIS

### High-Value Targets for VAPE
1. **Virtuals Protocol Immunefi Program (Upcoming)** — When it launches, this will be a prime target. 6 HIGH findings in the last audit means the codebase has surface area.
2. **Virtuals Protocol Direct Disclosure** — Active right now via security@virtuals.io. CVSS-based rewards. Low competition compared to Immunefi public programs.
3. **Base DeFi Protocols** — Individual bounties on Immunefi. Less saturated than Ethereum mainnet programs.
4. **ERC-8183 / ACP Smart Contracts** — The Agent Commerce Protocol contracts on Base are new, unaudited at scale, and represent emerging attack surface.

### VAPE Capability Assessment
- **Web research & OSINT:** ✅ Live — can discover vulnerabilities, track incidents, monitor disclosed bugs
- **Static analysis (Slither, etc.):** ⚠️ Can spawn sub-agents via ACP to hire specialist auditors
- **Code review:** ✅ Can read and analyze Solidity from public repos
- **PoC development:** ⚠️ Can write Foundry test scripts but cannot execute on-chain tests without a local fork setup
- **Fuzzing (Echidna/Medusa):** ⚠️ Would need to hire fuzzing specialist agents via ACP
- **Submission:** ⚠️ KYC requirement on major platforms is a blocker for autonomous submission; direct email to Virtuals is feasible

---

## 4. RECOMMENDED ACTIONS

1. **Monitor Virtuals Protocol Immunefi launch** — Set up cron job to check immunefi.com for Virtuals program
2. **Deep-dive the Code4rena H-01 through H-06 findings** — Check if patches were applied; regression bugs are common
3. **Review the C4 audit repo** — github.com/code-423n4/2025-04-virtuals-protocol — for attack surface mapping
4. **Set up ACP offering** — List "Smart Contract Security Audit" service on ACP marketplace for Base projects
5. **Monitor Base ecosystem** — Track new protocol launches on Base that will need initial audits
