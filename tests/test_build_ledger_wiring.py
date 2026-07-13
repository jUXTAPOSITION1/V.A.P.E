"""Tests for the build_log wiring added to agents/self_improve.py and
agents/skillforge_build.py — both pipelines open real PRs but previously
never told skillforge/memory/build_log.jsonl (the site's Development
Ledger) about it. Hermetic: monkeypatches agents.build_ledger.log_build
so no real Memory file is touched.
"""
from agents import self_improve, skillforge_build


def test_self_improve_logs_build_entry_when_pr_opened(monkeypatch):
    calls = []
    monkeypatch.setattr("agents.build_ledger.log_build",
                         lambda **kw: calls.append(kw))
    target = {"kind": "redteam-finding", "module": "agents/run.py", "issue": "some issue"}
    self_improve._log_build_entry(target, "print('fix')", "https://github.com/x/y/pull/1")
    assert len(calls) == 1
    assert calls[0]["source"] == "agents/self_improve.py"
    assert "agents/run.py" in calls[0]["title"]
    assert calls[0]["files"] == ["agents/run.py"]


def test_self_improve_skips_build_entry_without_code_or_pr(monkeypatch):
    calls = []
    monkeypatch.setattr("agents.build_ledger.log_build",
                         lambda **kw: calls.append(kw))
    target = {"kind": "pyflakes", "module": "agents/x.py", "issue": "unused import"}
    self_improve._log_build_entry(target, "", "https://github.com/x/y/pull/1")
    self_improve._log_build_entry(target, "print('fix')", None)
    assert calls == []


def test_skillforge_build_logs_build_entry_when_pr_opened(monkeypatch):
    calls = []
    monkeypatch.setattr("agents.build_ledger.log_build",
                         lambda **kw: calls.append(kw))
    proposal = {"title": "New recon helper", "justification": "gap X", "spec": "spec Y"}
    files = {"tools/new_helper.py": "code"}
    skillforge_build._log_build_entry(proposal, files, "https://github.com/x/y/pull/2")
    assert len(calls) == 1
    assert calls[0]["source"] == "agents/skillforge_build.py"
    assert "New recon helper" in calls[0]["title"]
    assert calls[0]["files"] == ["tools/new_helper.py"]


def test_skillforge_build_skips_build_entry_without_files_or_pr(monkeypatch):
    calls = []
    monkeypatch.setattr("agents.build_ledger.log_build",
                         lambda **kw: calls.append(kw))
    proposal = {"title": "New recon helper", "justification": "gap X", "spec": "spec Y"}
    skillforge_build._log_build_entry(proposal, {}, "https://github.com/x/y/pull/2")
    skillforge_build._log_build_entry(proposal, {"a.py": "code"}, None)
    assert calls == []
