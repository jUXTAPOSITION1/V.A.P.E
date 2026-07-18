"""Tests for scripts/build_pr_history_dataset.py's transform/merge logic.
Hermetic — no live network call. Fixtures mirror the REAL shape of this
repo's own bot-authored PRs and their file diffs, captured via the GitHub
API during development (PR #185/#188/#154 on jUXTAPOSITION1/V.A.P.E), not
invented ones."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "build_pr_history_dataset", os.path.join(ROOT, "scripts", "build_pr_history_dataset.py"))
bph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bph)


def test_matches_title_accepts_all_three_real_prefixes():
    assert bph._matches_title("VAPE self-improvement: agents/run.py")
    assert bph._matches_title("VAPE self-build: hack_feed_replacement.py")
    assert bph._matches_title("SKILLFORGE skills update 2026-07-17")


def test_matches_title_rejects_unrelated_pr():
    assert not bph._matches_title("Fix typo in README")
    assert not bph._matches_title("")
    assert not bph._matches_title(None)


def test_is_housekeeping_matches_index_and_ledger():
    assert bph._is_housekeeping("skillforge/memory/INDEX.md")
    assert bph._is_housekeeping("skillforge/memory/BUILD_LEDGER.md")
    assert not bph._is_housekeeping("agents/hack_feed.py")


# Real (trimmed) shape of GET /repos/{repo}/pulls/{n} for the actual PR #188
# on jUXTAPOSITION1/V.A.P.E ("VAPE self-build: hack_feed_replacement.py").
_PR_UNMERGED = {
    "number": 188,
    "title": "VAPE self-build: hack_feed_replacement.py (DeFiLlama /hacks fetcher + normalizer)",
    "body": "**VAPE proposed this build itself** — grounded in real signals, not a human request.\n\n"
            "**Justification:** The only concrete gap signal is real...",
    "merged_at": None,
}

# Real shape for the actual merged PR #185 ("SKILLFORGE skills update").
_PR_MERGED = {
    "number": 185,
    "title": "SKILLFORGE skills update 2026-07-17",
    "body": "Auto-distilled from real findings/lessons by skillforge-synthesize. Review before merge.",
    "merged_at": "2026-07-18T01:16:23Z",
}

_FILES_WITH_CODE = [
    {"filename": "skillforge/memory/INDEX.md", "status": "modified", "patch": "@@ housekeeping diff @@"},
    {"filename": "skillforge/skills/skills-ledger-drift-review-md.md", "status": "added",
     "patch": "@@ -0,0 +1,3 @@\n+# Ledger Drift Review\n+Step 1...\n+Step 2..."},
]

_FILES_HOUSEKEEPING_ONLY = [
    {"filename": "skillforge/memory/INDEX.md", "status": "modified", "patch": "@@ housekeeping diff @@"},
]


def test_pr_to_row_builds_real_pair_and_tags_outcome():
    row = bph.pr_to_row(_PR_MERGED, _FILES_WITH_CODE)
    assert row["source"] == "pr_history"
    assert row["source_id"] == f"{bph.REPO}#185"
    assert row["outcome"] == "merged"
    assert "Ledger Drift Review" in row["messages"][2]["content"]
    assert "INDEX.md" not in row["messages"][2]["content"]  # housekeeping excluded


def test_pr_to_row_tags_closed_unmerged_when_no_merged_at():
    row = bph.pr_to_row(_PR_UNMERGED, [
        {"filename": "agents/hack_feed.py", "status": "added", "patch": "@@ -0,0 +1,2 @@\n+import json\n+..."},
    ])
    assert row["outcome"] == "closed_unmerged"


def test_pr_to_row_none_for_unmatched_title():
    row = bph.pr_to_row({"number": 1, "title": "Fix typo", "body": "x", "merged_at": None}, _FILES_WITH_CODE)
    assert row is None


def test_pr_to_row_none_for_empty_body():
    pr = dict(_PR_MERGED, body="")
    assert bph.pr_to_row(pr, _FILES_WITH_CODE) is None


def test_pr_to_row_none_when_only_housekeeping_files_changed():
    assert bph.pr_to_row(_PR_MERGED, _FILES_HOUSEKEEPING_ONLY) is None


def test_pr_to_row_none_when_no_files_have_a_patch():
    binary_only = [{"filename": "agents/logo.png", "status": "added"}]  # no "patch" key
    assert bph.pr_to_row(_PR_MERGED, binary_only) is None


def test_merge_rows_fresh_wins_on_collision_else_union():
    cached = [{"source": "pr_history", "source_id": "r#1", "outcome": "closed_unmerged"}]
    fresh = [{"source": "pr_history", "source_id": "r#1", "outcome": "merged"},
             {"source": "pr_history", "source_id": "r#2", "outcome": "merged"}]
    merged = bph.merge_rows(cached, fresh)
    by_id = {r["source_id"]: r for r in merged}
    assert len(merged) == 2
    assert by_id["r#1"]["outcome"] == "merged"


def test_outcome_counts():
    rows = [{"outcome": "merged"}, {"outcome": "merged"}, {"outcome": "closed_unmerged"}]
    assert bph._outcome_counts(rows) == {"merged": 2, "closed_unmerged": 1}
