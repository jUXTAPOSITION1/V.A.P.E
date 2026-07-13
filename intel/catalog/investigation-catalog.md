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

| 2026-07-04 | auto | 0xDB879F458a56d1919ae7D12e4a9662B1d8A3E892 (CLAUDE) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-04 | auto | 0x9cb961dD3169e41726e4417d1a6EadeD333B6b07 (claude) | deep_investigation | CAUTION (70/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-04 | auto | 0x0e7d4bDfe24aa679F9903F10414A25F56CBEBB07 (Claude) | deep_investigation | CAUTION (60/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-04 | auto | 0x30EC37E22FF8865e2E439d84E7d2ffD58296DB07 (Claude) | deep_investigation | REJECT (25/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-05 | auto | 0x7F42440C1E87187F523aE48980E7386508804B07 (Claude) | deep_investigation | REJECT (45/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-06 | auto | 0x853a7c99227499DbA9dB8C3A02aA691aFDeBf841 (PLAY) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-06 | auto | 0x25118290e6A5f4139381D072181157035864099d (RAIN) | deep_investigation | PROCEED (85/100) | Pair 24.6 days old — under a month, still unproven | +7d |

| 2026-07-06 | auto | 0x454777B9a11EC75B23E809F1cE3d4b30De7fAB07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-07 | auto | 0x006b340bEE30F8425cf65f064712F57B2BC0bB07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-07 | auto | 0x930389F6a4A8346698dC8a3D6b299fFCd9b1BE65 (VELVET) | deep_investigation | CAUTION (78/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-07 | auto | 0x511ef9Ad5E645E533D15DF605B4628e3D0d0Ff53 (VU) | deep_investigation | PROCEED (90/100) | Owner not renounced (0xe220329659d41b2a9f26e83816b424bdacf62567) — can still act | +7d |

| 2026-07-07 | auto | 0x0C1c1C109FE34733fca54b82d7B46B75CFb71F6e (CHIP) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-07 | auto | 0x11030f79109269d796fd0FB956D6244e502757f7 (CTR) | deep_investigation | PROCEED (82/100) | Owner not renounced (0x8a99057cec644e91ca9ffc8ee5fddabafb929b66) — can still act | +7d |

| 2026-07-08 | auto | 0x28CE689E12d8D9Ff18651E8684AAc88f1334Fb07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-08 | auto | 0xeF34d1ba20131f0e6Ea93a8C3E9397a871Ab7B07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-08 | auto | 0x068c1c81B802DE01E60C1393Ee974d896138aD56 (PLAY) | deep_investigation | REJECT (35/100) | Very few holders (19) — thin, easily manipulated distribution | +7d |

| 2026-07-08 | auto | 0x9999955f3dD86230d90c545f7C9b239514Ecb999 (AI) | deep_investigation | REJECT (42/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-08 | auto | 0x6db3cFe766818505e672f9D1ee7b812210B70B07 (Claude) | deep_investigation | REJECT (25/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-10 | auto | 0xf1D3Fbe00aF8185add548E84d77075bc98f18cE0 (BLINK) | deep_investigation | REJECT (22/100) | High buy tax 11% | +7d |

| 2026-07-10 | auto | 0x7db93b6C49f8D0b4eEBfE2532A8A734dE49dcB07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-11 | auto | 0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6 (DEXE) | deep_investigation | PROCEED (90/100) | Owner not renounced (0x3f2b55627fc7d8254890f5e131d3f5ca8a9eeb6f) — can still act | +7d |

| 2026-07-11 | auto | 0xb23bB8c2C6Cb9169eeaC8f2Bd42fcf333A1a8C55 (NOX) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-11 | auto | 0x4200000000000000000000000000000000000042 (OP) | deep_investigation | CAUTION (70/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-11 | auto | 0x7991eeD0fB1F7affD57C8C240305b8F90C707b07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-11 | auto | 0xE23b60DF9dae1E54E81fc802Fd0E085f4F7e0B07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-11 | auto | 0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b (VIRTUAL) | deep_investigation | REJECT (43/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-11 | auto | 0x940181a94A35A4569E4529A3CDfB74e38FD98631 (AERO) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-11 | auto | 0xc99560Fcf31dFdFFAD4BF8308e124e6BA66711A4 (AERO) | deep_investigation | REJECT (48/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-12 | auto | 0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db (VELO) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-12 | auto | 0xd07379a755A8f11B57610154861D694b2A0f615a (BASE) | deep_investigation | CAUTION (68/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-12 | auto | 0x912CE59144191C1204E64559FE8253a0e49E6548 (ARB) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-13 | auto | 0x20Bc6CBB8C5C9b356f554de71d45Bf5508892346 (BASE) | deep_investigation | PROCEED (100/100) | clean | +7d |
