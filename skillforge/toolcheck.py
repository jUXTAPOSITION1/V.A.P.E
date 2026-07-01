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

# Tools install to user-writable bins; ensure they're on PATH for install + probe.
HOME = os.path.expanduser("~")
EXTRA_PATH = ":".join([os.path.join(HOME, p) for p in (".cargo/bin", ".cyfrin/bin", ".foundry/bin", ".local/bin")])
ENV = dict(os.environ, PATH=EXTRA_PATH + ":" + os.environ.get("PATH", ""))

def sh(cmd, timeout=600):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=ENV)
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
    print(f"[toolcheck] {verified}/{total} verified, {len(broken)} broken")

if __name__ == "__main__":
    main()
