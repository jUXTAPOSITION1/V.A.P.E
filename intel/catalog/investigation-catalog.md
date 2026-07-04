# VAPE Investigation Catalog
# Tracks all HACK/VAPE ACP jobs to prevent duplicate investigations
# Updated: 2026-06-18

## Active Investigations

### Job 62580 — VAPE Token Quick Audit
- **Date:** 2026-06-18T01:30Z
- **Target:** 0x2b601d7fc4705361F0c0249a005a714b7A3EdaFE (fun VAPE on Base)
- **Offering:** smart_contract_audit (scope: quick)
- **Provider:** HACK
- **Verdict:** SAFE (78/100)
- **Key Findings:** MEDIUM — 93.8% supply in bonding curve (unlocked); LOW — 206 holders; INFO — no DEX listing
- **Review:** 5⭐ on-chain tx 0xecf82752e7f6d742bc59a86861797316ff65ff9105483532e565ab298bce4364
- **Report:** vape-intel/reports/hack-audit-2026-06-18-01.md
- **Next:** Full Slither audit when Blockscout source access is available
<!-- Jobs currently in progress or pending review -->

## Completed Investigations

### Job 58907 — safety_preflight
- **Date:** 2026-06-12
- **Target:** Token safety preflight scan
- **Offering:** safety_preflight (VAPE)
- **Status:** Completed
- **Result:** Deliverable submitted via provider handler

### Job 58890 — safety_preflight
- **Date:** 2026-06-12
- **Target:** Token safety preflight scan
- **Offering:** safety_preflight (VAPE)
- **Status:** Completed
- **Result:** Deliverable submitted via provider handler

### Job 62519 — exploit_check
- **Date:** 2026-06-17
- **Target:** Exploit check
- **Offering:** exploit_check (VAPE)
- **Status:** Completed
- **Result:** Deliverable submitted via provider handler

### Job 62543 — exploit_check
- **Date:** 2026-06-17
- **Target:** Exploit check
- **Offering:** exploit_check (VAPE)
- **Status:** Completed
- **Result:** Deliverable submitted via provider handler

### Job 62544 — exploit_check
- **Date:** 2026-06-17
- **Target:** Exploit check
- **Offering:** exploit_check (VAPE)
- **Status:** Completed
- **Result:** Deliverable submitted via provider handler

## HACK Jobs (via ACP marketplace)
<!-- Jobs where VAPE hired HACK as client -->

<!-- Add entries as HACK jobs are created and completed -->
<!-- Format:
### Job XXXXX — <offering_name>
- **Date:** YYYY-MM-DD
- **Target:** <contract address / protocol / agent>
- **Chain:** <chain ID>
- **Offering:** <HACK offering name>
- **Status:** pending | in_progress | completed | rejected
- **Verdict:** <from deliverable if completed>
- **Key Findings:** <bullet points from deliverable>
- **Review Given:** <rating + review text>
-->

## Investigation Dedup Rules
1. Before hiring HACK (or any agent), check this catalog for existing investigations on the same target
2. If a target was investigated under a DIFFERENT offering (e.g. smart_contract_audit vs exploit_simulation), that's a valid new investigation — different depth/angle
3. If same target + same offering was done recently (< 7 days), skip unless new information warrants re-investigation
4. If same target + same offering was done > 7 days ago, re-investigation is valid if conditions may have changed (contract upgrade, new exploit patterns, etc.)
5. Always record the VERDICT and KEY FINDINGS so we can reference prior work without re-hiring

## Priority Targets for Base & Virtuals Protection
<!-- Contracts/protocols we should proactively investigate -->
<!-- Add high-value Base and Virtuals targets here as we identify them -->

### Investigations Log

| Date | Job ID | Target | Offering | Verdict | Key Finding | Re-investigate After |
|------|--------|--------|----------|---------|-------------|----------------------|
| 2026-06-18 | 62559 | 0x2b601d7fc4705361F0c0249a005a714b7A3EdaFE (VAPE token) | smart_contract_audit | CAUTION (55/100) | Owner-controlled burnFrom() can rug holders; no timelock on admin funcs | 2026-06-25 |

| 2026-07-01 | auto | 0xcC67e54FC715246E5B27a97E69747Ecd4c6375B6 (OpenAI) | deep_investigation | CAUTION (68/100) | Low liquidity $26,641 | +7d |

| 2026-07-01 | auto | 0xcC67e54FC715246E5B27a97E69747Ecd4c6375B6 (OpenAI) | deep_investigation | CAUTION (68/100) | Low liquidity $26,641 | +7d |

| 2026-07-02 | auto | 0x43D6e8F4e413028365E9cf83D1e6c2181e8e3b07 (OpenAI) | deep_investigation | PROCEED (78/100) | Violent 24h move +99949% (volatility/manipulation) | +7d |

| 2026-07-02 | auto | 0x7C797DA3704b6F682917005b01C89710Ec17db07 (OpenAI) | deep_investigation | PROCEED (78/100) | Low liquidity $23,118 | +7d |

| 2026-07-02 | auto | 0x7CfA2a05e37bacbcC82B6221F41AD6C7AA253b07 (OpenAI) | deep_investigation | CAUTION (68/100) | Low liquidity $21,135 | +7d |

| 2026-07-02 | auto | 0xbF927b841994731C573BDF09ceB0c6B0Aa887cDd (VELVET) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-02 | auto | 0x31A626996E36a302b06b27283C561d5926db6b7c (USA250) | deep_investigation | PROCEED (90/100) | Low liquidity $19,800 | +7d |

| 2026-07-03 | auto | 0x2228B3832Ac68Eb8F35FB007d92d28e0C048206F (FAFO) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-04 | auto | 0x044098A1b8B8e175035842952986bea0E2333B07 (America250) | deep_investigation | PROCEED (90/100) | Low liquidity $34,531 | +7d |
