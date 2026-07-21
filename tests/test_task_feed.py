"""Hermetic tests for agents.task_feed's deterministic parts — real-commit
filtering/classification and the honest degrade path when nothing is found.
The LLM synthesis call is mocked/stubbed out; only its input grounding is
checked, never a real network/LLM call."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import task_feed as tf


def _commit(sha, message, author_name="VAPE Bot", committer_login="github-actions[bot]"):
    return {
        "sha": sha,
        "html_url": f"https://github.com/x/y/commit/{sha}",
        "commit": {"author": {"name": author_name, "date": "2026-07-20T12:00:00Z"}, "message": message},
        "committer": {"login": committer_login},
    }


def test_classify_matches_real_commit_message_patterns():
    assert tf._classify("Featured investigation 2026-07-20T12:00Z")[0] == "investigation"
    assert tf._classify("SCOUT bounty radar sweep 2026-07-20T12:00Z")[0] == "bounty-radar"
    assert tf._classify("Deep-dive audit report for 0xabc...")[0] == "audit"
    assert tf._classify("Broadcast 2026-07-20-12.md")[0] == "broadcast"
    assert tf._classify("Update reputation.json")[0] == "reputation"
    assert tf._classify("some totally unrelated commit")[0] == "automation"


def test_classify_uses_only_the_first_line():
    kind, first_line = tf._classify("Featured investigation 2026-07-20T12:00Z\n\nlonger body text here")
    assert kind == "investigation"
    assert first_line == "Featured investigation 2026-07-20T12:00Z"


def test_recent_bot_commits_filters_to_real_automation_identity(monkeypatch):
    fake_commits = [
        _commit("aaaaaaaaaa", "Featured investigation 2026-07-20T12:00Z"),
        _commit("bbbbbbbbbb", "A human's manual commit", author_name="Some Human", committer_login="some-human"),
        _commit("cccccccccc", "SCOUT bounty radar sweep 2026-07-20T13:00Z"),
    ]
    monkeypatch.setattr(tf, "_get", lambda *a, **kw: fake_commits)
    tasks = tf._recent_bot_commits()
    assert len(tasks) == 2
    assert tasks[0]["kind"] == "investigation"
    assert tasks[1]["kind"] == "bounty-radar"
    assert all(t["sha"] for t in tasks)


def test_recent_bot_commits_returns_empty_on_non_list_response(monkeypatch):
    monkeypatch.setattr(tf, "_get", lambda *a, **kw: {"error": "HTTP 502"})
    assert tf._recent_bot_commits() == []


def test_recent_bot_commits_respects_keep_limit(monkeypatch):
    many = [_commit(f"{i:010d}", "Featured investigation cycle") for i in range(50)]
    monkeypatch.setattr(tf, "_get", lambda *a, **kw: many)
    assert len(tf._recent_bot_commits()) == tf.KEEP_LIMIT


def test_synthesis_is_honest_when_no_tasks():
    assert "No automated activity" in tf._synthesis([])


def test_synthesis_calls_grok_analysis_with_grounded_real_data(monkeypatch):
    captured = {}

    def fake_grok_analysis(role, grounding, **kw):
        captured["role"] = role
        captured["grounding"] = grounding
        return "VAPE ran two investigations and one bounty-radar sweep this cycle."

    import agents.intel_common as intel_common
    monkeypatch.setattr(intel_common, "grok_analysis", fake_grok_analysis)

    tasks = [{"kind": "investigation", "message": "Featured investigation X", "date": "2026-07-20T12:00:00Z"}]
    result = tf._synthesis(tasks)
    assert result == "VAPE ran two investigations and one bounty-radar sweep this cycle."
    assert "Featured investigation X" in captured["grounding"]
