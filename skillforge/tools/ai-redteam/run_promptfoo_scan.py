"""
Real promptfoo redteam scan against VAPE's actual system prompt
(agents/run.py::VAPE_REPORT_SYSTEM), via promptfoo's native Groq provider
(keyed by the same GROQ_API_KEY VAPE already uses — confirmed against
promptfoo's own provider source; zero new secrets).

Two-step process (`redteam run`'s own `-o` only captures generated test
cases, not results — confirmed via `promptfoo redteam run --help`):
  1. `redteam generate` — builds adversarial test cases for the plugins in
     the config gen_promptfoo_config.py writes, into a full evaluable config.
  2. `eval -o results.json` — actually runs them against the real target
     and writes structured JSON results (confirmed real flag/format via
     `promptfoo eval --help`).

Usage: python run_promptfoo_scan.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_DIR)))
sys.path.insert(0, _REPO_ROOT)
sys.path.insert(0, _THIS_DIR)

from gen_promptfoo_config import generate as gen_config  # noqa: E402

REPORTS_DIR = os.path.join(_REPO_ROOT, "reports")
FINDINGS_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "findings.jsonl")
PROMPTFOO_SH = os.path.join(_THIS_DIR, "promptfoo.sh")
WORK_DIR = "/tmp/vape-promptfoo"


def run_scan():
    if not os.getenv("GROQ_API_KEY"):
        return {"skipped": True, "reason": "no GROQ_API_KEY"}

    os.makedirs(WORK_DIR, exist_ok=True)
    base_config = os.path.join(WORK_DIR, "base.yaml")
    generated_config = os.path.join(WORK_DIR, "generated.yaml")
    results_path = os.path.join(WORK_DIR, "results.json")
    gen_config(base_config)

    gen_proc = subprocess.run(
        [PROMPTFOO_SH, "redteam", "generate", "-c", base_config, "-o", generated_config, "--force"],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=900,
    )
    print(gen_proc.stdout[-3000:])
    if gen_proc.returncode != 0 or not os.path.exists(generated_config):
        return {"skipped": True, "reason": f"redteam generate failed: {gen_proc.stderr[-1000:]}"}

    eval_proc = subprocess.run(
        [PROMPTFOO_SH, "eval", "-c", generated_config, "-o", results_path, "--no-progress-bar", "--no-table"],
        cwd=_REPO_ROOT, capture_output=True, text=True, timeout=900,
    )
    print(eval_proc.stdout[-3000:])
    if not os.path.exists(results_path):
        return {"skipped": True, "reason": f"eval produced no results file: {eval_proc.stderr[-1000:]}"}

    with open(results_path) as f:
        results = json.load(f)
    return {"skipped": False, "results": results}


def _extract_cases(results):
    """promptfoo's eval JSON nests results under results.results (array of
    per-test-case records with .success / .testCase.metadata.pluginId)."""
    body = results.get("results", results)
    cases = body.get("results") if isinstance(body, dict) else None
    return cases or []


def _append_finding(plugin_id, failing_count, total_count):
    entry = {
        "category": "finding",
        "title": f"AI red-team (promptfoo): {plugin_id} — {failing_count}/{total_count} failed",
        "content": (
            f"promptfoo redteam scan of VAPE's real system prompt (agents/run.py::"
            f"VAPE_REPORT_SYSTEM) via groq:llama-3.3-70b-versatile: plugin '{plugin_id}' "
            f"had {failing_count} failing case(s) out of {total_count}."
        ),
        "source": "skillforge/tools/ai-redteam/run_promptfoo_scan.py",
        "tags": ["ai-redteam", "promptfoo", "vape-report-pipeline"],
        "confidence": 0.85,
        "severity": "HIGH" if total_count and failing_count / total_count >= 0.3 else "MED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(FINDINGS_PATH), exist_ok=True)
        with open(FINDINGS_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[run_promptfoo_scan] could not append finding: {e}")


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORTS_DIR, f"redteam_promptfoo_{stamp}.md")

    result = run_scan()
    if result.get("skipped"):
        with open(report_path, "w") as f:
            f.write(f"# promptfoo Scan — {datetime.now(timezone.utc).isoformat()}\n\n"
                     f"Skipped: {result['reason']}\n")
        print(f"[run_promptfoo_scan] skipped: {result['reason']}")
        return

    cases = _extract_cases(result["results"])
    by_plugin = {}
    for c in cases:
        # Confirmed against a real (non-redteam) promptfoo eval run that
        # case["success"] is the right field; pluginId's exact location for
        # redteam-generated cases couldn't be verified without live network
        # access in this environment, so check both documented locations.
        plugin_id = (
            ((c.get("testCase") or {}).get("metadata") or {}).get("pluginId")
            or (c.get("metadata") or {}).get("pluginId")
            or "unknown"
        )
        by_plugin.setdefault(plugin_id, {"pass": 0, "fail": 0})
        if c.get("success"):
            by_plugin[plugin_id]["pass"] += 1
        else:
            by_plugin[plugin_id]["fail"] += 1

    lines = [f"# promptfoo Scan — {datetime.now(timezone.utc).isoformat()}", "",
             "Target: agents/run.py::VAPE_REPORT_SYSTEM (real system prompt) via "
             "groq:llama-3.3-70b-versatile — VAPE's real production model.", ""]
    any_fail = False
    for plugin_id, counts in by_plugin.items():
        total = counts["pass"] + counts["fail"]
        status = "FAIL" if counts["fail"] > 0 else "PASS"
        any_fail = any_fail or counts["fail"] > 0
        lines.append(f"- {status} — {plugin_id}: {counts['pass']}/{total} passed")
        if counts["fail"] > 0:
            _append_finding(plugin_id, counts["fail"], total)
    if not by_plugin:
        lines.append("No test cases were generated/evaluated this cycle (see raw results.json in "
                      f"{WORK_DIR} for the actual promptfoo output if this looks wrong).")
    lines.append("")
    lines.append(
        "## Verdict\n"
        + ("At least one plugin had real failures — see findings.jsonl." if any_fail else
           "All plugins passed this cycle. Re-run regularly — this covered a fixed plugin subset.")
    )
    with open(report_path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[run_promptfoo_scan] cycle complete. Report: {os.path.relpath(report_path, _REPO_ROOT)}")


if __name__ == "__main__":
    main()
