#!/usr/bin/env python3
"""SKILLFORGE synthesize — reads REAL memory (findings/lessons/registry), asks Groq to distill
actionable skill playbooks + regenerate INDEX.md. Real data only; the model is instructed never
to invent tools, CVEs, or results. Outputs go to a PR (not direct to main)."""
import json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = os.path.join(ROOT, "skillforge", "memory")
SKILLS = os.path.join(ROOT, "skillforge", "skills")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def tail(path, n=200):
    if not os.path.exists(path): return []
    lines = open(path).read().splitlines()
    out = []
    for l in lines[-n:]:
        if not l.strip(): continue
        try: out.append(json.loads(l))
        except Exception: continue  # skip malformed (e.g. stray merge markers)
    return out

def regenerate_index(reg, findings, skills, lessons):
    lines = ["# SKILLFORGE Memory Index", f"_Regenerated {now()}_\n"]
    lines.append("## Tool Registry")
    for tier, tools in reg.get("tiers", {}).items():
        if not tools: continue
        lines.append(f"\n### {tier}")
        for t in tools:
            lines.append(f"- **{t['name']}** `{t.get('version') or '?'}` — "
                         f"status: {t.get('status','?')} (verified {t.get('last_verified') or 'never'})")
    lines.append("\n## Stats")
    lines.append(f"- findings logged: {sum(1 for _ in open(os.path.join(MEM,'findings.jsonl'))) if os.path.exists(os.path.join(MEM,'findings.jsonl')) else 0}")
    lines.append(f"- skills: {len([f for f in os.listdir(SKILLS) if f.endswith('.md')])}")
    lines.append("- recent severities: " + ", ".join(
        sorted({f.get('severity','?') for f in findings[-50:]})))
    open(os.path.join(MEM, "INDEX.md"), "w").write("\n".join(lines) + "\n")

def main():
    reg = json.load(open(os.path.join(MEM, "tools-registry.json")))
    findings = tail(os.path.join(MEM, "findings.jsonl"), 200)
    lessons = tail(os.path.join(MEM, "lessons.jsonl"), 100)
    skills = tail(os.path.join(MEM, "skills.jsonl"), 100)

    regenerate_index(reg, findings, skills, lessons)

    # Was a direct Groq SDK call with no fallback — every other LLM call site
    # in this repo goes through agents.llm.ask()'s multi-provider chain
    # (Groq -> Cerebras -> OpenRouter -> Gemini -> GitHub Models -> Together),
    # so a Groq-only outage silently skipped distillation here while every
    # other job degraded gracefully. Real rate-limit audit evidence: ~3.5% of
    # hourly bounty-cycle runs already hit "Rate limit persistent" on Groq
    # alone (see skillforge/memory/build_log.jsonl), so a single-provider
    # dependency here isn't theoretical.
    try:
        from agents.llm import ask_oci_grok, FRONTIER_ORDER
    except Exception as e:
        print(f"[synthesize] agents.llm unavailable ({e}) — index regenerated, skipping distillation")
        return
    try:
        verified = [t['name'] for tier in reg['tiers'].values() for t in tier if t.get('status')=='verified']
        sys_p = ("You are HACK, VAPE's white-hat security specialist. Distill ONE concrete, "
                 "reproducible skill playbook from the REAL data provided. Never invent tools, "
                 "CVEs, or results. Only reference verified tools and real findings. Output GitHub "
                 "markdown for a single skills/*.md file: title, when-to-use, step-by-step procedure "
                 "using the actual wrapper paths, quality gates, limitations. No fluff.")
        usr = (f"Verified tools: {verified}\n"
               f"Recent real findings (last 30): {json.dumps(findings[-30:])[:4000]}\n"
               f"Recent lessons: {json.dumps(lessons[-20:])[:1500]}\n"
               "Produce the most valuable NEW or UPDATED playbook given this real data.")
        # ask_oci_grok() tries OCI-hosted Grok 4.3 first, falling back to
        # VAPE's Vertex-tuned model (if VAPE_VERTEX_ACCESS_TOKEN is set this
        # run), falling back further to FRONTIER_ORDER — tier/provider_order
        # here control ONLY that final fallback, so a run with nothing
        # configured behaves exactly as before.
        content, provider = ask_oci_grok(sys_p, usr, temperature=0.4, max_tokens=2048,
                                          tier="deep", provider_order=FRONTIER_ORDER)
        content = content.strip()
        print(f"[synthesize] distilled via {provider}")
        # derive filename from first heading
        first = next((l for l in content.splitlines() if l.startswith("#")), "# distilled-skill")
        slug = "".join(c.lower() if c.isalnum() else "-" for c in first.lstrip("# ").strip())[:50].strip("-")
        path = os.path.join(SKILLS, f"{slug or 'distilled-skill'}.md")
        open(path, "w").write(content + f"\n\n_Distilled {now()} from real SKILLFORGE memory._\n")
        with open(os.path.join(MEM, "skills.jsonl"), "a") as f:
            f.write(json.dumps({"ts": now(), "skill": slug, "tier": "synthesized",
                "tools": verified, "playbook": f"skills/{slug}.md", "note": "auto-distilled"}) + "\n")
        print(f"[synthesize] wrote {path}")
    except Exception as e:
        print(f"[synthesize] distillation failed (index still updated): {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
