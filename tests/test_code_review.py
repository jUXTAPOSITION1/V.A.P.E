"""Tests for agents/code_review.py — VAPE Reviewer's orchestration logic.
Live GitHub API and every LLM provider are unreachable from CI's/dev's
sandbox (same as every external call in this repo), so these tests
monkeypatch `_gh()` (the GitHubMCPWrapper factory) and `ask_safe` (the LLM
call) to assert the plumbing — diff/file fetching, the deterministic pass,
prompt construction, comment formatting, and honest degradation on
failure — is correct without ever touching the network.
"""
import json

import agents.code_review as cr


class _FakeGitHub:
    def __init__(self, head_ok=True, head_sha="abc123", files_ok=True, files=None,
                 comment_ok=True, comment_err=None, existing_comments=None,
                 list_comments_ok=True):
        self.head_ok = head_ok
        self.head_sha = head_sha
        self.files_ok = files_ok
        self.files = files if files is not None else []
        self.comment_ok = comment_ok
        self.comment_err = comment_err
        self.posted = []
        self.updated = []
        self._file_contents = {}
        self.existing_comments = existing_comments if existing_comments is not None else []
        self.list_comments_ok = list_comments_ok

    def get_pr_head_sha(self, repo, pr_number):
        return self.head_ok, self.head_sha

    def get_pr_files(self, repo, pr_number):
        return self.files_ok, self.files

    def read_file(self, repo, path, ref="main"):
        if path in self._file_contents:
            return True, self._file_contents[path]
        return False, ""

    def create_pr_comment(self, repo, pr_number, body):
        self.posted.append(body)
        if self.comment_ok:
            return True, {"url": "https://example/comment", "status": "created"}
        return False, {"error": self.comment_err or "failed"}

    def list_issue_comments(self, repo, pr_number):
        return self.list_comments_ok, self.existing_comments

    def update_issue_comment(self, repo, comment_id, body):
        self.updated.append((comment_id, body))
        if self.comment_ok:
            return True, {"url": "https://example/comment", "status": "updated"}
        return False, {"error": self.comment_err or "failed"}


def test_fetch_pr_head_and_files_success(monkeypatch):
    fake = _FakeGitHub(files=[{"path": "agents/foo.py", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b\n"}])
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    head, files, err = cr.fetch_pr_head_and_files(1)
    assert err is None
    assert head == "abc123"
    assert files[0]["path"] == "agents/foo.py"


def test_fetch_pr_head_and_files_both_fail(monkeypatch):
    fake = _FakeGitHub(head_ok=False, files_ok=False)
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    head, files, err = cr.fetch_pr_head_and_files(1)
    assert head is None
    assert files == []
    assert err is not None


def test_fetch_pr_head_and_files_partial_failure_still_returns_data(monkeypatch):
    # head lookup fails but files succeed — real diff/lint work can still
    # partially proceed rather than treating any single failure as total.
    fake = _FakeGitHub(head_ok=False, files_ok=True, files=[{"path": "x.py", "status": "modified", "patch": "p"}])
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    head, files, err = cr.fetch_pr_head_and_files(1)
    assert err is None
    assert head is None
    assert len(files) == 1


def test_build_diff_text_includes_patches():
    files = [
        {"path": "agents/foo.py", "status": "modified", "patch": "@@ -1 +1 @@\n-a\n+b\n"},
        {"path": "docs/x.js", "status": "added", "patch": "+new line"},
    ]
    diff = cr.build_diff_text(files)
    assert "agents/foo.py" in diff
    assert "docs/x.js" in diff
    assert "+b" in diff
    assert "[modified]" in diff and "[added]" in diff


def test_build_diff_text_handles_missing_patch():
    files = [{"path": "assets/logo.png", "status": "added", "patch": None}]
    diff = cr.build_diff_text(files)
    assert "binary or too large" in diff


def test_fetch_file_at_ref_success(monkeypatch):
    fake = _FakeGitHub()
    fake._file_contents["agents/foo.py"] = "print('hi')\n"
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    assert cr.fetch_file_at_ref("agents/foo.py", "abc123") == "print('hi')\n"


def test_fetch_file_at_ref_returns_none_on_failure(monkeypatch):
    monkeypatch.setattr(cr, "_gh", lambda: _FakeGitHub())
    assert cr.fetch_file_at_ref("agents/gone.py", "abc123") is None


def test_run_deterministic_pass_surfaces_lint_findings(monkeypatch):
    monkeypatch.setattr(cr, "fetch_file_at_ref", lambda path, ref: "eval(user_input)\n")
    files = [{"path": "agents/bad.py", "status": "modified"}, {"path": "docs/x.md", "status": "modified"}]
    findings = cr.run_deterministic_pass("abc123", files)
    # docs/x.md isn't a SOURCE_EXTS extension, so only bad.py is checked
    assert len(findings) == 1
    assert "eval" in findings[0][3]


def test_run_deterministic_pass_skips_removed_files(monkeypatch):
    calls = []
    monkeypatch.setattr(cr, "fetch_file_at_ref", lambda path, ref: calls.append(path))
    files = [{"path": "agents/deleted.py", "status": "removed"}]
    findings = cr.run_deterministic_pass("abc123", files)
    assert findings == []
    assert calls == []  # never even tried to fetch a removed file


def test_run_deterministic_pass_skips_unfetchable_files(monkeypatch):
    monkeypatch.setattr(cr, "fetch_file_at_ref", lambda path, ref: None)
    findings = cr.run_deterministic_pass("abc123", [{"path": "agents/x.py", "status": "modified"}])
    assert findings == []


def test_run_deterministic_pass_no_head_sha_returns_empty():
    findings = cr.run_deterministic_pass(None, [{"path": "agents/x.py", "status": "modified"}])
    assert findings == []


# ============================================================================
# Learned exceptions — "teach VAPE" mechanism (Memory-backed, guarded import)
# ============================================================================

def test_rule_tag_for_message_maps_known_patterns():
    assert cr._rule_tag_for_message("innerHTML assigned directly from 'msg' — pass it through...") \
        == "innerhtml-bare-var"
    assert cr._rule_tag_for_message("'API_SECRET' assigned a literal string that looks like a real secret") \
        == "hardcoded-secret-literal"
    assert cr._rule_tag_for_message("eval() called on a dynamically-built string") == "eval-exec-dynamic"
    assert cr._rule_tag_for_message("something totally unrelated") == "other"


def test_record_reviewed_exception_calls_append_to_memory(monkeypatch):
    captured = {}

    def fake_append(**kw):
        captured.update(kw)
        return {"id": "abc123"}

    monkeypatch.setattr(cr, "append_to_memory", fake_append)
    ok = cr.record_reviewed_exception(
        "docs/assets/hire.js",
        "innerHTML assigned directly from 'msg' — pass it through...",
        "escaped via escapeHtml() at every real call site",
    )
    assert ok is True
    assert captured["category"] == "lesson"
    assert cr.REVIEWED_EXCEPTION_TAG in captured["tags"]
    assert "innerhtml-bare-var" in captured["tags"]
    assert captured["metadata"]["path"] == "docs/assets/hire.js"


def test_record_reviewed_exception_false_when_memory_unavailable(monkeypatch):
    monkeypatch.setattr(cr, "append_to_memory", None)
    ok = cr.record_reviewed_exception("x.js", "innerHTML assigned directly from 'y'", "note")
    assert ok is False


def test_find_reviewed_exception_matches_path_and_rule(monkeypatch):
    monkeypatch.setattr(cr, "search_memory", lambda *a, **kw: [
        {"content": "escaped upstream", "metadata": {"path": "docs/assets/hire.js", "rule_tag": "innerhtml-bare-var"}},
    ])
    note = cr._find_reviewed_exception("docs/assets/hire.js", "innerHTML assigned directly from 'msg'")
    assert note == "escaped upstream"


def test_find_reviewed_exception_none_when_path_differs(monkeypatch):
    monkeypatch.setattr(cr, "search_memory", lambda *a, **kw: [
        {"content": "escaped upstream", "metadata": {"path": "docs/assets/other.js", "rule_tag": "innerhtml-bare-var"}},
    ])
    note = cr._find_reviewed_exception("docs/assets/hire.js", "innerHTML assigned directly from 'msg'")
    assert note is None


def test_find_reviewed_exception_none_when_memory_unavailable(monkeypatch):
    monkeypatch.setattr(cr, "search_memory", None)
    assert cr._find_reviewed_exception("docs/assets/hire.js", "innerHTML assigned directly from 'msg'") is None


def test_annotate_reviewed_exceptions_appends_note_on_match(monkeypatch):
    monkeypatch.setattr(cr, "_find_reviewed_exception", lambda path, msg: "escaped upstream")
    findings = [("MEDIUM", "docs/assets/hire.js", 193, "innerHTML assigned directly from 'msg'")]
    annotated = cr.annotate_reviewed_exceptions(findings)
    assert "Previously reviewed" in annotated[0][3]
    assert "escaped upstream" in annotated[0][3]
    assert annotated[0][0] == "MEDIUM"  # severity untouched — annotation only, never suppressed


def test_annotate_reviewed_exceptions_leaves_unmatched_findings_unchanged(monkeypatch):
    monkeypatch.setattr(cr, "_find_reviewed_exception", lambda path, msg: None)
    findings = [("HIGH", "agents/bad.py", 3, "eval() called on a dynamically-built string")]
    annotated = cr.annotate_reviewed_exceptions(findings)
    assert annotated == findings


def test_build_review_prompt_includes_findings_and_diff():
    findings = [("HIGH", "x.py", 3, "eval() called on a dynamic string")]
    system, prompt = cr.build_review_prompt("diff --git a/x b/x\n+eval(x)\n", findings)
    assert "eval() called on a dynamic string" in prompt
    assert "eval(x)" in prompt
    assert "## Security" in prompt
    assert "Django" in system  # real-stack grounding, not a generic project


def test_build_review_prompt_asks_for_summary_and_changes_sections():
    # CodeRabbit-style walkthrough parity: a plain-language summary and a
    # per-file changes list, ahead of the security-forward sections that
    # actually distinguish this reviewer.
    _, prompt = cr.build_review_prompt("diff --git a/x b/x\n+eval(x)\n", [])
    assert "## Summary" in prompt
    assert "## Changes" in prompt
    assert prompt.index("## Summary") < prompt.index("## Security")


def test_build_review_prompt_truncates_huge_diffs():
    huge_diff = "x" * (cr.MAX_DIFF_CHARS + 5000)
    _, prompt = cr.build_review_prompt(huge_diff, [])
    assert "truncated" in prompt
    assert len(prompt) < len(huge_diff) + 2000


def test_review_pr_diff_calls_ask_safe(monkeypatch):
    captured = {}

    def fake_ask_safe(system, user, **kw):
        captured["system"] = system
        captured["user"] = user
        return ("## Security\nNothing found.\n", "groq")

    monkeypatch.setattr(cr, "ask_safe", fake_ask_safe)
    text, provider = cr.review_pr_diff("diff --git a/x b/x\n", [])
    assert provider == "groq"
    assert "Nothing found" in text
    assert captured["user"]  # a real prompt was built and passed through


def test_build_comment_body_formats_sections():
    body = cr.build_comment_body(
        [("HIGH", "x.py", 3, "eval() called on a dynamic string")],
        "## Security\nNothing found.\n", "groq",
    )
    assert "VAPE Reviewer" in body
    assert "Advisory only" in body
    assert "1 finding" in body
    assert "x.py:3" in body
    assert "via groq" in body


def test_build_comment_body_notes_llm_unavailable():
    body = cr.build_comment_body([], "[llm unavailable: no key]", None)
    assert "unavailable this run" in body


def test_post_review_comment_creates_when_no_existing_comment(monkeypatch):
    fake = _FakeGitHub()
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    ok, err = cr.post_review_comment(42, "hello world")
    assert ok is True
    assert len(fake.posted) == 1
    assert cr.COMMENT_MARKER in fake.posted[0]
    assert "hello world" in fake.posted[0]
    assert fake.updated == []


def test_post_review_comment_updates_existing_comment_in_place(monkeypatch):
    # Mirrors CodeRabbit's own observed behavior on this repo: one comment
    # per PR, edited across pushes — not a new comment every run.
    fake = _FakeGitHub(existing_comments=[
        {"id": 999, "body": f"{cr.COMMENT_MARKER}\nold review"},
    ])
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    ok, err = cr.post_review_comment(42, "new review")
    assert ok is True
    assert fake.posted == []
    assert len(fake.updated) == 1
    comment_id, body = fake.updated[0]
    assert comment_id == 999
    assert "new review" in body


def test_find_existing_comment_id_ignores_other_bots_comments(monkeypatch):
    fake = _FakeGitHub(existing_comments=[
        {"id": 1, "body": "some CodeRabbit comment"},
        {"id": 2, "body": f"{cr.COMMENT_MARKER}\nours"},
    ])
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    assert cr.find_existing_comment_id(42) == 2


def test_find_existing_comment_id_returns_none_on_failure(monkeypatch):
    fake = _FakeGitHub(list_comments_ok=False)
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    assert cr.find_existing_comment_id(42) is None


def test_run_degrades_honestly_when_head_and_files_both_fail(monkeypatch):
    fake = _FakeGitHub(head_ok=False, files_ok=False)
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    result = cr.run(1)
    assert result is False
    assert len(fake.posted) == 1
    assert "unavailable this run" in fake.posted[0]


def test_run_posts_combined_report_on_success(monkeypatch):
    fake = _FakeGitHub(files=[{"path": "agents/x.py", "status": "modified", "patch": "+eval(x)"}])
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    monkeypatch.setattr(cr, "run_deterministic_pass", lambda head, files: [])
    monkeypatch.setattr(cr, "review_pr_diff", lambda diff, findings: ("## Security\nNothing found.\n", "groq"))
    result = cr.run(1)
    assert result is True
    assert len(fake.posted) == 1
    assert "Nothing found" in fake.posted[0]
    assert "via groq" in fake.posted[0]


# ============================================================================
# Findings persistence (Phase 2: closes the gap where code_lint.py's
# findings never survived past the advisory PR comment) — triggered by
# vape-reviewer.yml's pull_request:[closed] path via persist_merged_findings.
# ============================================================================

def test_select_persistable_findings_keeps_high_critical_only():
    findings = [
        ("HIGH", "agents/bad.py", 3, "eval() called on a dynamically-built string"),
        ("MEDIUM", "docs/assets/hire.js", 10, "innerHTML assigned directly from 'msg'"),
        ("CRITICAL", "agents/worse.py", 1, "pickle.loads() on a non-literal"),
    ]
    selected = cr._select_persistable_findings(findings)
    assert [f[0] for f in selected] == ["HIGH", "CRITICAL"]


def test_select_persistable_findings_drops_reviewed_exceptions():
    findings = [
        ("HIGH", "agents/bad.py", 3,
         "eval() called on a dynamically-built string [Previously reviewed and confirmed a false "
         "positive in this file: safe]"),
        ("HIGH", "agents/other.py", 5, "eval() called on a dynamically-built string"),
    ]
    selected = cr._select_persistable_findings(findings)
    assert len(selected) == 1
    assert selected[0][1] == "agents/other.py"


def test_already_persisted_true_on_match(monkeypatch):
    monkeypatch.setattr(cr, "search_memory", lambda *a, **kw: [
        {"metadata": {"pr_number": 42, "path": "agents/bad.py", "lineno": 3}},
    ])
    assert cr._already_persisted(42, "agents/bad.py", 3, "eval-exec-dynamic") is True


def test_already_persisted_false_no_match(monkeypatch):
    monkeypatch.setattr(cr, "search_memory", lambda *a, **kw: [
        {"metadata": {"pr_number": 41, "path": "agents/bad.py", "lineno": 3}},
    ])
    assert cr._already_persisted(42, "agents/bad.py", 3, "eval-exec-dynamic") is False


def test_already_persisted_false_when_memory_unavailable(monkeypatch):
    monkeypatch.setattr(cr, "search_memory", None)
    assert cr._already_persisted(42, "agents/bad.py", 3, "eval-exec-dynamic") is False


def test_append_finding_direct_writes_jsonl(tmp_path, monkeypatch):
    path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(cr, "FINDINGS_PATH", str(path))
    entry = {"category": "finding", "severity": "HIGH", "title": "x"}
    assert cr._append_finding_direct(entry) is True
    lines = path.read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["severity"] == "HIGH"


def test_append_finding_direct_handles_write_failure(monkeypatch):
    def broken_makedirs(*a, **kw):
        raise OSError("no disk")
    monkeypatch.setattr(cr.os, "makedirs", broken_makedirs)
    assert cr._append_finding_direct({"category": "finding"}) is False


def test_persist_merged_findings_returns_zero_without_merge_sha():
    assert cr.persist_merged_findings(1, None) == 0


def test_persist_merged_findings_returns_zero_on_fetch_error(monkeypatch):
    fake = _FakeGitHub(head_ok=False, files_ok=False)
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    assert cr.persist_merged_findings(1, "deadbeef") == 0


def test_persist_merged_findings_writes_high_findings_and_skips_medium(tmp_path, monkeypatch):
    fake = _FakeGitHub(files=[
        {"path": "agents/bad.py", "status": "modified"},
        {"path": "docs/assets/hire.js", "status": "modified"},
    ])
    fake._file_contents["agents/bad.py"] = "eval(x)\n"
    fake._file_contents["docs/assets/hire.js"] = "el.innerHTML = msg;\n"
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    monkeypatch.setattr(cr, "search_memory", None)  # no dedup lookups needed for a fresh PR
    findings_path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(cr, "FINDINGS_PATH", str(findings_path))

    n = cr.persist_merged_findings(7, "deadbeef")

    assert n == 1  # only the HIGH eval() finding -- innerHTML is MEDIUM, not persisted
    lines = [json.loads(line) for line in findings_path.read_text().splitlines()]
    assert len(lines) == 1
    assert lines[0]["severity"] == "HIGH"
    assert lines[0]["metadata"]["pr_number"] == 7
    assert lines[0]["metadata"]["path"] == "agents/bad.py"
    assert "PR #7" in lines[0]["title"]


def test_persist_merged_findings_skips_already_persisted(tmp_path, monkeypatch):
    fake = _FakeGitHub(files=[{"path": "agents/bad.py", "status": "modified"}])
    fake._file_contents["agents/bad.py"] = "eval(x)\n"
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    monkeypatch.setattr(cr, "search_memory", lambda *a, **kw: [
        {"metadata": {"pr_number": 7, "path": "agents/bad.py", "lineno": 1}},
    ])
    findings_path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(cr, "FINDINGS_PATH", str(findings_path))

    n = cr.persist_merged_findings(7, "deadbeef")

    assert n == 0
    assert not findings_path.exists()


def test_persist_merged_findings_excludes_reviewed_exceptions(tmp_path, monkeypatch):
    fake = _FakeGitHub(files=[{"path": "agents/bad.py", "status": "modified"}])
    fake._file_contents["agents/bad.py"] = "eval(x)\n"
    monkeypatch.setattr(cr, "_gh", lambda: fake)
    monkeypatch.setattr(cr, "search_memory", None)
    monkeypatch.setattr(cr, "_find_reviewed_exception", lambda path, msg: "confirmed safe in this context")
    findings_path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(cr, "FINDINGS_PATH", str(findings_path))

    n = cr.persist_merged_findings(7, "deadbeef")

    assert n == 0
    assert not findings_path.exists()
