"""
Real garak (NVIDIA's LLM vulnerability scanner) scan against VAPE's actual
production model — garak has a native `groq` generator keyed by the exact
same GROQ_API_KEY VAPE already uses everywhere else (agents/llm.py,
CI secrets), so this needs zero new secrets and zero custom generator code.

Per skillforge/skills/ai-agent-redteam.md step 2: "capture real hit rates,
never estimate." This shells out to the existing garak.sh wrapper, reads
garak's own JSONL report (entry_type == "eval" lines carry real
passed/fails/total_evaluated counts per probe+detector pair — verified
against a real garak run's actual report format, not guessed), and appends
a finding for any probe with a nonzero fail rate.

Usage: python run_garak_scan.py [model_name] [probes]
  Defaults match the skill doc's recommended starting set, against the
  same model agents/llm.py's "deep" tier actually uses in production.
"""
import glob
import json
import os
import subprocess
import time
from datetime import datetime, timezone

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
REPORTS_DIR = os.path.join(_REPO_ROOT, "reports")
FINDINGS_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "findings.jsonl")
GARAK_SH = os.path.join(_THIS_DIR, "garak.sh")

DEFAULT_MODEL = "llama-3.3-70b-versatile"  # matches agents/llm.py's Groq "deep" tier — the
                                           # model that actually generates VAPE's real reports
DEFAULT_PROBES = "promptinject,dan,encoding,leakreplay,sysprompt_extraction,packagehallucination"
GARAK_RUNS_DIR = os.path.expanduser("~/.local/share/garak/garak_runs")


def _find_new_report(started_at):
    """garak's own report path isn't returned structurally — it's printed in
    a banner line whose exact wording has changed across garak versions
    (confirmed empirically this session). Globbing for the newest report
    file created after this run started is version-independent."""
    candidates = glob.glob(os.path.join(GARAK_RUNS_DIR, "*.report.jsonl"))
    candidates = [c for c in candidates if os.path.getmtime(c) >= started_at - 1]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def run_scan(model_name=DEFAULT_MODEL, probes=DEFAULT_PROBES):
    if not os.getenv("GROQ_API_KEY"):
        return {"skipped": True, "reason": "no GROQ_API_KEY"}

    started_at = time.time()
    proc = subprocess.run(
        [GARAK_SH, "groq", model_name, probes],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=1800,
    )
    print(proc.stdout[-3000:])
    if proc.returncode != 0:
        print(proc.stderr[-2000:])

    report_path = _find_new_report(started_at)
    if not report_path:
        return {"skipped": True, "reason": "no garak report produced (install/run failure — see stderr above)"}

    evals = []
    with open(report_path) as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("entry_type") == "eval":
                evals.append(entry)

    return {"skipped": False, "report_path": report_path, "evals": evals, "model_name": model_name}


def _append_finding(ev, model_name):
    fail_rate = ev["fails"] / ev["total_evaluated"] if ev["total_evaluated"] else 0
    entry = {
        "category": "finding",
        "title": f"AI red-team (garak): {ev['probe']} / {ev['detector']} — {ev['fails']}/{ev['total_evaluated']} failed",
        "content": (
            f"garak scan of VAPE's real production model ({model_name}, Groq) found "
            f"{ev['fails']} failing case(s) out of {ev['total_evaluated']} for probe "
            f"'{ev['probe']}' under detector '{ev['detector']}' (fail rate {fail_rate:.0%})."
        ),
        "source": "skillforge/tools/ai-redteam/run_garak_scan.py",
        "tags": ["ai-redteam", "garak", "vape-report-pipeline"],
        "confidence": 0.9,
        "severity": "HIGH" if fail_rate >= 0.2 else "MED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(FINDINGS_PATH), exist_ok=True)
        with open(FINDINGS_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[run_garak_scan] could not append finding: {e}")


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORTS_DIR, f"redteam_garak_{stamp}.md")

    result = run_scan()
    if result.get("skipped"):
        with open(report_path, "w") as f:
            f.write(f"# garak Scan — {datetime.now(timezone.utc).isoformat()}\n\n"
                     f"Skipped: {result['reason']}\n")
        print(f"[run_garak_scan] skipped: {result['reason']}")
        return

    lines = [f"# garak Scan — {datetime.now(timezone.utc).isoformat()}", "",
             f"Model: groq/{result['model_name']} (agents/llm.py's real \"deep\" tier model). "
             f"Probes: {DEFAULT_PROBES}.", ""]
    any_fail = False
    for ev in result["evals"]:
        fail_rate = ev["fails"] / ev["total_evaluated"] if ev["total_evaluated"] else 0
        status = "FAIL" if ev["fails"] > 0 else "PASS"
        any_fail = any_fail or ev["fails"] > 0
        lines.append(f"- {status} — {ev['probe']} / {ev['detector']}: "
                      f"{ev['passed']}/{ev['total_evaluated']} passed ({fail_rate:.0%} fail rate)")
        if ev["fails"] > 0:
            _append_finding(ev, result["model_name"])
    lines.append("")
    lines.append(
        "## Verdict\n"
        + (f"At least one probe/detector pair had real failures — see "
           f"{os.path.relpath(FINDINGS_PATH, _REPO_ROOT)} and the full garak report at "
           f"{result['report_path']}." if any_fail else
           "All probes passed 100% this cycle. Re-run regularly with a wider probe set — "
           "this run covered a fixed subset, not garak's full battery.")
    )
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[run_garak_scan] cycle complete. Report: {os.path.relpath(report_path, _REPO_ROOT)}")


if __name__ == "__main__":
    main()
