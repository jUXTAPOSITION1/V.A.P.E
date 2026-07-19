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

| 2026-07-13 | auto | 0xeC0d015979077ebDDB16f665cCF2b4022fa3Ab07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-13 | auto | 0x5E1760831750DD0Be92d115e90CfEEF207c68B07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-13 | auto | 0x36D527D75aa29101C86Ae420EA46Dd7bE34b529a (DEXE) | deep_investigation | REJECT (33/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-13 | auto | 0x832b55B0fA6397ca9e63B8c15DAdeF3f6E44614c (DUAL) | deep_investigation | REJECT (33/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-13 | auto | 0x0c880f6761F1af8d9Aa9C466984b80DAb9a8c9e8 (PENDLE) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-13 | auto | 0x29cC30f9D113B356Ce408667aa6433589CeCBDcA (ELSA) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-13 | auto | 0x80F994E39286C2c624EE9f647365C7DC1f4e3FbF (ELSA) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-14 | auto | 0x459d9e517DdAb532FCA6e34e760fe202829ACcCf (DEXE) | deep_investigation | REJECT (3/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-14 | auto | 0x18cD0eF93Be7F3bB052885Bc2d66947aC7799b07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-14 | auto | 0x3c8B650257cFb5f272f799F5e2b4e65093a11a05 (VELO) | deep_investigation | CAUTION (68/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-14 | auto | 0x1Bdf71EDe1a4777dB1EebE7232BcdA20d6FC1610 (CES) | deep_investigation | PROCEED (82/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-14 | auto | 0xb77FB1083E2544969Cc2949912bF5376C1876b07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-14 | auto | 0xaa036928c9c0Df07d525B55ea8EE690Bb5a628C1 (EVAA) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-14 | auto | 0x3221BAEB0c2745e39A1dbA73CD413361b7f5Fe13 (ETD) | deep_investigation | CAUTION (50/100) | Very few holders (30) — thin, easily manipulated distribution | +7d |

| 2026-07-14 | auto | 0xed327E881bdDe8a134E6FDdcf4a64881F86A3b07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-15 | auto | 0x904567252D8F48555b7447c67dCA23F0372E16be (KITE) | deep_investigation | PROCEED (90/100) | Owner not renounced (0x725e318e181d7e1bb26c0d77ddc58ff6ba463fd8) — can still act | +7d |

| 2026-07-15 | auto | 0xB2000000000000000000007BF6D5cBb0E24cB301 (BRIAN) | deep_investigation | REJECT (30/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-15 | auto | 0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb (wstETH) | deep_investigation | CAUTION (74/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-15 | auto | 0xCFB287565201763743A77c556dcA44A673d0a777 (RISE) | deep_investigation | CAUTION (70/100) | High sell tax 20% | +7d |

| 2026-07-15 | auto | 0x932dDc710C39dF4838958553E8f2Da8331CBcB07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-15 | auto | 0x2c3a8Ee94dDD97244a93Bc48298f97d2C412F7Db (AKE) | deep_investigation | PROCEED (90/100) | Violent 24h move +215% (volatility/manipulation) | +7d |

| 2026-07-15 | auto | 0x9b88500C69CEa66c329Abd1C494319B197fb8453 (BRIAN) | deep_investigation | CAUTION (70/100) | Low liquidity $30,055 | +7d |

| 2026-07-15 | auto | 0x3ecced5b416e58664f04a39dD18935eB71D33B15 (BRIAN) | deep_investigation | CAUTION (75/100) | Owner can change balances (rug surface) | +7d |

| 2026-07-15 | auto | 0x2376A4fC1AE90A329B4B41fbb7611b9E76b9Eb07 (BRIAN) | deep_investigation | REJECT (30/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-15 | auto | 0x71A64AA011566A33F79eE48ed1491752AEc254b6 (BRIAN) | deep_investigation | REJECT (28/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-15 | auto | 0x693B8De886712f0039EEf578bbE5aC7ea3B598CE (doji) | deep_investigation | PROCEED (80/100) | Owner not renounced (0x05e40bcba6e5e2f23c4bd87544c42ba3363c1aeb) — can still act | +7d |

| 2026-07-15 | auto | 0x1DE2a8dCBe56Abf971E9F2a9feC21082901ef0e5 (DOJI) | deep_investigation | REJECT (37/100) | Low holder count (134) | +7d |

| 2026-07-15 | auto | 0x0027dA8d030dC3092e7Ddb6488c52e1EE65580bc (DOJI) | deep_investigation | REJECT (35/100) | Very few holders (4) — thin, easily manipulated distribution | +7d |

| 2026-07-16 | auto | 0xF11D5aD2D7A8261E72E549eD0971c5207c049bC6 (SMB) | deep_investigation | REJECT (14/100) | Transfers can be paused by owner | +7d |

| 2026-07-16 | auto | 0x0531f1e647b5ca694012EAb6Be2a9215B4070ba3 (Doji) | deep_investigation | CAUTION (65/100) | Violent 24h move +405% (volatility/manipulation) | +7d |

| 2026-07-16 | auto | 0xb2000000000000000000003833eD6154d9fA0f01 (DOJI) | deep_investigation | REJECT (20/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-16 | auto | 0xC17c30e98541188614dF99239cABD40280810cA3 (RISE) | deep_investigation | REJECT (23/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-16 | auto | 0x199084f1390B58493096Ff73Ec74c68164ba8453 ($COBIE) | deep_investigation | CAUTION (70/100) | Violent 24h move +1684% (volatility/manipulation) | +7d |

| 2026-07-16 | auto | 0x038ad3c2241F54492E25a8A419Fd3E4494C6dB07 (DOJI) | deep_investigation | REJECT (10/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-16 | auto | 0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB (WETH.e) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-16 | auto | 0x664645ba2018507b4f336a1529122C5f982b2Ac8 (BRIAN) | deep_investigation | PROCEED (80/100) | Pair 9.8 days old — under two weeks, no track record yet | +7d |

| 2026-07-16 | auto | 0x936AD605716234B77b7A61CDb95D6b6A188Da8E8 (YIELD) | deep_investigation | REJECT (35/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-16 | auto | 0x3b8db18e69d6686Ad9371A423aFe3Dd1065C94f1 (ESP) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-16 | auto | 0x8453Cf5Dd4840072b5Da025Ca4c5caA13c192b07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-17 | auto | 0x0f020434fFa8649B6994781EeD1D1522411807Ee (YIELD) | deep_investigation | CAUTION (70/100) | Very few holders (20) — thin, easily manipulated distribution | +7d |

| 2026-07-17 | auto | 0x6fBBbD8bFB1cd3986B1D05e7861a0f62F87DB74b (VSN) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-17 | auto | 0xC4aa3dc36ba618EAA0D76A89750430181cFc7b07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-17 | auto | 0x311935Cd80B76769bF2ecC9D8Ab7635b2139cf82 (SOL) | deep_investigation | PROCEED (90/100) | Owner not renounced (0x3eff766c76a1be2ce1acf2b69c78bcae257d5188) — can still act | +7d |

| 2026-07-17 | auto | 0xF0Cb96a4011A0A6F73d100c7080Bf8020D10F87a (ARMSTRONG) | deep_investigation | PROCEED (90/100) | Violent 24h move +18481% (volatility/manipulation) | +7d |

| 2026-07-17 | auto | 0xf4B385849f2e817E92bffBfB9AEb48F950Ff4444 (EGL1) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-17 | auto | 0xB20000000000000000000029784108e9706A0001 (BRIAN) | deep_investigation | REJECT (30/100) | Very few holders (2) — thin, easily manipulated distribution | +7d |

| 2026-07-17 | auto | 0x13A466998Ce03Db73aBc2d4DF3bBD845Ed1f28E7 (PHAR) | deep_investigation | CAUTION (72/100) | Owner not renounced (0xd23f124bbbc958bcddc0ce624042b48154222fde) — can still act | +7d |

| 2026-07-17 | auto | 0xB200000000000000000000EAe54086e2363C0eC1 (BRIAN) | deep_investigation | REJECT (30/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-17 | auto | 0xFdcD8be9DD37CF982472d30eeeE4ec50A0296953 (IBNAi) | deep_investigation | CAUTION (55/100) | Owner not renounced (0x0f5f60ad3e43839d6b9d4a6d1d8eded24db73c32) — can still act | +7d |

| 2026-07-17 | auto | 0x4c433F4EF87fE506A7eED2fD1d822CBED411eBA3 (TSG) | deep_investigation | PROCEED (80/100) | Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act | +7d |

| 2026-07-17 | auto | 0x43976a124e6834b541840Ce741243dAD3dd538DA (RAIN) | deep_investigation | REJECT (37/100) | Owner not renounced (0xaff5289591653038340645fdc1e1ed3a3b52e436) — can still act | +7d |

| 2026-07-17 | auto | 0x5FbE62dfdB805E1711d36Db0c2E22a2D77195BA3 (TSG) | deep_investigation | CAUTION (50/100) | Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act | +7d |

| 2026-07-17 | auto | 0xB200000000000000000000717E391850b706fc01 (TSG) | deep_investigation | REJECT (10/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-17 | auto | 0xb20000000000000000000009a08Ff22fAC1d7F82 (mr_lightspeed) | deep_investigation | REJECT (5/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0xF94b5C5651c888d928439aB6514B93944eEE6F48 (YLD) | deep_investigation | CAUTION (57/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-18 | auto | 0x769607fcC19a53d2b56771617E8aFC4AC4E4C0cc (YIELD) | deep_investigation | REJECT (35/100) | Very few holders (26) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0x5F980Dcfc4c0fa3911554cf5ab288ed0eb13DBa3 (GITLAWB) | deep_investigation | PROCEED (90/100) | Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act | +7d |

| 2026-07-18 | auto | 0xB73a50850680c66CF6C14e5276A7f6149f0b7f63 (GITLAWB) | deep_investigation | CAUTION (78/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-18 | auto | 0xAE45b8faE07fFB2E5f4373bFCB6f4Bd827A45b07 (Gitlawb) | deep_investigation | REJECT (45/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-18 | auto | 0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270 (WPOL) | deep_investigation | PROCEED (100/100) | address has no contract code (EOA or not deployed) | +7d |

| 2026-07-18 | auto | 0x7B492118AFC2b4EB3Da5Cc4253795885FEB2154B (Gitlawb) | deep_investigation | REJECT (47/100) | Low holder count (58) | +7d |

| 2026-07-18 | auto | 0xB33F6E70535584c2aCa18335305797C16f1ad589 (AKE) | deep_investigation | REJECT (35/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0x8c81B4c816d66D36c4bF348BdeC01dBCbC70E987 (BRIUN) | deep_investigation | PROCEED (90/100) | Violent 24h move +481% (volatility/manipulation) | +7d |

| 2026-07-18 | auto | 0x152b9d0FdC40C096757F570A51E494bd4b943E50 (BTC.b) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-18 | auto | 0xB20000000000000000000033C22aB099bbF76001 (COBIE) | deep_investigation | REJECT (30/100) | Very few holders (5) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0x0675E10c848Ca8a725d186f7626dD5247cEED9Ea (MidnightProtocol) | deep_investigation | REJECT (45/100) | Very few holders (14) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0x89837420864ca27f36c6847B9d1E8Dbe0C6EccdB (MidnightProtocol) | deep_investigation | CAUTION (65/100) | Violent 24h move +1095% (volatility/manipulation) | +7d |

| 2026-07-18 | auto | 0xb20000000000000000000038a46caFDcb2B3a301 (BRIUN) | deep_investigation | REJECT (10/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0x243666616819d6D0A106A769efB1Ee8890Ae2F73 (BRIAN) | deep_investigation | CAUTION (58/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-18 | auto | 0x21b8dfe779671e54A4009F1882B955e0F6d1e0A2 (BRIAN) | deep_investigation | CAUTION (58/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-18 | auto | 0xb200000000000000000000cFe0745F0793F0206b (COBIE) | deep_investigation | REJECT (40/100) | Very few holders (4) — thin, easily manipulated distribution | +7d |

| 2026-07-18 | auto | 0x02C4347ECE55Fe108c9A29e96221615f13070791 (COBIE) | deep_investigation | PROCEED (90/100) | Low liquidity $13,998 | +7d |

| 2026-07-19 | auto | 0xb20000000000000000000012141bf387DD37eB01 (BRIUN) | deep_investigation | REJECT (5/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-19 | auto | 0x72f3a461B2C631dffe9A2A6A95dC816b78279B07 (BRIAN) | deep_investigation | REJECT (30/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |
