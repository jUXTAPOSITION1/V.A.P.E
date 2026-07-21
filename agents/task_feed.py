#!/usr/bin/env python3
"""
Live "tasks" feed for the site's Bounty Command Center.

Real gap this closes: the Command Center has never had a live-task feed —
"tasks" doesn't exist as a stat anywhere in the codebase prior to this. Every
entry here is a REAL commit VAPE's own scheduled automation made to this
repo's main branch (committed as "VAPE Bot" / github-actions[bot] — see any
of the *.yml workflows' `git config user.name "VAPE Bot"` step), each one a
genuine, verifiable unit of automated work: an investigation logged, an
audit filed, a broadcast published, a sweep run, DATA AGENT/SCOUT cycling,
etc. Never fabricated, never a simulated "systems status" widget.

Writes: data/task-feed.json (committed; dashboard fetches it raw from GitHub)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.data_fetchers import _get

REPO = "jUXTAPOSITION1/V.A.P.E"
OUT = os.path.join(ROOT, "data", "task-feed.json")
COMMITS_API = f"https://api.github.com/repos/{REPO}/commits"
FETCH_LIMIT = 30
KEEP_LIMIT = 15

# Cosmetic classification of a real commit message's first line into a task
# category — never invents content, just labels what's already there. Order
# matters: more specific patterns (audit/broadcast) are checked before the
# generic sweep/automation catch-alls.
_KIND_PATTERNS = [
    (re.compile(r"^Featured investigation", re.I), "investigation"),
    (re.compile(r"^SCOUT bounty radar", re.I), "bounty-radar"),
    (re.compile(r"audit|deep.dive", re.I), "audit"),
    (re.compile(r"broadcast", re.I), "broadcast"),
    (re.compile(r"reputation", re.I), "reputation"),
    (re.compile(r"sweep", re.I), "sweep"),
    (re.compile(r"data.agent|catalog sweep", re.I), "data-agent"),
    (re.compile(r"^Merge pull request", re.I), "build"),
]


def _classify(message):
    first_line = (message or "").split("\n")[0].strip()
    for pattern, kind in _KIND_PATTERNS:
        if pattern.search(first_line):
            return kind, first_line
    return "automation", first_line


def _recent_bot_commits():
    """Real commits authored by VAPE's own scheduled workflows — filters to
    the exact bot identity every workflow's `git config` step sets, so a
    human commit (like this session's own PR merges) or a Dependabot bump
    never gets mistaken for automated "task" activity."""
    data = _get(f"{COMMITS_API}?per_page={FETCH_LIMIT}", ttl=180, cache_key="task_feed_commits")
    if not isinstance(data, list):
        return []
    tasks = []
    for c in data:
        if not isinstance(c, dict):
            continue
        commit = c.get("commit") or {}
        author = commit.get("author") or {}
        committer_login = (c.get("committer") or {}).get("login")
        if author.get("name") != "VAPE Bot" and committer_login != "github-actions[bot]":
            continue
        kind, first_line = _classify(commit.get("message"))
        tasks.append({
            "sha": (c.get("sha") or "")[:10],
            "kind": kind,
            "message": first_line,
            "date": author.get("date"),
            "url": c.get("html_url"),
        })
        if len(tasks) >= KEEP_LIMIT:
            break
    return tasks


def _synthesis(tasks):
    """One real, grounded line via OCI Grok (agents/intel_common.py::
    grok_analysis(), OCI Grok primary — see that function's own docstring for
    the fallback chain) describing what VAPE's automation has actually been
    doing, strictly from the real commit messages above. Degrades to an
    honest static line if the LLM layer is unavailable or there's nothing to
    summarize, exactly like every other grok_analysis() call site in this
    repo — never invents an event that isn't in the list."""
    if not tasks:
        return "No automated activity recorded in the last 30 commits."
    try:
        from agents.intel_common import grok_analysis
    except Exception:
        return "Automated activity log below — narrative synthesis unavailable this cycle."
    grounding = "\n".join(f"- [{t['kind']}] {t['message']} ({t['date']})" for t in tasks)
    return grok_analysis(
        role="operations analyst",
        grounding=f"VAPE's {len(tasks)} most recent automated commits to its own repository:\n{grounding}",
        instructions=(
            "In exactly one sentence (max ~25 words), describe what VAPE's automation "
            "has actually been doing this cycle, grounded only in the list above. No "
            "preamble, no markdown formatting, just the sentence."
        ),
        max_tokens=120,
        temperature=0.4,
        search=False,
    )


def main():
    tasks = _recent_bot_commits()
    out = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synthesis": _synthesis(tasks),
        "tasks": tasks,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps({"wrote": OUT, "tasks": len(tasks)}))


if __name__ == "__main__":
    main()
