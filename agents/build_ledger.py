#!/usr/bin/env python3
"""
VAPE Build Ledger — the "how VAPE learns to build" log.

Where findings.jsonl records WHAT VAPE found and lessons.jsonl records
WHETHER a build attempt succeeded, this records HOW: a growing,
instructional trail of the actual patterns, gotchas, and reusable
techniques behind real changes to this repo — detailed enough that a
future build (by VAPE, or by a human) can follow the reasoning without
re-deriving it from scratch. This is the living tree the site's
Development Ledger section (docs/index.html#the-workshop) points to as
its coding-tools counterpart.

Storage: skillforge/memory/build_log.jsonl, through the same shared,
append-only Memory system (skillforge/memory/retriever.py) every other
VAPE subsystem already reads and writes. Retrieve past entries the same
way any other memory category is retrieved:

    from skillforge.memory.retriever import search_memory
    search_memory("icon resolver", category="build_log")

CLI:
  python -m agents.build_ledger --title "..." --content "..." \
      --source "agents/foo.py" --tags pattern,css --files docs/index.html
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from skillforge.memory.retriever import append_to_memory


def log_build(title, content, source="manual", tags=None, files=None, confidence=0.9):
    """Append one instructional build-log entry. `content` should explain
    the *how and why* — the reasoning and the reusable pattern — not just
    restate the diff; the code itself is already in git history."""
    return append_to_memory(
        category="build_log",
        title=title,
        content=content,
        source=source,
        tags=list(tags or []),
        confidence=confidence,
        metadata={"files": files or []},
    )


def main():
    ap = argparse.ArgumentParser(description="Append an instructional entry to VAPE's build ledger")
    ap.add_argument("--title", required=True)
    ap.add_argument("--content", required=True)
    ap.add_argument("--source", default="manual")
    ap.add_argument("--tags", default="", help="comma-separated")
    ap.add_argument("--files", default="", help="comma-separated repo-relative paths touched")
    args = ap.parse_args()
    entry = log_build(
        args.title, args.content, source=args.source,
        tags=[t.strip() for t in args.tags.split(",") if t.strip()],
        files=[f.strip() for f in args.files.split(",") if f.strip()],
    )
    print(f"Logged build_log entry {entry.get('id', '?')}: {entry.get('title', '?')}")


if __name__ == "__main__":
    main()
