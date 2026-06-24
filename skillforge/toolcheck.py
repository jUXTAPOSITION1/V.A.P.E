#!/usr/bin/env python3
"""SKILLFORGE toolcheck — really installs + smoke-tests each registered tool on the runner,
updates version + last_verified + status. Writes broken tools to /tmp/broken_tools.txt for issue.
Real verification only; status reflects actual install/run result."""
import json, os, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "skillforge", "memory", "tools-registry.json")
LESSONS = os.path.join(ROOT, "skillforge", "memory", "lessons.jsonl")
BROKEN = "/tmp/broken_tools.txt"

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sh(cmd, timeout=600):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, str(e)

def main():
    reg = json.load(open(REGISTRY))
    broken = []
    total = verified = 0
    for tier, tools in reg.get("tiers", {}).items():
        for t in tools:
            total += 1
            name = t["name"]
            print(f"[toolcheck] {name}: installing...", flush=True)
            sh(t["install"], timeout=600)  # best-effort install (cached across runs)
            # version probe = smoke test
            rc, out = sh(t.get("version_cmd", "true"), timeout=120)
            if rc == 0 and out:
                ver = out.splitlines()[0][:80]
                t["version"] = ver
                t["status"] = "verified"
                t["last_verified"] = now()
                verified += 1
                print(f"[toolcheck] {name}: OK -> {ver}", flush=True)
            else:
                t["status"] = "broken"
                t["last_verified"] = now()
                broken.append(f"- **{name}** ({t.get('repo')}): `{t.get('version_cmd')}` rc={rc} :: {out[:200]}")
                print(f"[toolcheck] {name}: BROKEN rc={rc}", flush=True)

    reg["updated"] = now()
    json.dump(reg, open(REGISTRY, "w"), indent=2)

    with open(LESSONS, "a") as f:
        f.write(json.dumps({"ts": now(), "action": "toolcheck",
            "outcome": f"{verified}/{total} verified", "bounty_usd": 0,
            "note": f"{len(broken)} broken"}) + "\n")

    if broken:
        open(BROKEN, "w").write("\n".join(broken))
    print(f"[toolcheck] {verified}/{total} verified, {len(broken)} broken")

if __name__ == "__main__":
    main()
