"""Tests for agents/external_audit.py — VAPE's reusable external bug-bounty
engagement pipeline. Hermetic: urllib and ask_oci_grok_frontier are both
mocked/monkeypatched, no real network call.
"""
import json
import os
import urllib.error

from agents import external_audit as ea


def test_detect_language_move():
    assert ea.detect_language(["a/b.move", "c/d.move", "e.toml"]) == "move"


def test_detect_language_solidity():
    assert ea.detect_language(["a/B.sol", "c/D.sol", "README.md"]) == "solidity"


def test_detect_language_unknown_when_no_match():
    assert ea.detect_language(["README.md", "package.json"]) == "unknown"


def test_select_source_files_filters_by_extension():
    paths = ["a.move", "b.toml", "c.move", "README.md"]
    assert ea.select_source_files(paths, "move") == ["a.move", "c.move"]


def test_select_source_files_respects_max_files():
    paths = [f"{i}.move" for i in range(10)]
    assert len(ea.select_source_files(paths, "move", max_files=3)) == 3


def test_select_source_files_unknown_language_falls_back_to_all_paths():
    paths = ["a.rs", "b.rs"]
    assert ea.select_source_files(paths, "unknown", max_files=5) == paths


def test_fetch_file_returns_none_on_http_error(monkeypatch):
    def fake_urlopen(*a, **kw):
        raise urllib.error.HTTPError("url", 404, "Not Found", {}, None)

    monkeypatch.setattr(ea.urllib.request, "urlopen", fake_urlopen)
    result = ea.fetch_file("owner", "repo", "main", "missing.move")
    assert result is None


def test_fetch_file_returns_decoded_content_on_success(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b"module x::y; fun z() {}"

    monkeypatch.setattr(ea.urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    result = ea.fetch_file("owner", "repo", "main", "y.move")
    assert result == "module x::y; fun z() {}"


def test_fetch_repo_tree_returns_empty_list_on_failure(monkeypatch):
    def fake_urlopen(*a, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(ea.urllib.request, "urlopen", fake_urlopen)
    assert ea.fetch_repo_tree("owner", "repo", "main") == []


def test_fetch_repo_tree_extracts_blob_paths(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"tree": [
                {"path": "a.move", "type": "blob"},
                {"path": "src", "type": "tree"},
                {"path": "b.move", "type": "blob"},
            ]}).encode()

    monkeypatch.setattr(ea.urllib.request, "urlopen", lambda *a, **kw: FakeResp())
    assert ea.fetch_repo_tree("owner", "repo", "main") == ["a.move", "b.move"]


def test_build_prompt_includes_all_files_and_truncates_over_budget(monkeypatch):
    monkeypatch.setattr(ea, "MAX_TOTAL_CHARS", 10)
    files = {"a.move": "0123456789ABCDEF", "b.move": "short"}
    prompt = ea.build_prompt("Test Program", "owner", "repo", "main", files)
    assert "=== FILE: a.move ===" in prompt
    assert "=== FILE: b.move ===" in prompt
    assert "omitted" in prompt


def test_run_external_audit_no_files_fetched_returns_error(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path))
    monkeypatch.setattr(ea, "fetch_file", lambda *a, **kw: None)
    result = ea.run_external_audit("owner", "repo", "main", paths=["a.move"])
    assert "error" in result


def test_run_external_audit_writes_report_and_logs_finding(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    findings_path = tmp_path / "findings.jsonl"
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(findings_path))
    monkeypatch.setattr(ea, "fetch_file", lambda owner, repo, ref, p, timeout=15: f"// content of {p}")

    def fake_ask(system, prompt, max_tokens=None, temperature=None):
        assert "content of a.move" in prompt
        return ("## Executive Summary\nNo exploitable finding this pass — clean code.", "oci_grok")

    monkeypatch.setattr(ea, "ask_oci_grok_frontier", fake_ask)
    result = ea.run_external_audit("mmt-finance", "v3-core", "main", paths=["a.move"],
                                    program_name="Momentum Smart Contracts Core")
    assert result["provider"] == "oci_grok"
    assert result["language"] == "move"
    assert result["files_reviewed"] == 1
    assert os.path.exists(tmp_path / "audits")
    report_files = list((tmp_path / "audits").iterdir())
    assert len(report_files) == 1
    content = report_files[0].read_text()
    assert "Momentum Smart Contracts Core" in content
    assert "No exploitable finding" in content
    findings = [json.loads(l) for l in findings_path.read_text().splitlines()]
    assert len(findings) == 1
    assert findings[0]["source"] == "agents/external_audit.py"


def test_run_external_audit_handles_llm_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(ea, "fetch_file", lambda owner, repo, ref, p, timeout=15: "content")

    def fake_ask(system, prompt, max_tokens=None, temperature=None):
        raise RuntimeError("no keys")

    monkeypatch.setattr(ea, "ask_oci_grok_frontier", fake_ask)
    result = ea.run_external_audit("owner", "repo", "main", paths=["a.move"])
    assert result["provider"] is None
    assert "unavailable" in result["verdict_summary"]
