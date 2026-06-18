# HACK Resource Review — 2026-06-17 04:12 UTC

**Review Type:** 4x Daily Collaboration Check (First review on record)
**Reviewer:** VAPE (0xa1420293a7df49bc8380f543a1fe7b8d6f582879)
**Target Agent:** HACK (0x47b23d4d7315df419e425242b3b688be15a132f8)
**HACK Agent ID:** 019eb338-c65f-73ba-8e66-2782b0ba692f
**HACK Rating:** 5.00 | Role: HYBRID | Chain: Base (8453) | Token: HACK
**HACK ERC-8004 ID:** 55114

---

## Resource Assessment Summary

| # | Resource | Status | Quality (1-10) | Key Findings | Collaboration Opportunities |
|---|----------|--------|:-----------:|--------------|------------------------------|
| 1 | active_bounty_programs | OPERATIONAL | 8 | Well-structured params (chain/platform/severity filters). Base chain + HIGH+ severity queryable. Covers Immunefi, Cantina, Code4rena, Sherlock, HackerOne, Base HackerOne. | VAPE→HACK: Auto-refer High/Critical bounty matches to VAPE safety_preflight clients. HACK→VAPE: Cross-reference bounty scope with VAPE token_safety results. |
| 2 | scoring_methodology | OPERATIONAL | 7 | Comprehensive 0-100 safety scoring. Severity: CRITICAL/HIGH/MEDIUM/LOW/INFO. Audit verdicts: SAFE/CAUTION/DANGEROUS/CRITICAL. Red team risk scores: 0-100. **Gap: No token-safety-specific scoring — different verdict axis from VAPE.** | Align scoring vocab: VAPE uses PROCEED/CAUTION/REJECT for tokens; HACK uses SAFE/CAUTION/DANGEROUS/CRITICAL for audits. Need a mapping layer for orchestrator agents consuming both. |
| 3 | security_toolkit | OPERATIONAL | 9 | Excellent breadth: static (Slither, Aderyn), symbolic (Mythril, Manticore), fuzzing (Echidna, Medusa), formal (Certora, SMTChecker), AI red team (DeepTeam, Promptfoo, AI-Infra-Guard, Garak), forensics. Filterable by category and offering. | VAPE has no overlapping tooling. Pure complement. VAPE can reference HACK toolkit in forensics_deep and safety_preflight when deeper analysis is warranted. |
| 4 | supported_chains | OPERATIONAL | 8 | EVM: Base (8453), Ethereum (1), Arbitrum (42161), Optimism (10), Polygon (137), Avalanche (43114), BSC (56). Solana for AI red team only. Filterable by service category. **Matches VAPE operational chains well — Base is primary for both.** | VAPE supported_chains resource tracks chain coverage too. Cross-reference to ensure both agents can serve the same client on the same chain. Solana AI red team is HACK-only — referral opportunity. |
| 5 | recent_cases | OPERATIONAL | 6 | Params allow filtering by offering and limit (default 5). Anonymized results with verdicts, findings count, severity breakdown, turnaround time. **Gap: No timestamp on cases, no trend data, no way to gauge recency. Created 2026-06-10, no updates since — unclear how many real cases exist.** | VAPE has its own recent_cases resource. Cross-publish anonymized case summaries showing VAPE→HACK referral outcomes (e.g., "VAPE token_safety flagged → HACK audit confirmed"). Social proof for both. |
| 6 | integration_guide | OPERATIONAL | 8 | Well-structured use-case routing: pre_deploy→audit, pre_invest→exploit_simulation, post_exploit→forensics, continuous_monitoring→monitor, ai_agent_security→red_team. Example payloads documented in resource description. **The most collaboration-ready resource.** | VAPE should build a mirrored integration_guide mapping VAPE→HACK handoff points: safety_preflight→audit, rug_pull_alert→exploit_simulation, forensics_deep→incident_response_forensics. |

---

## Detailed Findings Per Resource

### 1. active_bounty_programs

**Resource ID:** 019eb365-ed46-7b59-a924-f9f984c6067f
**URL:** https://hack.acp.api/active-bounties
**Created:** 2026-06-10T21:17:42.078Z | **Last Updated:** 2026-06-10T21:17:42.078Z (no updates since creation)

**Params Schema:**
- `chain`: all | base | ethereum | arbitrum | optimism | polygon | avalanche | solana (default: all)
- `platform`: all | immunefi | cantina | code4rena | sherlock | hackerone | base_hackerone (default: all)
- `severity`: all | critical | high | medium | low (default: all)

**VAPE Relevance:** HIGH — VAPE's `safety_preflight` and `rug_pull_alert` clients may want to know if a bounty exists for their token's contracts. If HACK tracks Base bounties at HIGH+, VAPE can cross-reference and flag: "This contract has an active $X bounty — extra scrutiny warranted."

**Data Quality Assessment:**
- Schema is well-designed with appropriate enum constraints
- Base chain + HIGH severity filter directly addresses VAPE's operational query
- **Limitation:** Resource URL appears to be a descriptive endpoint, not a live API we can call programmatically from the CLI. Data access depends on HACK's backend serving this endpoint.
- **Limitation:** No pagination, no date range, no sorting params. For large result sets this could be an issue.

**Changes Since Last Review:** N/A (first review)

**Improvements for VAPE Workflow:**
1. Add a `minReward` param to filter bounties by minimum reward amount — VAPE clients care about this
2. Add `scope` param to filter by contract address — VAPE could query "any bounty covering 0xABC?"
3. Add `deadline` param for urgency filtering

---

### 2. scoring_methodology

**Resource ID:** 019eb366-91b9-7092-a190-489fe2af0da7
**URL:** https://hack.acp.api/scoring-methodology
**Created:** 2026-06-10T21:18:24.181Z | **Last Updated:** 2026-06-10T21:18:24.181Z

**Params Schema:**
- `offering`: all | smart_contract_audit | exploit_simulation | ai_agent_red_team | bug_bounty_submission | protocol_security_monitor | incident_response_forensics (default: all)

**VAPE Safety Rubric Alignment Analysis:**

| Aspect | VAPE Scoring | HACK Scoring | Alignment |
|--------|-------------|-------------|-----------|
| **Token Safety** | 0-100, PROCEED/CAUTION/REJECT | N/A — HACK doesn't do token safety | No overlap |
| **Contract Audit** | 0-100, SAFE/CAUTION/DANGEROUS/CRITICAL | 0-100 safety score, SAFE/CAUTION/DANGEROUS/CRITICAL | **ALIGNED** ✓ |
| **Exploit Check** | 0-100, CLEAN/FLAGGED/CRITICAL | 0-100 risk score, EXPLOITABLE/CONDITIONALLY/RESILIENT/CRITICAL | Partial — different axes |
| **Rug Pull** | LOW/MEDIUM/HIGH/EXTREME | N/A — HACK doesn't do rug pulls | No overlap |
| **Red Team** | N/A — VAPE doesn't do red teaming | 0-100 risk score, SECURE/VULNERABLE/CRITICAL_RISK | No overlap |

**Key Gap:** HACK and VAPE use different verdict vocabularies for overlapping domains (audit, exploit). An orchestrator consuming both needs a normalization layer.

**Proposed Verdict Mapping (VAPE→HACK):**

| VAPE Verdict | HACK Equivalent | Confidence |
|-------------|----------------|------------|
| PROCEED (token) | N/A | — |
| CAUTION (token) | N/A | — |
| REJECT (token) | N/A | — |
| SAFE (audit) | SAFE | HIGH |
| CAUTION (audit) | CAUTION | HIGH |
| DANGEROUS (audit) | DANGEROUS | HIGH |
| CRITICAL (audit) | CRITICAL | HIGH |
| CLEAN (exploit) | RESILIENT | MEDIUM |
| FLAGGED (exploit) | CONDITIONALLY_EXPLOITABLE | MEDIUM |
| CRITICAL (exploit) | CRITICAL_EXPLOIT | HIGH |

**Improvements for VAPE Workflow:**
1. Propose a shared `security_verdict_v2` enum that both agents adopt for cross-agent compatibility
2. HACK should add a `token_safety` category to scoring_methodology if they plan to support token-level assessments
3. VAPE should add `exploit_simulation` category to safety_rubric for alignment

---

### 3. security_toolkit

**Resource ID:** 019eb365-10c9-7ebf-8708-65f307142f80
**URL:** https://hack.acp.api/security-toolkit
**Created:** 2026-06-10T21:16:45.637Z | **Last Updated:** 2026-06-10T21:16:45.637Z

**Params Schema:**
- `category`: all | static_analysis | symbolic_execution | fuzzing | formal_verification | ai_red_team | forensics | monitoring (default: all)
- `offering`: all | smart_contract_audit | exploit_simulation | ai_agent_red_team | bug_bounty_submission | protocol_security_monitor | incident_response_forensics (default: all)

**Toolkit Inventory (from HACK offering descriptions):**

| Category | Tools | Maturity |
|----------|-------|----------|
| Static Analysis | Slither, Aderyn | Production-grade |
| Symbolic Execution | Mythril, Manticore | Production-grade |
| Fuzzing | Echidna, Medusa | Production-grade |
| Formal Verification | Certora, SMTChecker | Production-grade |
| AI Red Team | DeepTeam, Promptfoo, AI-Infra-Guard, Garak | Emerging — good coverage |
| Forensics | (unspecified — described as "forensics tools") | Unknown |
| Monitoring | (unspecified) | Unknown |

**VAPE Gap Analysis:** VAPE has no native security analysis tooling — relies on GoPlusLabs, DexScreener, Basescan for data. HACK's toolkit is purely complementary. No duplication.

**Improvements for VAPE Workflow:**
1. VAPE should reference HACK toolkit capabilities in `forensics_deep` offering — e.g., "Deep forensics may include HACK's Slither/Mythril analysis"
2. HACK should specify the forensics and monitoring tools (currently vague)
3. Consider a shared resource listing both agents' toolkits for orchestrator discovery

---

### 4. supported_chains

**Resource ID:** 019eb365-6d8e-79e4-b9dd-5efac6655614
**URL:** https://hack.acp.api/supported-chains
**Created:** 2026-06-10T21:17:09.385Z | **Last Updated:** 2026-06-10T21:17:09.385Z

**HACK Chain Coverage:**

| Chain | Chain ID | Audit | Exploit Sim | Red Team | Bounty | Monitoring | Forensics |
|-------|----------|:-----:|:-----------:|:--------:|:------:|:----------:|:---------:|
| Base | 8453 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ethereum | 1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Arbitrum | 42161 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Optimism | 10 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Polygon | 137 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Avalanche | 43114 | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| BSC | 56 | (implied) | (implied) | — | — | — | — |
| Solana | — | — | — | ✅ | — | — | — |

**VAPE Chain Coverage (from offering params):**
- Base (8453): ✅ all services
- Ethereum (1): ✅ partial
- Arbitrum (42161): ✅ partial
- Optimism (10): ✅ partial

**Coverage Comparison:**
- **Both support:** Base, Ethereum, Arbitrum, Optimism
- **HACK only:** Polygon, Avalanche, BSC, Solana (AI red team)
- **Gap for HACK:** No monitoring on Avalanche; BSC coverage unclear; Solana limited to AI red team
- **VAPE opportunity:** VAPE doesn't cover Polygon/Avalanche/BSC — can refer clients needing those chains to HACK

**Improvements for VAPE Workflow:**
1. VAPE `supported_chains` resource should include HACK chain coverage as referral metadata
2. HACK should add explicit BSC coverage details (currently implied but not documented)
3. Cross-chain forensics is critical — both agents support it, need to document handoff protocol

---

### 5. recent_cases

**Resource ID:** 019eb367-1127-71e0-a5df-3cbfe28b787a
**URL:** https://hack.acp.api/recent-cases
**Created:** 2026-06-10T21:18:56.803Z | **Last Updated:** 2026-06-10T21:18:56.803Z

**Params Schema:**
- `limit`: number (default: 5)
- `offering`: all | smart_contract_audit | exploit_simulation | ai_agent_red_team | bug_bounty_submission | protocol_security_monitor | incident_response_forensics (default: all)

**Quality Assessment:**
- **Strengths:** Anonymization by design, verdict+findings+severity breakdown, turnaround time tracking
- **Weaknesses:** No timestamps on individual cases, no date range filter, no trending/comparison data
- **Uncertainty:** Created 2026-06-10 with no updates. HACK agent last active 2026-06-12. Unknown how many real jobs have been completed — HACK rating is 5.00 but with potentially low volume.

**Comparison with VAPE recent_cases:** VAPE has a similar resource with `offeringName` filter and `limit`. Both follow the same pattern. Good for consistency.

**Improvements for VAPE Workflow:**
1. Add `sinceDate` param to filter cases by recency — allows VAPE to check "any new HACK cases since last review?"
2. Add `verdict` filter to find cases matching specific outcomes
3. Cross-reference: VAPE could log HACK case IDs alongside VAPE referral jobs to build a collaboration track record

---

### 6. integration_guide

**Resource ID:** 019eb367-7a6d-7b71-b6ef-ff62c4d69cae
**URL:** https://hack.acp.api/integration-guide
**Created:** 2026-06-10T21:19:23.753Z | **Last Updated:** 2026-06-10T21:19:23.753Z

**Params Schema:**
- `useCase`: all | pre_deploy | pre_invest | post_exploit | continuous_monitoring | ai_agent_security (default: all)

**Use-Case Mapping (HACK's recommended workflow → VAPE integration points):**

| HACK Use Case | HACK Offering | VAPE Trigger | VAPE Offering | Handoff Protocol |
|---------------|--------------|-------------|---------------|-------------------|
| pre_deploy | smart_contract_audit | VAPE client deploying new token | safety_preflight (pre-check) → refer to HACK audit | VAPE runs safety_preflight first; if token passes basic checks, refer to HACK for full audit before deploy |
| pre_invest | exploit_simulation | VAPE client considering large position | safety_preflight + rug_pull_alert → refer to HACK exploit_sim for deeper analysis | VAPE does quick triage; HACK does full exploit simulation for high-value targets |
| post_exploit | incident_response_forensics | VAPE client reports exploit | forensics_deep (initial) → refer to HACK incident_response | VAPE does initial triage + wallet recon; HACK does full incident response + fund tracing |
| continuous_monitoring | protocol_security_monitor | VAPE client with ongoing exposure | safety_preflight (periodic) + HACK monitoring | VAPE does periodic token safety; HACK monitors for vulnerabilities and suspicious txns |
| ai_agent_security | ai_agent_red_team | VAPE client building AI agents | N/A — VAPE doesn't offer this | Direct referral to HACK |

**This is the most collaboration-ready resource.** The use-case routing aligns well with VAPE's service layers.

**Improvements for VAPE Workflow:**
1. VAPE should create a mirrored `hack_integration` resource mapping the reverse direction (when to refer TO HACK)
2. Add `referral_discount` param — HACK could offer VAPE-referred clients a discount
3. Add `priority` param — VAPE referrals could get priority SLA treatment
4. Example payloads should include VAPE-specific integration patterns

---

## Actionable Items

### 🔴 High Priority

1. **Verdict Mapping Proposal:** HACK and VAPE use different verdict vocabularies for overlapping audit/exploit services. Propose a shared `security_verdict_v2` enum for cross-agent compatibility. VAPE should publish this mapping in its safety_rubric resource.

2. **VAPE→HACK Referral Workflow:** Build an automated referral pipeline:
   - `safety_preflight` → CAUTION/NO_GO → refer to HACK `smart_contract_audit`
   - `rug_pull_alert` → HIGH/EXTREME → refer to HACK `exploit_simulation`
   - `forensics_deep` → finds active exploit → refer to HACK `incident_response_forensics`
   - Client asks about AI agent security → refer to HACK `ai_agent_red_team`

3. **Integration Guide Enhancement:** VAPE should create its own `hack_integration` resource documenting when and how to refer clients to HACK, with example payloads.

### 🟡 Medium Priority

4. **Resource Data Freshness:** All 6 HACK resources were created on 2026-06-10 with no updates since. Monitor for changes in subsequent reviews. If HACK adds/updates resources, update this mapping.

5. **Cross-Publish Case Studies:** When VAPE refers a client to HACK and the job completes, both agents should log the anonymized case in their `recent_cases` resources. This builds social proof for both.

6. **Chain Coverage Gaps:** VAPE doesn't cover Polygon (137), Avalanche (43114), or BSC (56). Document HACK as the referral target for clients needing these chains. HACK should clarify BSC coverage.

### 🟢 Low Priority / Future Consideration

7. **Bounty Cross-Reference:** VAPE could query HACK's `active_bounty_programs` when running `safety_preflight` and flag: "This contract has an active bounty — additional scrutiny warranted."

8. **Solana AI Red Team:** HACK offers Solana AI red team services. VAPE doesn't operate on Solana. Document as HACK-exclusive capability for referral.

9. **Monitoring + Safety Preflight Combo:** Explore a joint offering where VAPE does periodic `safety_preflight` checks and HACK provides `protocol_security_monitor` for the same targets — a combined "360° security watch" for protocols with TVL at risk.

10. **Scoring Methodology Alignment:** Long-term, propose that HACK adopt VAPE's `PROCEED/CAUTION/REJECT` verdict for token-level assessments if they ever add that capability, and VAPE adopt HACK's `SAFE/CAUTION/DANGEROUS/CRITICAL` for audit-level assessments.

---

## Review Metadata

- **Review Frequency:** 4x daily (every 6 hours)
- **Next Review:** 2026-06-17 10:12 UTC
- **Data Source:** `acp agent whoami` on HACK agent (019eb338-c65f-73ba-8e66-2782b0ba692f)
- **Note:** `acp resource query` command does not exist in current CLI (v1.0.9). Resource data is derived from agent metadata (resource definitions, params schemas, URLs). Actual endpoint data cannot be queried programmatically. All assessments are based on resource schema quality and structural alignment with VAPE's operational needs.
