#!/usr/bin/env python3
"""SKILLFORGE synthesize — reads REAL memory (findings/lessons/registry), asks Groq to distill
actionable skill playbooks + regenerate INDEX.md. Real data only; the model is instructed never
to invent tools, CVEs, or results. Outputs go to a PR (not direct to main)."""
import json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = os.path.join(ROOT, "skillforge", "memory")
SKILLS = os.path.join(ROOT, "skillforge", "skills")

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def tail(path, n=200):
    if not os.path.exists(path): return []
    lines = open(path).read().splitlines()
    return [json.loads(l) for l in lines[-n:] if l.strip()]

def regenerate_index(reg, findings, skills, lessons):
    lines = [f"# SKILLFORGE Memory Index", f"_Regenerated {now()}_\n"]
    lines.append("## Tool Registry")
    for tier, tools in reg.get("tiers", {}).items():
        if not tools: continue
        lines.append(f"\n### {tier}")
        for t in tools:
            lines.append(f"- **{t['name']}** `{t.get('version') or '?'}` — "
                         f"status: {t.get('status','?')} (verified {t.get('last_verified') or 'never'})")
    lines.append(f"\n## Stats")
    lines.append(f"- findings logged: {sum(1 for _ in open(os.path.join(MEM,'findings.jsonl'))) if os.path.exists(os.path.join(MEM,'findings.jsonl')) else 0}")
    lines.append(f"- skills: {len([f for f in os.listdir(SKILLS) if f.endswith('.md')])}")
    lines.append(f"- recent severities: " + ", ".join(
        sorted({f.get('severity','?') for f in findings[-50:]})))
    open(os.path.join(MEM, "INDEX.md"), "w").write("\n".join(lines) + "\n")

def main():
    reg = json.load(open(os.path.join(MEM, "tools-registry.json")))
    findings = tail(os.path.join(MEM, "findings.jsonl"), 200)
    lessons = tail(os.path.join(MEM, "lessons.jsonl"), 100)
    skills = tail(os.path.join(MEM, "skills.jsonl"), 100)

    regenerate_index(reg, findings, skills, lessons)

    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("[synthesize] no GROQ_API_KEY — index regenerated, skipping distillation")
        return
    try:
        from groq import Groq
        client = Groq(api_key=key)
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
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":sys_p},{"role":"user","content":usr}],
            temperature=0.4, max_tokens=2048)
        content = resp.choices[0].message.content.strip()
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
