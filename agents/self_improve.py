"""
VAPE self-improvement agent — grounded, gated, opens a real PR.

The old version of this file called the LLM with a single vague sentence
("review the agents folder") and zero real content — exactly the pattern
that made agents/run.py's --review-repo mode hallucinate fictional files
before that was fixed. This version never asks the LLM to *find* a problem;
it finds one first with cheap, deterministic checks (pyflakes for real
undefined-name/unused-import bugs, then the same tool-registry gap data
agents/run.py's reports are grounded in), and only calls the LLM — via
agents.builder.Builder, which is real: multi-provider, Memory-grounded,
security-validated — to *propose a fix* for a concrete, evidence-backed
target. If no real issue is found, it says so and does nothing; it never
fabricates a target to fill a report.

The proposal is never applied to existing files automatically. It lands as
a new file under agents/proposals/ on a fresh branch, and a real GitHub PR
is opened for human review — Builder's security validation plus a human PR
review are the two gates before anything reaches main. This never merges.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.builder import Builder, validate_security  # noqa: E402

try:
    from skillforge.mcp import GitHubMCPWrapper  # noqa: E402
except Exception:
    GitHubMCPWrapper = None

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(_REPO_ROOT, "reports")
PROPOSALS_DIR = os.path.join(_REPO_ROOT, "agents", "proposals")
REGISTRY_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "tools-registry.json")
REPO_SLUG = "jUXTAPOSITION1/V.A.P.E"


def _now_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _run(cmd, **kwargs):
    return subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True, **kwargs)


# ─── Step 1: find a real, concrete target — no LLM, no guessing ──────────────

def _find_pyflakes_issue():
    """Real undefined-name / unused-import bugs via pyflakes — exactly the
    defect class (missing `import os` while calling `os.getenv`) found by
    hand in agents/self_pr.py this session. Skips agents/proposals/ (this
    script's own prior output) and itself."""
    try:
        result = _run([sys.executable, "-m", "pyflakes", "agents"])
    except FileNotFoundError:
        return None
    output = (result.stdout or "") + (result.stderr or "")
    for line in output.splitlines():
        m = re.match(r"^(agents/[^:]+\.py):(\d+):\d*:?\s*(.+)$", line.strip())
        if not m:
            continue
        rel_path, line_no, message = m.groups()
        if rel_path.startswith("agents/proposals/") or rel_path.endswith("self_improve.py"):
            continue
        return {
            "module": rel_path,
            "issue": f"pyflakes: {message} (line {line_no})",
            "kind": "pyflakes",
        }
    return None


def _find_tool_registry_gap():
    """Same real gap data agents/run.py's report grounding already uses —
    a confirmed broken tool or one blocked on a missing key."""
    try:
        with open(REGISTRY_PATH) as f:
            reg = json.load(f)
    except Exception:
        return None
    for tier, tools in reg.get("tiers", {}).items():
        for t in tools:
            status = t.get("status")
            if status == "broken":
                return {
                    "module": t.get("name", "?"),
                    "issue": f"Tool registry marks '{t.get('name')}' ({tier}) as broken: {t.get('purpose', '')}",
                    "kind": "tool-gap",
                }
            if status == "needs_key":
                return {
                    "module": t.get("name", "?"),
                    "issue": f"Tool '{t.get('name')}' ({tier}) is blocked on a missing key: {t.get('requires_key', '?')}",
                    "kind": "tool-gap",
                }
    return None


def find_improvement_target():
    return _find_pyflakes_issue() or _find_tool_registry_gap()


# ─── Step 2: ask Builder (real, grounded, validated) to propose a fix ────────

def _read_snippet(rel_path, limit=3000):
    path = os.path.join(_REPO_ROOT, rel_path)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()[:limit]
    except Exception:
        return ""


def build_task(target):
    if target["kind"] == "pyflakes" and os.path.exists(os.path.join(_REPO_ROOT, target["module"])):
        snippet = _read_snippet(target["module"])
        return (
            f"Fix a confirmed real bug in {target['module']}, found by pyflakes: "
            f"{target['issue']}.\n\n"
            f"Current full content of {target['module']}:\n```python\n{snippet}\n```\n\n"
            "Return the complete corrected file content as a single Python code block. "
            "Make the minimal change needed to fix the reported issue — do not "
            "restructure unrelated code."
        )
    return (
        f"Propose a concrete, minimal Python tool or fix addressing this real gap: "
        f"{target['issue']}. This is data from VAPE's own tool registry "
        f"(skillforge/memory/tools-registry.json), not a hypothetical. "
        "Return a single, self-contained Python code block."
    )


# ─── Step 3: land the proposal as a new file, on a branch, behind a real PR ──

def _git_current_branch():
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def open_proposal_pr(target, code, metadata, warnings):
    if not os.getenv("GITHUB_TOKEN") or GitHubMCPWrapper is None:
        print("[SelfImprove] No GITHUB_TOKEN / MCP wrapper available — skipping PR, report-only.")
        return None

    original_branch = _git_current_branch()
    slug = re.sub(r"[^a-z0-9]+", "-", target["module"].lower()).strip("-")[:40]
    branch = f"vape-self-improve-{_now_stamp()}-{slug}"
    rel_out = os.path.join("agents", "proposals", f"{slug}-{_now_stamp()}.py")
    out_path = os.path.join(_REPO_ROOT, rel_out)

    header = (
        f'"""\nVAPE self-improvement proposal — generated {datetime.now(timezone.utc).isoformat()}\n'
        f"Target: {target['module']}\nIssue: {target['issue']}\n"
        f"Security review: {'clean' if not warnings else '; '.join(warnings)}\n\n"
        "This is a PROPOSAL, not applied automatically. A human reviews this PR\n"
        "and decides whether/how to merge it into the actual target file.\n\"\"\"\n\n"
    )

    try:
        os.makedirs(PROPOSALS_DIR, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(header + code + "\n")

        _run(["git", "config", "user.name", "VAPE Bot"])
        _run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
        _run(["git", "checkout", "-b", branch])
        _run(["git", "add", rel_out])
        commit = _run(["git", "commit", "-m", f"Self-improvement proposal: {target['module']}"])
        if commit.returncode != 0:
            print(f"[SelfImprove] Nothing to commit: {commit.stdout}{commit.stderr}")
            return None
        push = _run(["git", "push", "-u", "origin", branch])
        if push.returncode != 0:
            print(f"[SelfImprove] Push failed: {push.stderr}")
            return None

        gh = GitHubMCPWrapper()
        body = (
            f"**Target:** `{target['module']}`\n"
            f"**Real issue found:** {target['issue']}\n"
            f"**Security review:** {'clean' if not warnings else ', '.join(warnings)}\n\n"
            f"Generated by `agents/self_improve.py`. This is a proposal only — nothing "
            f"was applied to the target file automatically. Review the new file at "
            f"`{rel_out}` and merge it into the real location by hand if it's correct.\n"
        )
        success, pr_data = gh.create_pr(
            repo=REPO_SLUG,
            title=f"VAPE self-improvement: {target['module']}"[:100],
            body=body,
            head=branch,
        )
        if success:
            print(f"[SelfImprove] PR opened: {pr_data.get('url')}")
            return pr_data.get("url")
        print(f"[SelfImprove] PR creation failed: {pr_data}")
        return None
    finally:
        _run(["git", "checkout", original_branch])


# ─── Orchestration ────────────────────────────────────────────────────────────

def self_review_and_improve():
    target = find_improvement_target()
    os.makedirs(REPORTS_DIR, exist_ok=True)
    stamp = _now_stamp()
    report_path = os.path.join(REPORTS_DIR, f"self_improve_{stamp}.md")

    if not target:
        report = (
            f"# Self-Improvement Cycle — {datetime.now(timezone.utc).isoformat()}\n\n"
            "No concrete issue found this cycle (pyflakes clean, no tool-registry "
            "gaps). Nothing fabricated — skipping code generation and PR.\n"
        )
        with open(report_path, "w") as f:
            f.write(report)
        print("[SelfImprove] No real gap found this cycle — report-only, no PR.")
        return None

    builder = Builder()
    if not builder.llm_ready:
        report = (
            f"# Self-Improvement Cycle — {datetime.now(timezone.utc).isoformat()}\n\n"
            f"Real target found: `{target['module']}` — {target['issue']}\n\n"
            "No LLM provider available this cycle — logging the target for the next run "
            "instead of fabricating a fix.\n"
        )
        with open(report_path, "w") as f:
            f.write(report)
        print("[SelfImprove] Target found but no LLM available — report-only.")
        return None

    task = build_task(target)
    code, metadata = builder.generate_code(task=task, review=True, tier="deep")
    # generate_code() already ran this and rejected unsafe code (code == "" in
    # that case); re-running it here on the returned code is cheap, pure, and
    # gets us the advisory warnings for the report without touching Builder.
    _, warnings = validate_security(code, task) if code else (True, [])

    pr_url = None
    if code:
        pr_url = open_proposal_pr(target, code, metadata, warnings)

    report = (
        f"# Self-Improvement Cycle — {datetime.now(timezone.utc).isoformat()}\n\n"
        f"## Real target this cycle\n- Module: `{target['module']}`\n- Issue: {target['issue']}\n\n"
        f"## Builder proposal\n"
        + (f"PR opened: {pr_url}\n\n" if pr_url else "No PR opened (see log — likely no GITHUB_TOKEN in this environment, or nothing generated).\n\n")
        + (f"```python\n{code}\n```\n" if code else "Builder did not return a usable code block this cycle.\n")
    )
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[SelfImprove] Cycle complete. Report: {os.path.relpath(report_path, _REPO_ROOT)}")
    return pr_url


if __name__ == "__main__":
    self_review_and_improve()
