#!/usr/bin/env python3
"""
Mines VAPE's own bot-authored PR history into
data/finetune/pr_history_corpus.jsonl — the concrete answer to "VAPE needs
to be able to write code and build tools on its own repo": given a real task
VAPE set for itself (a gap it found, an issue it was asked to fix), what did
it actually generate, and was that judged good enough to ship?

Honest finding from checking this repo's real PR history before writing this
(never guessed): most of VAPE's own code-generation PRs
(agents/self_improve.py's "VAPE self-improvement: ..." and
agents/skillforge_build.py's "VAPE self-build: ...") are deliberately
PROPOSAL-ONLY by design — the generated code lands under agents/proposals/
or build-requests/, and a human must manually decide whether/how to fold it
into the real target file. As of this writing, only a handful of this
repo's bot-authored PRs are actually merged, and those are almost entirely
the separate "SKILLFORGE skills update" pipeline (memory-index refresh +
distilled markdown skill playbooks) — not hand-approved code proposals.

Given that, this script does NOT restrict to merged==true (that would yield
a near-empty corpus of doc/index updates, not code). Instead it pulls every
CLOSED bot PR matching VAPE's own title patterns and tags each row with the
REAL outcome ("merged" or "closed_unmerged") as metadata — the same
real-judged-outcome discipline as everywhere else in this project, just with
an honestly mixed distribution instead of an all-success one. This is closer
in spirit to build_finetune_dataset.py's "lesson" source (VAPE's own PR
review outcomes) than to the purely deterministic investigation/sweep
sources.

INPUT: the PR title + the real task/issue text from its body (self_improve.py
and skillforge_build.py both write a real "Target"/"Real issue found" or
"Justification" section, not a fabricated one).
OUTPUT: the diff of the actual generated code/skill file(s) in that PR —
never the accompanying housekeeping files (skillforge/memory/INDEX.md and
similar regenerated-every-run files), since those aren't "VAPE writing a
tool," they're bookkeeping.

Needs a GITHUB_TOKEN with read access to this repo (used both to
authenticate — 5000 req/hr instead of unauthenticated's 60 — and because
some of these PRs' bodies/diffs are only reliably fetched at volume with a
token). Will not run from a network-policy-restricted sandbox; only from a
normal GitHub Actions runner (GITHUB_TOKEN is ambient there) or a manually
exported token.

Usage:
  GITHUB_TOKEN=... python scripts/build_pr_history_dataset.py [--max-prs 100]
  # writes/updates data/finetune/pr_history_corpus.jsonl
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
OUT_PATH = os.path.join(_REPO_ROOT, "data", "finetune", "pr_history_corpus.jsonl")

REPO = "jUXTAPOSITION1/V.A.P.E"

# VAPE's own real bot-authored PR title patterns (see agents/self_improve.py,
# agents/skillforge_build.py). Anything else — human PRs, CodeRabbit, other
# bots — is not VAPE writing code for itself and is excluded.
TITLE_PREFIXES = (
    "VAPE self-improvement:",
    "VAPE self-build:",
    "SKILLFORGE skills update",
)

# Files that accompany almost every such PR but aren't "VAPE writing a tool"
# — regenerated housekeeping, not authored code. Excluded from OUTPUT.
_HOUSEKEEPING_SUFFIXES = (
    "skillforge/memory/INDEX.md",
    "BUILD_LEDGER.md",
)

_TASK_SYSTEM = (
    "You are VAPE, extending your own repository. Given a real task or gap "
    "you identified, write the code that addresses it."
)


def _api(path_or_url, token, timeout=30):
    url = path_or_url if path_or_url.startswith("http") else f"https://api.github.com{path_or_url}"
    headers = {"User-Agent": "VAPE-training-corpus/1.0", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _matches_title(title):
    return any((title or "").startswith(p) for p in TITLE_PREFIXES)


def _is_housekeeping(filename):
    return any(filename.endswith(suf) for suf in _HOUSEKEEPING_SUFFIXES)


def pr_to_row(pr, files):
    """One PR (from GET /repos/{repo}/pulls/{n}) + its file list (from
    GET .../files) -> one training row, or None if there's no real authored
    task text or no non-housekeeping file changed."""
    title = pr.get("title") or ""
    if not _matches_title(title):
        return None
    body = (pr.get("body") or "").strip()
    if not body:
        return None

    code_files = [f for f in files if not _is_housekeeping(f.get("filename", ""))]
    if not code_files:
        return None  # this PR only touched housekeeping — not a real code sample

    diff_parts = []
    for f in code_files:
        patch = f.get("patch")
        if patch:
            diff_parts.append(f"--- {f['filename']} ({f.get('status')}) ---\n{patch}")
    if not diff_parts:
        return None  # binary/too-large files with no textual patch — nothing to learn from

    outcome = "merged" if pr.get("merged_at") else "closed_unmerged"
    return {
        "messages": [
            {"role": "system", "content": _TASK_SYSTEM},
            {"role": "user", "content": f"Task (PR #{pr['number']} — {title}):\n{body}"},
            {"role": "assistant", "content": "\n\n".join(diff_parts)},
        ],
        "source": "pr_history", "source_id": f"{REPO}#{pr['number']}",
        "outcome": outcome,
    }


def fetch_pr_history(max_prs=100, token=None):
    token = token or os.getenv("GITHUB_TOKEN")
    rows = []
    page = 1
    while len(rows) < max_prs:
        try:
            prs = _api(f"/repos/{REPO}/pulls?state=closed&per_page=100&page={page}&sort=created&direction=desc", token)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            print(f"[build_pr_history_dataset] pulls list fetch failed (page {page}): {e}", file=sys.stderr)
            break
        if not prs:
            break
        for pr in prs:
            if not _matches_title(pr.get("title") or ""):
                continue
            try:
                files = _api(f"/repos/{REPO}/pulls/{pr['number']}/files?per_page=100", token)
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
                print(f"[build_pr_history_dataset] files fetch failed for #{pr['number']}: {e}", file=sys.stderr)
                continue
            row = pr_to_row(pr, files)
            if row:
                rows.append(row)
            if len(rows) >= max_prs:
                break
        page += 1
    return rows


def _load_cached():
    if not os.path.exists(OUT_PATH):
        return []
    rows = []
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def merge_rows(cached, fresh):
    by_key = {(r["source"], r["source_id"]): r for r in cached}
    for r in fresh:
        by_key[(r["source"], r["source_id"])] = r
    return sorted(by_key.values(), key=lambda r: (r["source"], r["source_id"]))


def _outcome_counts(rows):
    counts = {}
    for r in rows:
        counts[r.get("outcome", "unknown")] = counts.get(r.get("outcome", "unknown"), 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser(description="Mine VAPE's own bot-authored PR history into a training corpus.")
    ap.add_argument("--max-prs", type=int, default=100)
    ap.add_argument("--stats", action="store_true", help="print cached counts, fetch nothing")
    args = ap.parse_args()

    if args.stats:
        cached = _load_cached()
        print(f"cached: {len(cached)} example(s) — {_outcome_counts(cached)}")
        return

    cached = _load_cached()
    fresh = fetch_pr_history(max_prs=args.max_prs)
    merged = merge_rows(cached, fresh)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"fetched {len(fresh)} fresh, cache now {len(merged)} total — {_outcome_counts(merged)}")
    print(f"wrote {os.path.relpath(OUT_PATH, _REPO_ROOT)}")


if __name__ == "__main__":
    main()
