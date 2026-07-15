#!/usr/bin/env python3
"""SKILLFORGE toolcheck — really installs + smoke-tests each registered tool on the runner,
updates version + last_verified + status. Writes broken tools to /tmp/broken_tools.txt for issue.
Real verification only; status reflects actual install/run result.

On top of that mechanical pass/fail: when anything is broken, a frontier-tier
(Grok 4.1 Fast first — see agents/intel_common.py's grok_analysis()) analyst
report is written to intel/reports/ diagnosing WHY each tool likely broke
(version drift, upstream API change, missing dependency) and what to try —
grounded strictly in the real rc/stdout/stderr captured below, with one
bounded web search per broken tool for fresh upstream context. Previously
this check had no narrative output at all beyond a registry JSON diff and a
GitHub issue body built from raw command output."""
import json, os, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
REGISTRY = os.path.join(ROOT, "skillforge", "memory", "tools-registry.json")
LESSONS = os.path.join(ROOT, "skillforge", "memory", "lessons.jsonl")
BROKEN = "/tmp/broken_tools.txt"

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Tools install to user-writable bins; ensure they're on PATH for install + probe.
HOME = os.path.expanduser("~")
EXTRA_PATH = ":".join([os.path.join(HOME, p) for p in (".cargo/bin", ".cyfrin/bin", ".foundry/bin", ".local/bin")])
ENV = dict(os.environ, PATH=EXTRA_PATH + ":" + os.environ.get("PATH", ""))

def sh(cmd, timeout=600):
    try:
        # cmd always comes from tools-registry.json (repo-controlled config), never
        # external/runtime input, and genuinely needs shell features (pipes, $(...),
        # || fallback chaining) that a shlex.split()+shell=False rewrite would break.
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=ENV)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, str(e)

def main():
    reg = json.load(open(REGISTRY))
    broken = []
    broken_detail = []
    total = verified = 0
    for tier, tools in reg.get("tiers", {}).items():
        for t in tools:
            total += 1
            name = t["name"]
            # Tools with a documented upstream limitation (e.g. paid-only API
            # endpoints) are not code breakages; skip probing and don't flag.
            if t.get("known_limitation"):
                t["status"] = "unsupported"
                t["last_verified"] = now()
                print(f"[toolcheck] {name}: known upstream limitation (skipped, not broken)", flush=True)
                continue
            print(f"[toolcheck] {name}: installing...", flush=True)
            sh(t["install"], timeout=600)  # best-effort install (cached across runs)
            # version probe = smoke test
            rc, out = sh(t.get("version_cmd", "true"), timeout=120)
            needs_key = t.get("requires_key")
            err_markers = ('"error"', 'NOTOK', 'not supported', 'Invalid API Key', 'rate limit')
            has_err = any(m.lower() in out.lower() for m in err_markers)
            if rc == 0 and out and not has_err:
                ver = out.splitlines()[0][:80]
                t["version"] = ver
                t["status"] = "verified"
                t["last_verified"] = now()
                verified += 1
                print(f"[toolcheck] {name}: OK -> {ver}", flush=True)
            elif needs_key and not os.environ.get(needs_key):
                # Tool is fine; just no key in this environment. Not a breakage.
                t["status"] = "needs_key"
                t["last_verified"] = now()
                print(f"[toolcheck] {name}: needs {needs_key} (skipped, not broken)", flush=True)
            else:
                t["status"] = "broken"
                t["last_verified"] = now()
                broken.append(f"- **{name}** ({t.get('repo')}): `{t.get('version_cmd')}` rc={rc} :: {out[:200]}")
                broken_detail.append({"name": name, "repo": t.get("repo"), "tier": tier,
                                       "install": t.get("install"), "version_cmd": t.get("version_cmd"),
                                       "rc": rc, "output": out[:500]})
                print(f"[toolcheck] {name}: BROKEN rc={rc}", flush=True)

    reg["updated"] = now()
    tmp = REGISTRY + ".tmp"
    with open(tmp, "w") as f:
        json.dump(reg, f, indent=2)
    os.replace(tmp, REGISTRY)  # atomic

    with open(LESSONS, "a") as f:
        f.write(json.dumps({"ts": now(), "action": "toolcheck",
            "outcome": f"{verified}/{total} verified", "bounty_usd": 0,
            "note": f"{len(broken)} broken"}) + "\n")

    if broken:
        open(BROKEN, "w").write("\n".join(broken))
        write_tool_gap_report(broken_detail, verified, total)
    print(f"[toolcheck] {verified}/{total} verified, {len(broken)} broken")


def write_tool_gap_report(broken_detail, verified, total):
    """Real analyst report, not just a raw-output issue body: for each broken
    tool, one bounded web search checks for a fresh upstream fix/changelog,
    then a frontier-tier (Grok 4.1 Fast first) pass diagnoses the likely
    cause and next step per tool — grounded strictly in the real rc/output
    captured above, explicitly barred from inventing a root cause the data
    doesn't support. Never blocks the rest of toolcheck on failure."""
    try:
        from agents import intel_common as ic
    except Exception as e:
        print(f"[toolcheck] tool-gap report skipped (intel_common unavailable: {e})")
        return

    researched = []
    for tool in broken_detail:
        search = ic.web_search_snippets(
            f"{tool['name']} {tool.get('repo') or ''} error fix changelog 2026", max_results=5
        )
        researched.append({**tool, "search": search})

    grounding_parts = []
    for tool in researched:
        results = tool["search"].get("results", [])
        research_lines = "\n".join(f"  - {r['title']}: {r['snippet']}" for r in results) or "  (no web research available)"
        grounding_parts.append(
            f"### {tool['name']} ({tool.get('repo') or 'no repo listed'}, tier: {tool.get('tier')})\n"
            f"Install command: `{tool.get('install')}`\n"
            f"Version/probe command: `{tool.get('version_cmd')}`\n"
            f"Exit code: {tool['rc']}\n"
            f"Real captured output:\n```\n{tool['output']}\n```\n"
            f"Web research ({tool['search'].get('provider') or 'unavailable'}):\n{research_lines}"
        )
    grounding = f"Registry status: {verified}/{total} tools verified this cycle.\n\n" + "\n\n".join(grounding_parts)

    briefing = ic.grok_analysis(
        "tooling/DevOps diagnostician",
        grounding,
        instructions=(
            "For each broken tool above, diagnose the most likely root cause (version drift, an "
            "upstream API/CLI change, a missing system dependency, a flaky network install) using "
            "ONLY the real exit code/output/research given — never invent an error you weren't shown. "
            "Propose one concrete next step per tool (a specific install-command fix, a version pin "
            "to try, or 'needs a human to look at X specifically'). If the web research didn't surface "
            "anything useful for a tool, say so rather than padding."
        ),
        max_tokens=2600,
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""# SKILLFORGE Tool Gap Report

**Date:** {stamp}
**Registry status:** {verified}/{total} tools verified, {len(broken_detail)} broken this cycle

---

## Analyst Briefing (Grok 4.1 Fast)

{briefing}

---

## Raw Per-Tool Data

{chr(10).join(grounding_parts)}

---

*Report generated by `skillforge/toolcheck.py`. The registry status above is deterministic
(real install/smoke-test result); the Analyst Briefing is Grok 4.1 Fast's (or the next
available provider in `agents.llm.FRONTIER_ORDER`) diagnosis of that same real data plus
this cycle's web research — it never overrides the actual pass/fail result.*
"""
    try:
        path = ic.write_report("skillforge-toolcheck", body)
        print(f"[toolcheck] wrote tool gap report -> {os.path.relpath(path, ROOT)}")
    except Exception as e:
        print(f"[toolcheck] could not write tool gap report: {e}")

if __name__ == "__main__":
    main()
