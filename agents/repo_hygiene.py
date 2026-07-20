"""VAPE repo-hygiene memory — the same "teach VAPE and make it stick" pattern
agents/code_review.py already uses for false-positive findings, generalized
to the other class of judgment call a human makes constantly on this repo:
triaging PRs and issues (merge vs. close, is a major-version bump actually
safe, is a CI check worth keeping).

Without this, every one of those judgment calls lives only in a PR comment
or a chat reply — gone the moment the conversation scrolls past. This module
gives them one place to land (skillforge/memory/retriever.py's existing
"lesson" category, same storage every other lesson in this repo already
uses) and one place to be looked up again, so the next PR/issue triage
(human or automated) starts from precedent instead of re-deriving it.

Deliberately thin: no new storage, no new file format, no automatic
triage decisions. record_hygiene_lesson() is called AFTER a human (or an
automated check with a clear, stated rule) has already made the call —
this only makes that call persistent. search_hygiene_lessons() is the
read side for whatever calls it next."""
try:
    from skillforge.memory.retriever import append_to_memory, search_memory
except Exception:
    append_to_memory = None
    search_memory = None

HYGIENE_TAG = "repo-hygiene"


def record_hygiene_lesson(title, content, tags=None, source="human-review"):
    """Record one repo-hygiene decision (a PR merged/closed, a check removed,
    a dependency bump reviewed) as a lesson. Returns True on success, False
    if Memory is unavailable or the write failed — never raises."""
    if not append_to_memory:
        return False
    entry = append_to_memory(
        category="lesson",
        title=title,
        content=content,
        source=source,
        tags=[HYGIENE_TAG] + (tags or []),
        confidence=0.85,
    )
    return bool(entry)


def search_hygiene_lessons(query, max_results=10):
    """Prior repo-hygiene lessons matching `query` (e.g. a check name, a
    package name, a PR pattern) — for a future triage pass to ground its
    decision in precedent instead of re-deriving it from scratch. Returns
    [] if Memory is unavailable, never raises."""
    if not search_memory:
        return []
    try:
        return search_memory(query, category="lesson", tags=[HYGIENE_TAG], max_results=max_results)
    except Exception:
        return []
