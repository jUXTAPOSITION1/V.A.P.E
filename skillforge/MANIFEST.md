# 🦍🔧 VAPE SKILLFORGE — Persistent Skill & Memory Ecosystem

A self-reinforcing loop that constantly sharpens VAPE/HACK's bug-bounty & white-hat skill set.
**Real data only. No hypotheticals, no fiction, no simulated tool output.**

## Architecture: two compute tiers

### Tier 1 — GitHub Actions (frequent, FREE, zero local compute)
| Workflow | Cadence | Job | LLM? |
|---|---|---|---|
| `skillforge-harvest.yml` | hourly | Pull live CVEs (NVD), new GH security-tool releases, active bounty programs → append `memory/findings.jsonl` + flag new tools | no |
| `skillforge-toolcheck.yml` | every 4h (6×/day) | Clone+smoke-test each tool in `tools-registry.json`, update versions + `last_verified`, auto-issue on breakage | no |
| `skillforge-synthesize.yml` | daily 06:00 UTC | Groq reads memory, distills new `skills/*.md` playbooks from real findings, opens a **PR** | yes (Groq free) |

### Tier 2 — OpenClaw agent (deep, 4×/day, owner compute)
Extends `vape-intel-sweep`. Does what runners can't: cross-vertical correlation, writing new tool
wrappers when a capability is used here but missing from the repo, memory dedupe/prune, lessons scoring.

## The "mirror every tool" rule
Any capability VAPE uses through OpenClaw (scanner, API, analysis) MUST get a repo-native,
runnable equivalent committed under `tools/<tier>/<name>.sh` and registered in `tools-registry.json`.
A skill isn't "learned" until it's reproducible from this repo with one command.

## Memory base (append-only, git-versioned, never lost)
- `memory/tools-registry.json` — canonical tool list: install + invoke + version + last_verified + status
- `memory/findings.jsonl`  — real vulns/audits/CVEs: {ts, source, severity, target, summary, ref}
- `memory/skills.jsonl`    — learned skills: {ts, skill, tier, tools[], playbook}
- `memory/lessons.jsonl`   — what worked/failed: {ts, action, outcome, bounty_usd, note}
- `memory/INDEX.md`        — human rollup, regenerated each cycle

## Self-improvement scoring (each cycle appends to lessons.jsonl)
tools_verified / tools_total · new_skills · new_findings · dead_tools_pruned · bounties_landed.
VAPE measurably sharpens on REAL outcomes, not vibes.

## Commit policy
- Pure data (harvest, toolcheck) → **direct commit** to main.
- Skill changes (synthesize) → **PR** for review.

## Scope (phased)
- **Phase 1 (NOW):** smart-contract security tier — Slither, Aderyn, Mythril, Echidna, Foundry.
- Phase 2: AI red-team tier (Garak, Promptfoo, DeepTeam).
- Phase 3: recon/forensics tier (token-safety, wallet-trace, bridge-trace).

*The chain never lies. VAPE makes sure you hear the truth first.* 🔫🦍
