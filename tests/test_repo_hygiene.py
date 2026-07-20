"""Tests for agents/repo_hygiene.py — the "teach VAPE" mechanism generalized
to PR/issue triage decisions. Same guarded-import + monkeypatch pattern as
tests/test_code_review.py's Memory-backed exception tests: no real disk I/O,
no network.
"""
import agents.repo_hygiene as rh


def test_record_hygiene_lesson_calls_append_to_memory(monkeypatch):
    captured = {}

    def fake_append(**kw):
        captured.update(kw)
        return {"id": "abc123"}

    monkeypatch.setattr(rh, "append_to_memory", fake_append)
    ok = rh.record_hygiene_lesson("Removed Codacy", "it was noise", tags=["codacy"])
    assert ok is True
    assert captured["category"] == "lesson"
    assert rh.HYGIENE_TAG in captured["tags"]
    assert "codacy" in captured["tags"]
    assert captured["title"] == "Removed Codacy"


def test_record_hygiene_lesson_false_when_memory_unavailable(monkeypatch):
    monkeypatch.setattr(rh, "append_to_memory", None)
    assert rh.record_hygiene_lesson("title", "content") is False


def test_search_hygiene_lessons_scopes_to_hygiene_tag(monkeypatch):
    captured = {}

    def fake_search(query, **kw):
        captured["query"] = query
        captured.update(kw)
        return [{"title": "Removed Codacy"}]

    monkeypatch.setattr(rh, "search_memory", fake_search)
    results = rh.search_hygiene_lessons("codacy")
    assert results == [{"title": "Removed Codacy"}]
    assert captured["query"] == "codacy"
    assert captured["category"] == "lesson"
    assert rh.HYGIENE_TAG in captured["tags"]


def test_search_hygiene_lessons_empty_when_memory_unavailable(monkeypatch):
    monkeypatch.setattr(rh, "search_memory", None)
    assert rh.search_hygiene_lessons("anything") == []


def test_search_hygiene_lessons_never_raises_on_backend_error(monkeypatch):
    def broken_search(*a, **kw):
        raise RuntimeError("disk full")

    monkeypatch.setattr(rh, "search_memory", broken_search)
    assert rh.search_hygiene_lessons("anything") == []
