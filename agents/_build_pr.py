"""
Shared git/PR plumbing for VAPE's build pipelines (agents/build_request.py,
agents/skillforge_build.py) — both land LLM-generated files in an isolated
build-requests/<dir>/ directory via a PR, never applied directly to existing
production files. Extracted here so the human-issue-driven pipeline and
VAPE's own self-directed proposal pipeline share one exact, tested landing
mechanism instead of two subtly-different copies.
"""
import os
import subprocess

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
        with open(os.path.join(out_dir, "README.md"), "w") as f:
            f.write(readme)

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
        success, pr_data = gh.create_pr(repo=REPO_SLUG, title=pr_title[:100], body=pr_body, head=branch)
        if success:
            print(f"[BuildPR] PR opened: {pr_data.get('url')}")
            return pr_data.get("url")
        print(f"[BuildPR] PR creation failed: {pr_data}")
        return None
    finally:
        _run(["git", "checkout", original_branch])
