"""
Shared git/PR plumbing for VAPE's build pipelines (agents/build_request.py,
agents/skillforge_build.py) — both land LLM-generated files in an isolated
build-requests/<dir>/ directory via a PR, never applied directly to existing
production files. Extracted here so the human-issue-driven pipeline and
VAPE's own self-directed proposal pipeline share one exact, tested landing
mechanism instead of two subtly-different copies.
"""
import os
import shutil
import subprocess
import py_compile

try:
    from skillforge.mcp import GitHubMCPWrapper
except Exception:
    GitHubMCPWrapper = None

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_SLUG = "jUXTAPOSITION1/V.A.P.E"


def _run(cmd, **kwargs):
    return subprocess.run(cmd, cwd=_REPO_ROOT, capture_output=True, text=True, **kwargs)


def git_current_branch():
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def verify_files(out_dir, files):
    """Actually verify generated files parse/compile — not just Builder's
    security-pattern-matching of the raw text. Returns [(rel_path, ok, detail), ...]
    where ok is True/False/None (None = no verifier available for this file type,
    or the checking tool itself wasn't installed — never silently swallowed)."""
    results = []
    for rel_path in files:
        full_path = os.path.join(out_dir, rel_path)
        if rel_path.endswith(".py"):
            try:
                py_compile.compile(full_path, doraise=True)
                results.append((rel_path, True, "py_compile OK"))
            except py_compile.PyCompileError as e:
                results.append((rel_path, False, str(e.exc_value)[:200]))
            except Exception as e:
                results.append((rel_path, False, str(e)[:200]))
        elif rel_path.endswith((".js", ".mjs", ".cjs")):
            try:
                p = subprocess.run(["node", "--check", full_path], capture_output=True, text=True, timeout=30)
                results.append((rel_path, p.returncode == 0, (p.stderr or "node --check OK").strip()[:300]))
            except Exception as e:
                results.append((rel_path, None, f"node --check failed to run: {e}"))
        elif rel_path.endswith((".ts", ".tsx")):
            # Best-effort only: a lone generated file has no project context (tsconfig,
            # node_modules), so this can only catch gross syntax errors via a bare tsc
            # parse, not real type errors against the rest of the codebase. Skip (ok=None)
            # rather than fail the whole verification pass when tsc isn't installed.
            tsc = shutil.which("tsc")
            cmd = [tsc, "--noEmit", "--skipLibCheck", "--allowJs", full_path] if tsc else \
                  (["npx", "--no-install", "tsc", "--noEmit", "--skipLibCheck", "--allowJs", full_path]
                   if shutil.which("npx") else None)
            if not cmd:
                results.append((rel_path, None, "tsc not available in this environment — skipped"))
                continue
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                results.append((rel_path, p.returncode == 0, (p.stdout or p.stderr or "tsc OK").strip()[:300]))
            except Exception as e:
                results.append((rel_path, None, f"tsc check failed to run: {e}"))
        else:
            results.append((rel_path, None, "no verifier for this file type — not checked"))
    return results


def _format_verification(results):
    lines = ["## Generated-file verification (real compile/syntax check, not just pattern-matching)", ""]
    for rel_path, ok, detail in results:
        icon = "✅" if ok is True else ("⚠️" if ok is None else "❌")
        lines.append(f"- {icon} `{rel_path}` — {detail}")
    return "\n".join(lines)


def open_build_pr(branch, out_dir_rel, pr_title, pr_body, readme, files):
    """Write `files` (rel_path -> content) + a README into out_dir_rel on a
    fresh branch, commit, push, and open a PR back to main.

    Returns the PR URL, or None if anything short of a code bug prevented it
    (missing token, nothing to commit, push race) — callers treat None as
    "report-only this cycle," never as fatal.
    """
    if not os.getenv("GITHUB_TOKEN") or GitHubMCPWrapper is None:
        print("[BuildPR] No GITHUB_TOKEN / MCP wrapper available — skipping PR, report-only.")
        return None

    original_branch = git_current_branch()
    out_dir = os.path.join(_REPO_ROOT, out_dir_rel)
    try:
        os.makedirs(out_dir, exist_ok=True)
        for rel_path, content in files.items():
            full_path = os.path.join(out_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # Real verification, not just Builder's security-pattern-matching of the raw
        # text — actually try to compile/parse every generated file and say so plainly
        # in both the README and the PR body, so a reviewer sees pass/fail at a glance.
        verification = verify_files(out_dir, files)
        verify_block = _format_verification(verification)
        print(f"[BuildPR] verification: {verify_block}")

        with open(os.path.join(out_dir, "README.md"), "w") as f:
            f.write(readme + "\n\n" + verify_block + "\n")

        _run(["git", "config", "user.name", "VAPE Bot"])
        _run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"])
        _run(["git", "checkout", "-b", branch])
        _run(["git", "add", out_dir_rel])
        commit = _run(["git", "commit", "-m", pr_title])
        if commit.returncode != 0:
            print(f"[BuildPR] Nothing to commit: {commit.stdout}{commit.stderr}")
            return None
        push = _run(["git", "push", "-u", "origin", branch])
        if push.returncode != 0:
            print(f"[BuildPR] Push failed: {push.stderr}")
            return None

        gh = GitHubMCPWrapper()
        success, pr_data = gh.create_pr(repo=REPO_SLUG, title=pr_title[:100],
                                         body=pr_body + "\n\n" + verify_block, head=branch)
        if success:
            print(f"[BuildPR] PR opened: {pr_data.get('url')}")
            return pr_data.get("url")
        print(f"[BuildPR] PR creation failed: {pr_data}")
        return None
    finally:
        _run(["git", "checkout", original_branch])
