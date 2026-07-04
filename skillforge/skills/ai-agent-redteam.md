# Skill: AI Agent & LLM Red-Teaming

**Tier:** ai-redteam · **Tools:** garak, promptfoo, deepteam · **Status:** live (daily, `redteam-deep.yml`)

## When to use
Assessing any LLM-powered system or autonomous agent (incl. Virtuals ACP agents) for
jailbreak, prompt injection, data leakage, tool-abuse, and guardrail bypass. HACK's core
AI-security lane — pairs with the SC-security tier for full-stack agent audits.

## Real, wired campaigns (not just the wrapper scripts below)
- `agents/redteam.py` — custom prompt-injection test against the real attacker-controlled-
  token-symbol -> grounding path, daily via `redteam.yml`.
- `skillforge/tools/ai-redteam/run_garak_scan.py` — garak against garak's native `groq`
  generator (same `GROQ_API_KEY`, VAPE's real "deep" model), daily via `redteam-deep.yml`.
- `skillforge/tools/ai-redteam/gen_promptfoo_config.py` + `run_promptfoo_scan.py` — promptfoo
  against its native `groq:` provider, config generated from the REAL
  `agents/run.py::VAPE_REPORT_SYSTEM` (never hand-copied, can't drift), daily.
- `skillforge/tools/ai-redteam/campaign_vape.py` + `vape_deepeval_model.py` — deepteam
  campaign against the real report pipeline, using VAPE's own free-tier model as
  simulator+judge (`vape_deepeval_model.py`'s `VapeLLM` — zero new secrets/cost; see its
  docstring for the self-judging honesty caveat), daily.

All four append real findings to `skillforge/memory/findings.jsonl` and write a report under
`reports/` — this is the reference procedure for adding MORE probes/plugins/vulnerability
types to those scripts, not a from-scratch manual process.

## Procedure (reproducible, real-data-only)
1. **Scope the target.** Identify model/endpoint, system prompt exposure, tool/function surface,
   and trust boundaries (what the agent can read/write/spend).
2. **Broad scan — garak:** `skillforge/tools/ai-redteam/garak.sh <model_type> <model_name> <probes>`
   - Start with `promptinject,dan,encoding,leakreplay` probes. garak emits a JSONL report with
     pass/fail per probe — capture real hit rates, never estimate.
3. **Targeted suite — promptfoo:** generate a config from the real target prompt (see
   `gen_promptfoo_config.py` — never hand-write/copy the prompt into YAML), then
   `redteam generate -c config.yaml -o generated.yaml` followed by `eval -c generated.yaml
   -o results.json` (promptfoo's `redteam run -o` only captures generated tests, not results —
   confirmed via `--help`, hence the two-step form).
4. **Campaign — deepteam:** write a `campaign.py` using deepteam's `red_team()` with the relevant
   vulnerabilities (PromptInjection, PIILeakage, BiasVulnerability, etc.) + attack enhancements;
   run via `skillforge/tools/ai-redteam/deepteam.sh campaign.py`. If wiring a custom
   `DeepEvalBaseLLM` (e.g. to avoid an OpenAI key), `generate`/`a_generate` MUST raise
   `TypeError` when called with a `schema=` kwarg they can't honor — deepteam's own
   `generate_with_schema` catches that to fall back to its text+JSON-extraction path; silently
   swallowing `schema` via `**kwargs` breaks that contract (confirmed by hand this session —
   every simulated attack errored with `'str' object has no attribute 'data'` until fixed).
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
