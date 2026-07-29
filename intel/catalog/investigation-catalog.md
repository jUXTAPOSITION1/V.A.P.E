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

| 2026-07-19 | auto | 0xb200000000000000000000AC6A5D35756eB8Cd01 (Baseller) | deep_investigation | REJECT (30/100) | Very few holders (4) — thin, easily manipulated distribution | +7d |

| 2026-07-19 | auto | 0x4c18406Fa690fAa53E5efa899a971557251Af72d (IDL) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-19 | auto | 0xE1b7A5096343164FAe02Db10353C03cd295787c5 (Baseller) | deep_investigation | REJECT (47/100) | Low holder count (74) | +7d |

| 2026-07-19 | auto | 0x3AeE7602b612de36088F3ffEd8c8f10E86EbF2bF (BANK) | deep_investigation | PROCEED (80/100) | Owner not renounced (0x1716ece3ad0803df784ea57a38722d66305d536f) — can still act | +7d |

| 2026-07-19 | auto | 0xB2000000000000000000002b40e71C8F8609a1C8 (BASELLER) | deep_investigation | REJECT (40/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-19 | auto | 0x420FcA0121DC28039145009570975747295f2329 (COQ) | deep_investigation | PROCEED (100/100) | address has no contract code (EOA or not deployed) | +7d |

| 2026-07-19 | auto | 0xE2F097962C9E7D8BD97dC961A7a169bb0eE68b1E (Baseller) | deep_investigation | REJECT (33/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-19 | auto | 0xDcB01cc464238396E213a6fDd933E36796eAfF9f (YLD) | deep_investigation | REJECT (8/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-19 | auto | 0x2690e2f94fdc03F590Bc68C7eF3f608a0F4A0532 (VORF) | deep_investigation | REJECT (38/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-19 | auto | 0x624e2e7fDc8903165F64891672267AB0FCB98831 (SOSO) | deep_investigation | REJECT (43/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-19 | auto | 0xE8556a4641c862aa3172f95d6b4eDdd9Ada8F8D4 (GR4YS) | deep_investigation | REJECT (37/100) | Owner not renounced (0xe3b5d677199000d6f2d71bf9dd78a2c86029fca5) — can still act | +7d |

| 2026-07-19 | auto | 0x8B7DdE054BE9D180c1Be7FaE0874697374A49832 (PROS) | deep_investigation | CAUTION (70/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-20 | auto | 0xA1AFFfE3F4D611d252010E3EAf6f4D77088b0cd7 (RFI) | deep_investigation | CAUTION (65/100) | Very low liquidity $1,181 (rug/illiquid) | +7d |

| 2026-07-20 | auto | 0xB20000000000000000000024bDb2e92b8826AD30 (DUAL) | deep_investigation | REJECT (40/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-20 | auto | 0x5110EE173d24Cc03c1E836c2558C3dDaABC485bf (ZORS) | deep_investigation | CAUTION (55/100) | Very few holders (4) — thin, easily manipulated distribution | +7d |

| 2026-07-20 | auto | 0x08574906C462A0B8dA0786ca061E0C2e0C644cA0 (PLAY) | deep_investigation | REJECT (28/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-20 | auto | 0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf (cbBTC) | deep_investigation | CAUTION (74/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-20 | auto | 0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7 (WAVAX) | deep_investigation | PROCEED (100/100) | address has no contract code (EOA or not deployed) | +7d |

| 2026-07-20 | auto | 0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2 (USDT) | deep_investigation | REJECT (45/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-20 | auto | 0xa0Df17B5aC76ABaBA36E1450E2cbCd18A620C845 (FWA) | deep_investigation | CAUTION (60/100) | Owner not renounced (0x019817ad02a31b990433542097be29d97613e8cb) — can still act | +7d |

| 2026-07-21 | auto | 0x47883e389BB6be3650B0C0935b300b50a95fc072 (FWA) | deep_investigation | REJECT (35/100) | Owner not renounced (0x019817ad02a31b990433542097be29d97613e8cb) — can still act | +7d |

| 2026-07-21 | auto | 0xA12CC123ba206d4031D1c7f6223D1C2Ec249f4f3 (ZAMA) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-21 | auto | 0x431F2f58Ab87D9Fe8aCeF48b17e43A0f8d7e1eB2 (RISE) | deep_investigation | CAUTION (63/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-21 | auto | 0x230f1E241C621d5af670Dad83ebCdd18971E2995 (NES) | deep_investigation | CAUTION (77/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-21 | auto | 0x6E88056E8376Ae7709496Ba64d37fa2f8015ce3e (DEXE) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-21 | auto | 0xc2B8C6647e7bCa4Ea7CCD27b52DA849bB95652c2 (misosoupqueen) | deep_investigation | REJECT (17/100) | Same deployer has a prior CAUTION/REJECT verdict on record: ZORS (0x5110EE173d24 | +7d |

| 2026-07-21 | auto | 0x28D4e499C4CdE621e1Cea7c9CBf9D43bf75a9525 (HLX) | deep_investigation | CAUTION (70/100) | Low holder count (155) | +7d |

| 2026-07-21 | auto | 0x40Faa04e54a6f3C6F85B3114bb04890Dc77b8be3 (cbBTC) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-21 | auto | 0x0A1a1A107E45b7Ced86833863f482BC5f4ed82EF (USDai) | deep_investigation | CAUTION (57/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-21 | auto | 0x31bC2932D4A9b532da771C2681BDA14b2D2Ad98b (:p) | deep_investigation | REJECT (40/100) | Same deployer has a prior CAUTION/REJECT verdict on record: PLAY (0x068c1c81B802 | +7d |

| 2026-07-22 | auto | 0x75F16b63e8f94F91dbc924845Aa42093396283e8 (ZAMA) | deep_investigation | CAUTION (58/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-22 | auto | 0xFd15909C86BCd27F195B0B9f9A791c17Eb87Eb07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-22 | auto | 0x33417DFDa9845853266b3bA4686A397aA0ae8B07 (OpenAI) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-22 | auto | 0x2B225125765ECBBc4d4E4D2674F92e43c6340331 (OpenAI) | deep_investigation | REJECT (15/100) | Token name/symbol (OpenAI / OpenAI) impersonates a real company with no on-chain | +7d |

| 2026-07-22 | auto | 0x2D76fe86d39a7bfF9EE814110A46fDE2412F933F (PROS) | deep_investigation | REJECT (48/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-22 | auto | 0x775387eFAbDad9816e8C52dA5672127185581f0b (VBV) | deep_investigation | PROCEED (90/100) | Owner not renounced (0x5fcbbd899d608559b14a2d2cc6a886ee9776fbf8) — can still act | +7d |

| 2026-07-22 | auto | 0x9385Bd6198EC6664567c456Db8cEE1C940D1cB07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-22 | auto | 0x6E97D91456C55a6097ef49234942d2C1e2AB8b07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-22 | auto | 0x0000C9AF57138af42f22729A4DE46c650E602EF4 (SWOGE) | deep_investigation | CAUTION (62/100) | Low holder count (146) | +7d |

| 2026-07-22 | auto | 0x4aC963E04EcCD97A98bBe6BCB6d3bc2A649E0b07 (Claude) | deep_investigation | REJECT (0/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-22 | auto | 0x4C6e295398B2A4eE255928eBF0D210dd49EDFD59 (play) | deep_investigation | REJECT (25/100) | Same deployer has a prior CAUTION/REJECT verdict on record: PLAY (0x068c1c81B802 | +7d |

| 2026-07-22 | auto | 0x7787548C57031023C031304F274BEda304dA734f (BTC) | deep_investigation | REJECT (37/100) | Owner not renounced (0x5cc575f1b197022be8bba1c6e4a9e5972daa397e) — can still act | +7d |

| 2026-07-23 | auto | 0x34628A64aBbcb562dfC668Ab8E76327759fc855f (USDC) | deep_investigation | CAUTION (73/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-23 | auto | 0x9126236476eFBA9Ad8aB77855c60eB5BF37586Eb (CHECK) | deep_investigation | PROCEED (82/100) | Owner not renounced (0x9de1abeeb6cc60ded81de4e8c11930c3793f8bdb) — can still act | +7d |

| 2026-07-23 | auto | 0x2EFAc0a597A37050AafcF4beC627249D533DD9f8 ($checkr) | deep_investigation | CAUTION (60/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-23 | auto | 0x88888880d5Ca13018D2dC11e2e4744BD91a5656f (BTBB) | deep_investigation | REJECT (25/100) | Owner not renounced (0x98834162fe037a3d213a908162db5e2ded8cba77) — can still act | +7d |

| 2026-07-23 | auto | 0x3526989bA0dbc5E4163F4E453d20f9fedcC87081 (Del) | deep_investigation | PROCEED (90/100) | Low liquidity $22,125 | +7d |

| 2026-07-23 | auto | 0xec6432B90e7fD4d9f872cc5C781f05B617DB861E (DEL) | deep_investigation | REJECT (8/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-23 | auto | 0x372359b83C4B286b6a1084f07017957a3bd16Ba3 (aero) | deep_investigation | CAUTION (50/100) | Owner not renounced (0x660eaaedebc968f8f3694354fa8ec0b4c5ba8d12) — can still act | +7d |

| 2026-07-23 | auto | 0xC720078b43083B0962467fde30B6517AC00F770f (USDT) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-23 | auto | 0x9A27f0A9d45Dd49230C026Ebe6A344A180877C79 (Del404) | deep_investigation | CAUTION (72/100) | Owner not renounced (0x36bcc86f3ff09ae379c1db8a33ad88fb117232f5) — can still act | +7d |

| 2026-07-23 | auto | 0x99E980265Bf36516C442be982df1772a6cCb3233 (ASSET) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-23 | auto | 0xe76278619DDe1f71E5f8547d8AF9076A76C1322D (ASSET) | deep_investigation | REJECT (28/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-24 | auto | 0x0000000000000000000000000000000000000000 (ETH) | deep_investigation | PROCEED (80/100) | Holder count unavailable — cannot assess distribution | +7d |

| 2026-07-24 | auto | 0x2614f29C39dE46468A921Fd0b41fdd99A01f2EDf (HLX) | deep_investigation | CAUTION (53/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-24 | auto | 0xe8D3f6F1c669f02964d1A7Ee562cA99128180106 (CHECK) | deep_investigation | REJECT (5/100) | Same deployer has a prior CAUTION/REJECT verdict on record: PLAY (0x068c1c81B802 | +7d |

| 2026-07-24 | auto | 0xeB51D9A39AD5EEF215dC0Bf39a8821ff804A0F01 (LGNS) | deep_investigation | PROCEED (88/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-24 | auto | 0x5b290eCdF0c4d2D8F2b69661A61b73E6be2DD04A (CHECK) | deep_investigation | REJECT (5/100) | Same deployer has a prior CAUTION/REJECT verdict on record: ContentCoin (0x31A62 | +7d |

| 2026-07-24 | auto | 0x87c6c398F811A462d623D24cAfEcaf0F0E553b08 (CHECK) | deep_investigation | REJECT (35/100) | Very few holders (23) — thin, easily manipulated distribution | +7d |

| 2026-07-24 | auto | 0xAAAB9D12A30504559b0C5a9A5977fEE4A6081c6b (PHAR) | deep_investigation | REJECT (43/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-24 | auto | 0x7404AC09aDf614603D9c16a7CE85A1101F3514ba (PLAY) | deep_investigation | CAUTION (55/100) | Owner not renounced (0x5e0fdc32c24a7f2b49ed81abefcc5484775fa4e7) — can still act | +7d |

| 2026-07-24 | auto | 0xf7C1CEfCf7E1dd8161e00099facD3E1Db9e528ee (TOWER) | deep_investigation | REJECT (45/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-24 | auto | 0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a (GMX) | deep_investigation | REJECT (25/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-24 | auto | 0xac531Eb26Ca1d21b85126De8FB87E80E09002DcF (SAND) | deep_investigation | CAUTION (57/100) | Owner can change balances (rug surface) | +7d |

| 2026-07-25 | auto | 0xe9A53C43a0B58706e67341C4055de861e29Ee943 (ELMNT) | deep_investigation | CAUTION (65/100) | Very low liquidity $7,927 (rug/illiquid) | +7d |

| 2026-07-25 | auto | 0x30B9F6FccBf69b8CAbe37A6867373BAD78278420 (VELVET) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x8dB2be2bf9C90b7c7B11Af0F46bcafe4FAb6Dd88 (USDC) | deep_investigation | CAUTION (68/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x2B11834Ed1FeAEd4b4b3a86A6F571315E25A884D (MENTE) | deep_investigation | PROCEED (82/100) | Owner not renounced (0xcc29169da9063f893d7958e8c021e788446e7229) — can still act | +7d |

| 2026-07-25 | auto | 0xA3d36e8B5cA7A74b95c6427e546dA586DE5607Be (USOR OIL) | deep_investigation | PROCEED (90/100) | Low liquidity $41,326 | +7d |

| 2026-07-25 | auto | 0xdCf5130274753c8050aB061B1a1DCbf583f5bFd0 (VCNT) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-25 | auto | 0x712be9C5b93d4aC284382593327Ae29e59977b07 (VCNT) | deep_investigation | REJECT (35/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-25 | auto | 0xa8Ec9351397e29e4a93D08f09Badd56f3Bd0b581 (dexcheckai) | deep_investigation | CAUTION (70/100) | Same deployer has a prior CAUTION/REJECT verdict on record: ContentCoin (0x31A62 | +7d |

| 2026-07-25 | auto | 0xf30d3221a6d46645423FF82C324875586c0fAB07 (OpenAI) | deep_investigation | REJECT (20/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-25 | auto | 0xB8d7710f7d8349A506b75dD184F05777c82dAd0C (ARENA) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-25 | auto | 0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb (DAI) | deep_investigation | REJECT (45/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0xEB466342C4d449BC9f53A865D5Cb90586f405215 (axlUSDC) | deep_investigation | REJECT (23/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0xC4FA51E5208b835Bc6dB3144F25067aA194BEfBa (TRUMP28) | deep_investigation | PROCEED (80/100) | Low liquidity $25,871 | +7d |

| 2026-07-25 | auto | 0x32708538a107253b51a735A724330A23106ca4cA (01) | deep_investigation | PROCEED (85/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-25 | auto | 0x4d7078DDd6cCFED2F85dB5B7D3Ff16828d378d48 (AI) | deep_investigation | CAUTION (62/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-25 | auto | 0x2598c30330D5771AE9F983979209486aE26dE875 (AI) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-25 | auto | 0xaa26754dD0C8310cB70F3B66DAeAb52c8cFf3c30 (H420) | deep_investigation | REJECT (32/100) | Owner not renounced (0xe449a29a89738303cea0e43461df716103d5ea45) — can still act | +7d |

| 2026-07-25 | auto | 0xD60ABFB751dB36514a592963fD71DD50c6CF9Ba9 (JAKEX) | deep_investigation | CAUTION (65/100) | Very low liquidity $1,778 (rug/illiquid) | +7d |

| 2026-07-25 | auto | 0x3CfaDB7f1fD7C786a98c3Fa37131ff1537E554C5 (NTFS) | deep_investigation | REJECT (13/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0xB200000000000000000000109019757367070Eb0 (NTFS) | deep_investigation | REJECT (15/100) | Very few holders (2) — thin, easily manipulated distribution | +7d |

| 2026-07-25 | auto | 0xc8Fb80fCc03f699C70ff0CC08C09106288888888 (CTM) | deep_investigation | CAUTION (75/100) | Owner not renounced (0x70f279fa72c82110a0bb4745d6283b790190c33f) — can still act | +7d |

| 2026-07-25 | auto | 0x014522b4199Fa89674F45917D39f9ad46268A5da (CTM) | deep_investigation | REJECT (28/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0xd8526e86fDBcaf9b4d104D995e2c8023f73954c5 (FWAres) | deep_investigation | REJECT (30/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-25 | auto | 0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE (SHIB) | deep_investigation | CAUTION (77/100) | Top 10 non-LP/burn holders control 64% of supply — meaningful concentration | +7d |

| 2026-07-25 | auto | 0x55f622B7834a81436EB49138c0d3D2C7D1ffbFc0 (SHIB) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x279a9C40151bfe9AFEFf5530c5F32bc6ecea652a (CTM) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x6f09344D2a9a7AB1470a19cb014423334F3C57E4 (AUGU) | deep_investigation | REJECT (20/100) | Top 10 non-LP/burn holders control 94% of supply — concentrated, easily manipula | +7d |

| 2026-07-25 | auto | 0xa78d8321B20c4Ef90eCd72f2588AA985A4BDb684 (ANT) | deep_investigation | CAUTION (70/100) | Top 10 non-LP/burn holders control 81% of supply — concentrated, easily manipula | +7d |

| 2026-07-25 | auto | 0x271415A029602f9c370D022aDEba703F172c79fF (VC) | deep_investigation | CAUTION (60/100) | Top 10 non-LP/burn holders control 105% of supply — concentrated, easily manipul | +7d |

| 2026-07-25 | auto | 0x2A168c00310451E7024E1149A433c796c72d515D (CTM) | deep_investigation | REJECT (38/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x1F514A61bcde34F94Bc39731235690ab9da737F7 (TAROT) | deep_investigation | CAUTION (63/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0xf280B16EF293D8e534e370794ef26bF312694126 (ASTEROID) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-25 | auto | 0xAFF2565091E7207191dBe340B8528D02FA78d044 (ASTEROID) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-25 | auto | 0x3134be4a8D5E42Bc9237F7dbeAb14F72E4089c10 (ASTEROID) | deep_investigation | REJECT (23/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x375488F097176507e39B9653b88FDc52cDE736Bf (TAROT) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-25 | auto | 0x2c72D25530191EBD244Eb6325E1892480b0e6E28 (AIPF) | deep_investigation | CAUTION (73/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x1e9909F1c7051aD4Bf4496A345736dCEdC2A3Cfd (LTZ) | deep_investigation | REJECT (5/100) | Very few holders (32) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x49DDee75D588b79a3eB1225dd386644eeeeeaF08 (EBCC) | deep_investigation | CAUTION (70/100) | Top 9 non-LP/burn holders control 100% of supply — concentrated, easily manipula | +7d |

| 2026-07-26 | auto | 0xB5C064F955D8e7F38fE0460C556a72987494eE17 (QUICK) | deep_investigation | CAUTION (74/100) | Owner not renounced (0xa6fa4fb5f76172d178d61b04b0ecd319c5d1c0aa) — can still act | +7d |

| 2026-07-26 | auto | 0x831753DD7087CaC61aB5644b308642cc1c33Dc13 (QUICK) | deep_investigation | PROCEED (90/100) | Owner not renounced (0xa6fa4fb5f76172d178d61b04b0ecd319c5d1c0aa) — can still act | +7d |

| 2026-07-26 | auto | 0xD90b9773f9922A34F763087665B3A4649E710326 (ARBI) | deep_investigation | REJECT (32/100) | Low holder count (162) | +7d |

| 2026-07-26 | auto | 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359 (USDC) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-26 | auto | 0xd9Fcd98c322942075A5C3860693e9f4f03AAE07b (EUL) | deep_investigation | CAUTION (65/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0xC5667DC06597ab4d2276EcE522918d7Fd8A578a4 (EUL) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x6A92B1E99De09f71CD96BC91F934826d96B8b26E (AS) | deep_investigation | CAUTION (53/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x77719EAA4B9C24425bfCd39ac84F1e2E9C88568f (RW) | deep_investigation | CAUTION (75/100) | Owner not renounced (0x6597cbb2d2ef74c0d037c07f0d41a4fd51386fd0) — can still act | +7d |

| 2026-07-26 | auto | 0x99a57E6C8558BC6689f894e068733ADf83C19725 (sLGNS) | deep_investigation | REJECT (25/100) | Owner not renounced (0xe979f492f934556c56fb9c1f6a82fecc7abb867e) — can still act | +7d |

| 2026-07-26 | auto | 0x79774Bf5867ac4e014A48B471CBd94A01cc9a4D2 (BTC) | deep_investigation | CAUTION (70/100) | Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipul | +7d |

| 2026-07-26 | auto | 0x82ce191D049Ed69bCb00870e95478C401C3002c8 (DIM) | deep_investigation | CAUTION (50/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-26 | auto | 0xAc9ce2775B918C4d4fddEcB772064637c292C295 (SOSO) | deep_investigation | REJECT (30/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x35e9e9A79756e952B9EA358Be79D7faa8D9381a0 (DIM) | deep_investigation | CAUTION (50/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-26 | auto | 0xAF895F7718dBc701418FcFeFaBadA961848a79b2 (DIM) | deep_investigation | REJECT (17/100) | Low holder count (51) | +7d |

| 2026-07-26 | auto | 0xbB0191DA27aff1ad391F85B8DFAa2eBb0219342C (EUL) | deep_investigation | REJECT (28/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x0Fa73480b77B9E3B8C16540b71F9e33247FB395E (SHIB) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x85bAbbd6124589F5Ef3AE12a2745267cc1852f42 (gLGNS) | deep_investigation | REJECT (7/100) | Low holder count (68) | +7d |

| 2026-07-26 | auto | 0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063 (LGNS) | deep_investigation | PROCEED (92/100) | Top 10 non-LP/burn holders control 62% of supply — meaningful concentration | +7d |

| 2026-07-26 | auto | 0xB6fc4bc614BC3275C36D609B7a9E1f5017274aB1 ($PLY) | deep_investigation | REJECT (20/100) | Very few holders (8) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x0Cb9610b0b3C6f0758aee0082e149b861a667E99 (PLAY) | deep_investigation | REJECT (0/100) | Same deployer has a prior CAUTION/REJECT verdict on record: PLAY (0x068c1c81B802 | +7d |

| 2026-07-26 | auto | 0x4c28f48448720e9000907BC2611F73022fdcE1fA (WETH) | deep_investigation | CAUTION (60/100) | Top 10 non-LP/burn holders control 90% of supply — concentrated, easily manipula | +7d |

| 2026-07-26 | auto | 0x8cDDd6EeA1067b78B77255e49861843F69D4703D (PUPPY) | deep_investigation | CAUTION (50/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-26 | auto | 0xd6a20E0E2d2399c925e315732E76538F3883a1d6 (EBCC) | deep_investigation | REJECT (3/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x6a4e26FA2f769A3d98b47A9e0e3C2177Cd5C88BF (PUPPY) | deep_investigation | REJECT (32/100) | Low holder count (90) | +7d |

| 2026-07-26 | auto | 0x289ba1701C2F088cf0faf8B3705246331cB8A839 (LPT) | deep_investigation | CAUTION (58/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0x0E63B9C287E32A05E6b9AB8ee8dF88A2760225A9 (PIEVERSE) | deep_investigation | REJECT (18/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0xA3c322Ad15218fBFAEd26bA7f616249f7705D945 (MV) | deep_investigation | CAUTION (52/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-26 | auto | 0xd17c2AE3FB89448991D26bCd877692122341f1D6 (MV) | deep_investigation | REJECT (0/100) | Transfers can be paused by owner | +7d |

| 2026-07-26 | auto | 0x204820B6e6FEae805e376D2C6837446186e57981 (ROND) | deep_investigation | REJECT (40/100) | Owner not renounced (0x78a3b0a018b9763a67dcfbae7ba7e2e47b9e341f) — can still act | +7d |

| 2026-07-26 | auto | 0xEd2EE58908eA569A994a1ac77da4A947807A4444 (DCA) | deep_investigation | CAUTION (55/100) | Low liquidity $42,250 | +7d |

| 2026-07-26 | auto | 0x095576F441006679a79a53ddF9136b550095dD1C (DCA) | deep_investigation | REJECT (30/100) | Very few holders (15) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0xfDf82991f00caE63062fD1d52e7f340693A34444 (DCA) | deep_investigation | REJECT (40/100) | Very few holders (33) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x1460d468466D17F65FF1426571E18059d23a9eBD (dca) | deep_investigation | REJECT (47/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0xb932933E3504F85c330aa20Ed3Ce7610851C96E4 (OPENAI) | deep_investigation | REJECT (0/100) | Token name/symbol (OpenAI BOT / OPENAI) impersonates a real company with no on-c | +7d |

| 2026-07-26 | auto | 0xDB9d15E484368facB45f5784A99A0A5fECEed624 (NTFS) | deep_investigation | REJECT (43/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-26 | auto | 0xBA103bbd78C76E87D1067Dc383cc2A78fb70687c (PUPPY) | deep_investigation | REJECT (30/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x047653a3C6c97C8a4dD2cFbf996f157d166F17A0 (DEXE) | deep_investigation | REJECT (0/100) | Very few holders (16) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x8729438EB15e2C8B576fCc6AeCdA6A148776C0F5 (QI) | deep_investigation | CAUTION (77/100) | Top 10 non-LP/burn holders control 68% of supply — meaningful concentration | +7d |

| 2026-07-26 | auto | 0x60781C2586D68229fde47564546784ab3fACA982 (PNG) | deep_investigation | CAUTION (62/100) | Top 10 non-LP/burn holders control 87% of supply — concentrated, easily manipula | +7d |

| 2026-07-26 | auto | 0x8D88e48465F30Acfb8daC0b3E35c9D6D7d36abaf (CNR) | deep_investigation | REJECT (35/100) | Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipula | +7d |

| 2026-07-26 | auto | 0x01C2086faCFD7aA38f69A6Bd8C91BEF3BB5adFCa (YAY) | deep_investigation | REJECT (27/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-26 | auto | 0xCBc5b4b1a171fc4f86106e3E36853592AC16aaaa (DCA) | deep_investigation | CAUTION (70/100) | Top 10 non-LP/burn holders control 85% of supply — concentrated, easily manipula | +7d |

| 2026-07-26 | auto | 0xeA4D009DD99cb83FF4e27C533e279e6120364444 (DCA) | deep_investigation | REJECT (10/100) | Same deployer has a prior CAUTION/REJECT verdict on record: DCA (0xfDf82991f00ca | +7d |

| 2026-07-26 | auto | 0xf72a7beA38b6f61B731b496EbB67A97AD9c8C68A (DIM) | deep_investigation | REJECT (5/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x9BE98a036f654040d39caF0F4530e95A4f890274 (DIM) | deep_investigation | REJECT (20/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x1257d823Fcb0abAe72eAB01c59456F463cA3c35a (DIM) | deep_investigation | REJECT (30/100) | Very few holders (2) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0xa2a17b400CD9Bc8AF04714AA3E99Bee86374F90e (DIM) | deep_investigation | REJECT (0/100) | Very few holders (41) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0xc883e1910b9A2e39840E7c26BB7B7A3f80dB4f98 (sosocupid) | deep_investigation | REJECT (0/100) | Same deployer has a prior CAUTION/REJECT verdict on record: CHECK (0x87c6c398F81 | +7d |

| 2026-07-26 | auto | 0xcB362b3701eF6F811DCdCd702482812D0Cf34444 (DCA) | deep_investigation | REJECT (40/100) | Very few holders (5) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0xa00453052A36D43A99Ac1ca145DFe4A952cA33B8 (CATE) | deep_investigation | PROCEED (90/100) | Violent 24h move +667% (volatility/manipulation) | +7d |

| 2026-07-26 | auto | 0xF39e4b21c84e737Df08e2C3b32541d856f508E48 (ESPORTS) | deep_investigation | REJECT (40/100) | Hidden owner | +7d |

| 2026-07-26 | auto | 0x9b38D8BC5E35c074e7DFE45CBF9A9818B4c04444 (DCA) | deep_investigation | REJECT (40/100) | Very few holders (5) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x911828FF4036f5c1AcF0c0Da3c71900dd937C8A9 (CATE) | deep_investigation | REJECT (30/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x67E5481ED9F785Db6508761eef45b85a19Ee0Df3 (DIM) | deep_investigation | REJECT (30/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-26 | auto | 0x181cd4706322EF57a51c5dA6AdE1fC56FF694444 (DCA) | deep_investigation | REJECT (10/100) | Same deployer has a prior CAUTION/REJECT verdict on record: DCA (0xcB362b3701eF6 | +7d |

| 2026-07-26 | auto | 0x8682BaCE40610Eefcf14b1Af9CCd92b77bf88471 (Subject 3) | deep_investigation | REJECT (40/100) | Transfers can be paused by owner | +7d |

| 2026-07-27 | auto | 0xF26662c4298e6be93F7ac22778Bf6e2Bf96F8063 (NightDriver) | deep_investigation | REJECT (7/100) | Owner not renounced (0xbf71ff1f8284abbc4eb11297bce7f979acf959f7) — can still act | +7d |

| 2026-07-27 | auto | 0x9d02E97177073FB92A0F3F75CA36D56fdAfe2bcA (SHIB) | deep_investigation | REJECT (20/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-27 | auto | 0xCBf4AB00b6Aa19B4d5D29C7c3508B393a1C01Fe3 (MegaDoge) | deep_investigation | CAUTION (50/100) | Only 5% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-27 | auto | 0x93ecd8e9156E6b217514BCFE59837b3807D8F53D (KABOSU) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-27 | auto | 0xc02179dda49187A8761156F011F40D7E41FaCAAF (velvet) | deep_investigation | REJECT (10/100) | Same deployer has a prior CAUTION/REJECT verdict on record: ContentCoin (0x31A62 | +7d |

| 2026-07-27 | auto | 0xAC0F66379A6d7801D7726d5a943356A172549Adb (GEOD) | deep_investigation | REJECT (35/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-27 | auto | 0x0e4F6209eD984b21EDEA43acE6e09559eD051D48 (ON) | deep_investigation | CAUTION (77/100) | Top 10 non-LP/burn holders control 61% of supply — meaningful concentration | +7d |

| 2026-07-27 | auto | 0x444045B0EE1ee319A660a5E3d604CA0ffA35ACaA (BTW) | deep_investigation | CAUTION (65/100) | Owner not renounced (0x8dafd691ef82f90b23fddb10a67d782f04073bd3) — can still act | +7d |

| 2026-07-27 | auto | 0xEa59Fa56e4ff71D690BaA76EbB3A7325490E9680 (USD₮) | deep_investigation | CAUTION (50/100) | Very few holders (8) — thin, easily manipulated distribution | +7d |

| 2026-07-27 | auto | 0x49E60D05319f6f9945012067E0718a2B6267cF58 (BTW) | deep_investigation | REJECT (35/100) | Top 10 non-LP/burn holders control 99% of supply — concentrated, easily manipula | +7d |

| 2026-07-27 | auto | 0xdE8D34cc700055aA6Bc8F7614851a051ca14bF33 (HRC) | deep_investigation | REJECT (15/100) | Owner can change balances (rug surface) | +7d |

| 2026-07-27 | auto | 0x604448c8f009135e913C7e0E4Bef692B0003A02A (ON) | deep_investigation | PROCEED (85/100) | Top 10 non-LP/burn holders control 88% of supply — concentrated, easily manipula | +7d |

| 2026-07-27 | auto | 0x0ffd960881C83Cd63a50d5C944C9F2B866f55a28 (SCR) | deep_investigation | REJECT (19/100) | Transfers can be paused by owner | +7d |

| 2026-07-27 | auto | 0x6982508145454Ce325dDbE47a25d4ec3d2311933 (PEPE) | deep_investigation | PROCEED (85/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-27 | auto | 0xd5d0A9b3f2C264b955Ae7161cfA6D38A7aEa60a7 (abcPHAR) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-27 | auto | 0x5C09A9cE08C4B332Ef1CC5f7caDB1158C32767Ce (fBOMB) | deep_investigation | CAUTION (77/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-27 | auto | 0xA64aC4eCc7302Ba4dCF1F9Cc8856Ac5C2eD2C581 (RWA) | deep_investigation | REJECT (32/100) | Owner not renounced (0xe1450d7708de452b1d89cbf9b83e0cba97719d39) — can still act | +7d |

| 2026-07-27 | auto | 0xfCF7985661d2c3F62208970cBE25e70BCCe73E7C (RWA) | deep_investigation | CAUTION (60/100) | Transfers can be paused by owner | +7d |

| 2026-07-27 | auto | 0xf3610Dbfe8E3e469cbF8594aD9830efb12aa4444 (AEON) | deep_investigation | CAUTION (57/100) | Top 10 non-LP/burn holders control 64% of supply — meaningful concentration | +7d |

| 2026-07-27 | auto | 0x2f6A9340C84E94413d01afCEEf85f1A8D1f27aD7 (LFWA) | deep_investigation | REJECT (27/100) | Low holder count (169) | +7d |

| 2026-07-27 | auto | 0x277aDD739c6E0477616948357AF9E79Fe1Ec9B80 (AEON) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-27 | auto | 0xE441E2e14b0A2704D73F9d34FAB479682a22A897 (SLGNS) | deep_investigation | REJECT (27/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-27 | auto | 0x844810406C9a8dD3EBeAB658F526dF0A3172aa1E (CATE) | deep_investigation | CAUTION (55/100) | Low liquidity $26,479 | +7d |

| 2026-07-27 | auto | 0xd0bc8Ab397851ECfa58009D03bBc1a41FC764444 (币有) | deep_investigation | CAUTION (75/100) | Violent 24h move +591% (volatility/manipulation) | +7d |

| 2026-07-27 | auto | 0x97Fbf25645a67A78ce9cb49498b281928518DCF0 (CHECK) | deep_investigation | REJECT (22/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-27 | auto | 0xd04981C24dE192665A59D4BEeAdFA58BD9994444 (币有) | deep_investigation | REJECT (30/100) | Top 10 non-LP/burn holders control 120% of supply — concentrated, easily manipul | +7d |

| 2026-07-28 | auto | 0x3C0541e68CE0F1F9073E4BA3Db81b730Eb614444 (币有) | deep_investigation | CAUTION (55/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x9a6Cb2C43A3454c8DB4e89e4e031FDcFC8769A02 (币有) | deep_investigation | REJECT (0/100) | Very few holders (25) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0xaf412164E9af710d3868A088d759478a5A004444 (币有) | deep_investigation | REJECT (40/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x49Fcf04B7eB04D1DfEBd8E5FE3dFCF42f69505E4 (WPOL) | deep_investigation | CAUTION (55/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x7142b752A1259F5D37A58e47ef60451F5F8038eD (CATE) | deep_investigation | CAUTION (65/100) | Violent 24h move +3641% (volatility/manipulation) | +7d |

| 2026-07-28 | auto | 0xe22b36dB6bCDb931e4a4833F5A24d3D4036D4444 (币有) | deep_investigation | REJECT (40/100) | Very few holders (6) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0xD8Db79190FB3Ddb6A30f27d0Ba11634b05a54444 (币有) | deep_investigation | REJECT (10/100) | Top 10 non-LP/burn holders control 100% of supply — concentrated, easily manipul | +7d |

| 2026-07-28 | auto | 0x93849a00A16C39a3F32DF6490b66a6b015A090C3 (币有) | deep_investigation | REJECT (0/100) | Very few holders (8) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x95057017d55fd324987A96d8219674081Ece377b (币有) | deep_investigation | REJECT (5/100) | Very few holders (13) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x227f7D025B140D9881A00fB4F3f76A4eDa72581f (币有) | deep_investigation | REJECT (25/100) | Very few holders (24) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x53DDBC55613f4cf51F26e477C9BE46Fe351cad87 (AS) | deep_investigation | REJECT (47/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0xeBd6d1E042bD16893a51a3F9E5c495998a4D4444 (币有) | deep_investigation | REJECT (10/100) | Top 10 non-LP/burn holders control 98% of supply — concentrated, easily manipula | +7d |

| 2026-07-28 | auto | 0x05FA81Ae340098c8C7fcd310469195F9f8410858 (STEM) | deep_investigation | REJECT (13/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-28 | auto | 0x22D418A8d69d5AacfaeDf84653448a8591d5e63B (币有) | deep_investigation | REJECT (25/100) | Very few holders (24) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0xb7E4183260BfC5ED9965f723bF739451c7757f89 (币有) | deep_investigation | REJECT (25/100) | Very few holders (6) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x32B0007f0E3eDd1F55c015bD7445EA5556cF4B07 (DXCHCK) | deep_investigation | REJECT (10/100) | Deployed via a permissionless meme-token factory template (ClankerToken) — no te | +7d |

| 2026-07-28 | auto | 0x57c4ABE2560C41F97519C43dbe874e844D63F3BC (Blinky) | deep_investigation | REJECT (35/100) | Top 10 non-LP/burn holders control 86% of supply — concentrated, easily manipula | +7d |

| 2026-07-28 | auto | 0x6224e0f53de461fEEfD4D755dc314FA0324a4444 (币有) | deep_investigation | REJECT (40/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x942AC36bfB89944CA07EE465A8893201e0764444 (币有) | deep_investigation | REJECT (40/100) | Very few holders (6) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0xFB4EA38d713afBb3eD35869B790aec3CA53B0000 (币有) | deep_investigation | REJECT (45/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x6e6B8968D304B106F2f0f283e857971e9C9D036e (币有) | deep_investigation | REJECT (45/100) | Very few holders (0) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0x7987f03462200b3D8A072E02C89A8A41dCB124EE (V4) | deep_investigation | CAUTION (50/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-28 | auto | 0xaB71d6C5611182D23c631fa8471D2fA7ac544444 (币有) | deep_investigation | REJECT (40/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0xc5b0251daCFaB74bc2deBaa52072a2A4c939c105 (DOGE-1) | deep_investigation | CAUTION (75/100) | Transfers can be paused by owner | +7d |

| 2026-07-28 | auto | 0xD721706581d97eCd202bBab5c71b5a85f0F78E69 (DOGE1) | deep_investigation | PROCEED (90/100) | Violent 24h move +169% (volatility/manipulation) | +7d |

| 2026-07-28 | auto | 0xFfE203b59393593965842439ce1E7D7c78109b46 (Doge-1) | deep_investigation | PROCEED (100/100) | clean | +7d |

| 2026-07-28 | auto | 0xAfB97Dd6630f1930B5cE8C542AfE7B988e40e805 (DOGE1) | deep_investigation | REJECT (18/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-28 | auto | 0x26e9dbe75aed331E41272BEcE932Ff1B48926Ca9 (fBOMB) | deep_investigation | REJECT (30/100) | Owner not renounced (0xcbeb24e8fc568001e83430ec4929ce56b29ba9a2) — can still act | +7d |

| 2026-07-28 | auto | 0x18E3605B13F10016901eAC609b9E188CF7c18973 (HEFE) | deep_investigation | CAUTION (75/100) | Low liquidity $35,536 | +7d |

| 2026-07-28 | auto | 0x6F43fF77A9C0Cf552b5b653268fBFe26A052429b (LAMBO) | deep_investigation | REJECT (35/100) | Owner can change balances (rug surface) | +7d |

| 2026-07-28 | auto | 0xa7Aee6cB644fCD1cef488f5a901d80D864Bb4444 (币有) | deep_investigation | REJECT (40/100) | Very few holders (2) — thin, easily manipulated distribution | +7d |

| 2026-07-28 | auto | 0xDDB3422497E61e13543BeA06989C0789117555c5 (COTI) | deep_investigation | CAUTION (63/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-28 | auto | 0xa10C39aBA4a9A392683414Ff9D8809Cd5fC03F24 (FERRET) | deep_investigation | CAUTION (55/100) | Low liquidity $26,431 | +7d |

| 2026-07-28 | auto | 0x317C63Fdf448779923fe9b845E4A58CB4d224e56 (Ferret) | deep_investigation | REJECT (47/100) | Low holder count (191) | +7d |

| 2026-07-28 | auto | 0xBcBDA13Bd60bC0e91745186E274D1445078D6b33 (FERRET) | deep_investigation | PROCEED (82/100) | Top 10 non-LP/burn holders control 65% of supply — meaningful concentration | +7d |

| 2026-07-28 | auto | 0xAf2CA40d3fc4459436D11B94d21FA4b8A89fB51d (gCOTI) | deep_investigation | REJECT (42/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0x1884Cc728574AAd4Fa06e556E9d9DCcF95B4BF02 (AIPF) | deep_investigation | CAUTION (62/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0xfb1561214348ee8D8198C06ea0D21232872cDEFd (AS) | deep_investigation | REJECT (27/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0x46dDcc662A045770CE1e264819542C9617547777 (BANK) | deep_investigation | PROCEED (92/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0x3f234f3Ab2B79dcF243Ab387939d2F7e2530b676 (CES) | deep_investigation | REJECT (12/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0x5bAd40E938230A0C347a86995D82Ba92bEE2cD2C (CES) | deep_investigation | REJECT (12/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-28 | auto | 0x9c891326Fd8b1a713974f73bb604677E1E63396D (ISLAMI) | deep_investigation | REJECT (28/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-28 | auto | 0x6664347791C8d58E266EB8F824CE774a2624Fa07 (TRUMP2028) | deep_investigation | REJECT (25/100) | Transfers can be paused by owner | +7d |

| 2026-07-28 | auto | 0xBaf069e57AE635e28f33Da73534008dDdCC99F76 (BEAT) | deep_investigation | CAUTION (65/100) | Very low liquidity $2,456 (rug/illiquid) | +7d |

| 2026-07-29 | auto | 0x2e5ef97C96D6a44CcB8Db9C30f2F5DCec04BB6f9 (GTAVI) | deep_investigation | PROCEED (85/100) | Pair 23.3 days old — under a month, still unproven | +7d |

| 2026-07-29 | auto | 0x259186E64E35ce5DF3CA31364BD521F665BeE73D (GTAVI) | deep_investigation | CAUTION (75/100) | Top 10 non-LP/burn holders control 84% of supply — concentrated, easily manipula | +7d |

| 2026-07-29 | auto | 0x5b650B618B988090A0D30831846cA3105B527d70 (AS) | deep_investigation | REJECT (27/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-29 | auto | 0x2f67D3BCdbc5030A79De0B217B934781A181c706 (ON) | deep_investigation | REJECT (25/100) | Very few holders (27) — thin, easily manipulated distribution | +7d |

| 2026-07-29 | auto | 0x9A8E5a3732080cACc2Bb52fad1cD065129801e50 (0B0L) | deep_investigation | REJECT (15/100) | Owner not renounced (0x8c5b872d0aaa28ac6ac0af71fc6360779c9f290a) — can still act | +7d |

| 2026-07-29 | auto | 0x40b8129B786D766267A7a118cF8C07E31CDB6Fde (UB) | deep_investigation | CAUTION (60/100) | Owner not renounced (0xc82c31b242d49db07f9282295b6e8e391771a588) — can still act | +7d |

| 2026-07-29 | auto | 0xd94128D66BD0020888e380E8dF515Cb0B840dadD (FWA) | deep_investigation | REJECT (35/100) | Only 0% of liquidity is locked — the deployer can pull the rest at any time | +7d |

| 2026-07-29 | auto | 0x89Cf5C1b3bc04ea54795B37A85258F1dfC9c31dF (Swing) | deep_investigation | CAUTION (77/100) | Top 10 non-LP/burn holders control 64% of supply — meaningful concentration | +7d |

| 2026-07-29 | auto | 0xfb3bcd142ab83505d57c446e1718D8429424DE3b (ZAMA) | deep_investigation | REJECT (40/100) | Very few holders (2) — thin, easily manipulated distribution | +7d |

| 2026-07-29 | auto | 0x2C69ff812F62e664Fe23f2dC781C773D8c404cCc (Buddy) | deep_investigation | REJECT (0/100) | Owner not renounced (0x000000000000000000000000000000000000dead) — can still act | +7d |

| 2026-07-29 | auto | 0xe0AeE745b22c522DE621F826a9453f534808DFD0 (MCU) | deep_investigation | REJECT (35/100) | Transfers can be paused by owner | +7d |

| 2026-07-29 | auto | 0x31397372b6FE190a08ceb99B83b09d5CbB4c9cC3 (策略01) | deep_investigation | REJECT (17/100) | Low holder count (65) | +7d |

| 2026-07-29 | auto | 0xb162B75f641a88E2c7d32AAC7F490fe830B5b11D (VELVET) | deep_investigation | REJECT (25/100) | Owner not renounced (0xb518bbf70f4fbb51420c6766e237b70758ef331b) — can still act | +7d |

| 2026-07-29 | auto | 0xcf3232B85b43BCa90E51D38cc06Cc8bB8C8A3E36 (Beat) | deep_investigation | REJECT (37/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-29 | auto | 0x56BBbC01a416Fb9b995949d105a5697c2338Cd09 (Beat) | deep_investigation | REJECT (25/100) | Very few holders (24) — thin, easily manipulated distribution | +7d |

| 2026-07-29 | auto | 0xE7E7E741C23a4767831A56A8C99F522c5aC1E7E7 (EV) | deep_investigation | REJECT (27/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-29 | auto | 0xA7bef5abd9265Ab97EE43D2fc4A56e0Ba25ACA25 (BAY) | deep_investigation | CAUTION (60/100) | Top 10 non-LP/burn holders control 97% of supply — concentrated, easily manipula | +7d |

| 2026-07-29 | auto | 0xb111B7690F6420Fc27d63D6870AaD4450Dbe22D0 (FUN) | deep_investigation | REJECT (17/100) | Low holder count (79) | +7d |

| 2026-07-29 | auto | 0x7c6aa5126dA2691f62EBb2D2f082F908513983d0 (TRUMP2028) | deep_investigation | REJECT (27/100) | Upgradeable proxy (verify implementation) | +7d |

| 2026-07-29 | auto | 0xf64859A8A25175Ec8a35c4366C44EB2722fE154D (ON) | deep_investigation | REJECT (15/100) | Very few holders (1) — thin, easily manipulated distribution | +7d |

| 2026-07-29 | auto | 0x7DB662F5728Ed008d60caBae098E88AeA8fCa36C (ON) | deep_investigation | REJECT (0/100) | Mintable supply (dilution risk) | +7d |

| 2026-07-29 | auto | 0xB5D1AA718725FF1Ff3A56c8B30b4e8Ac41a1637A (ON) | deep_investigation | REJECT (0/100) | Same deployer has a prior CAUTION/REJECT verdict on record: ON (0x7DB662F5728Ed0 | +7d |
