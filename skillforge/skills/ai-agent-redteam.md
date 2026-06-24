# Skill: AI Agent & LLM Red-Teaming

**Tier:** ai-redteam · **Tools:** garak, promptfoo, deepteam · **Status:** active

## When to use
Assessing any LLM-powered system or autonomous agent (incl. Virtuals ACP agents) for
jailbreak, prompt injection, data leakage, tool-abuse, and guardrail bypass. HACK's core
AI-security lane — pairs with the SC-security tier for full-stack agent audits.

## Procedure (reproducible, real-data-only)
1. **Scope the target.** Identify model/endpoint, system prompt exposure, tool/function surface,
   and trust boundaries (what the agent can read/write/spend).
2. **Broad scan — garak:** `skillforge/tools/ai-redteam/garak.sh <model_type> <model_name> <probes>`
   - Start with `promptinject,dan,encoding,leakreplay` probes. garak emits a JSONL report with
     pass/fail per probe — capture real hit rates, never estimate.
3. **Targeted suite — promptfoo:** `skillforge/tools/ai-redteam/promptfoo.sh redteam init` then
   `... redteam run -c redteam.yaml`. Build adversarial cases for THIS agent's actual tools/prompts.
4. **Campaign — deepteam:** write a `campaign.py` using deepteam's `red_team()` with the relevant
   vulnerabilities (PromptInjection, PIILeakage, BiasVulnerability, etc.) + attack enhancements;
   run via `skillforge/tools/ai-redteam/deepteam.sh campaign.py`.
5. **Correlate + rate.** Dedup across tools, severity-rate each real finding (CRITICAL/HIGH/MED/LOW),
   map to attack class. Append to `skillforge/memory/findings.jsonl` with the report ref.
6. **Mitigations.** For each confirmed vuln give a concrete guardrail/fix (input filter, tool
   allow-list, output check, system-prompt hardening).

## Quality gates
- Every finding cites a real tool run + report artifact. No hypothetical exploits.
- White-hat only: test in authorized/sandboxed contexts; responsible disclosure for third parties.
- Capture tool versions from each wrapper's stderr banner for reproducibility.

## Known limitations
- garak pulls torch/transformers (heavy first install) — cache it; some probes need provider API keys.
- promptfoo needs Node 18+; deepteam is a library (campaigns are code, not one-liners).
- LLM-judged attacks can have false positives → manually confirm HIGH/CRITICAL before disclosure.

_Phase 2 tier. Updated by skillforge-synthesize as real campaigns accumulate._
