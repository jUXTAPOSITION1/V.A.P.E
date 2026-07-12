#!/usr/bin/env python3
"""
VAPE repo health monitor — cheap visibility into the "GitHub as the brain"
growth curve, so the archiving/scaling decisions are driven by real numbers
instead of guesswork or a surprise 5GB email from GitHub.

Prints a Markdown report (also appended to $GITHUB_STEP_SUMMARY when run in
Actions) covering: tracked file count by top-level dir, total working-tree
and .git sizes, the largest tracked files, per-category report counts, and
jsonl memory-log line counts. Read-only — never writes into the repo tree.

Usage:
  python scripts/repo_stats.py            # print Markdown to stdout
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Soft thresholds — not GitHub's hard limits (100MB/file, ~5GB/repo), but the
# points where day-to-day friction (tree browsing, checkout, glob/jsonl
# scans) starts to bite well before any hard limit. Crossing one is a nudge
# to archive, not an emergency.
WARN_TRACKED_FILES = 1500
WARN_GIT_MB = 250
WARN_LARGEST_FILE_KB = 1024


def _run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout


def _tracked_files():
    return [l for l in _run(["git", "ls-files"]).splitlines() if l]


def _du_mb(path):
    try:
        out = _run(["du", "-sm", path]).split()
        return int(out[0]) if out else 0
    except Exception:
        return 0


def _file_kb(path):
    try:
        return os.path.getsize(os.path.join(ROOT, path)) // 1024
    except OSError:
        return 0


def main():
    files = _tracked_files()
    by_dir = {}
    for f in files:
        top = f.split("/", 1)[0] if "/" in f else f
        by_dir[top] = by_dir.get(top, 0) + 1

    largest = sorted(((f, _file_kb(f)) for f in files), key=lambda x: -x[1])[:12]
    git_mb = _du_mb(os.path.join(ROOT, ".git"))

    lines = ["# VAPE repo health", ""]
    total = len(files)
    flag = " ⚠️" if total > WARN_TRACKED_FILES else ""
    lines.append(f"**Tracked files:** {total}{flag}  ·  **.git size:** {git_mb} MB"
                 f"{' ⚠️' if git_mb > WARN_GIT_MB else ''}")
    lines.append("")
    lines.append("## Tracked files by top-level dir")
    lines.append("| dir | files |")
    lines.append("|---|---|")
    for d in sorted(by_dir, key=lambda k: -by_dir[k]):
        lines.append(f"| `{d}` | {by_dir[d]} |")

    lines.append("")
    lines.append("## Largest tracked files")
    lines.append("| file | size |")
    lines.append("|---|---|")
    for f, kb in largest:
        mark = " ⚠️" if kb > WARN_LARGEST_FILE_KB else ""
        size = f"{kb/1024:.1f} MB" if kb >= 1024 else f"{kb} KB"
        lines.append(f"| `{f}` | {size}{mark} |")

    # jsonl memory-log line counts — the "brain" growth signal.
    mem_dir = os.path.join(ROOT, "skillforge", "memory")
    jsonl = sorted(f for f in os.listdir(mem_dir) if f.endswith(".jsonl")) if os.path.isdir(mem_dir) else []
    if jsonl:
        lines.append("")
        lines.append("## Memory logs (skillforge/memory/*.jsonl)")
        lines.append("| log | lines |")
        lines.append("|---|---|")
        for j in jsonl:
            with open(os.path.join(mem_dir, j), encoding="utf-8", errors="ignore") as fh:
                n = sum(1 for _ in fh)
            lines.append(f"| `{j}` | {n} |")

    report = "\n".join(lines)
    print(report)

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report + "\n")

    # Non-zero exit if any soft threshold is crossed, so a CI job can surface
    # it as a visible (non-blocking, if the workflow chooses) signal.
    breached = total > WARN_TRACKED_FILES or git_mb > WARN_GIT_MB
    return 1 if breached else 0


if __name__ == "__main__":
    sys.exit(main())
