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

    def fake_ask(system, prompt, max_tokens=None, temperature=None, search=None):
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


def test_run_external_audit_defaults_to_paid_engagement(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(ea, "fetch_file", lambda owner, repo, ref, p, timeout=15: "content")
    monkeypatch.setattr(ea, "ask_oci_grok_frontier",
                        lambda *a, **kw: ("## Executive Summary\nclean", "oci_grok"))
    result = ea.run_external_audit("owner", "repo", "main", paths=["a.move"])
    assert result["engagement"] == "paid"
    content = list((tmp_path / "audits").iterdir())[0].read_text()
    assert "pipeline-validation run" not in content


def test_run_external_audit_validation_engagement_framed_honestly(monkeypatch, tmp_path):
    """Real gap this pins: a manual validation dispatch against a real repo
    must never read as a real client engagement — mirrors deep_dive_audit.py's
    identical validation-framing requirement."""
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(ea, "fetch_file", lambda owner, repo, ref, p, timeout=15: "content")
    monkeypatch.setattr(ea, "ask_oci_grok_frontier",
                        lambda *a, **kw: ("## Executive Summary\nclean", "oci_grok"))
    result = ea.run_external_audit("owner", "repo", "main", paths=["a.move"], engagement="validation")
    assert result["engagement"] == "validation"
    content = list((tmp_path / "audits").iterdir())[0].read_text()
    assert "pipeline-validation run against a real target" in content
    assert "no payment was made" in content


def test_run_external_audit_handles_llm_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(ea, "fetch_file", lambda owner, repo, ref, p, timeout=15: "content")

    def fake_ask(system, prompt, max_tokens=None, temperature=None, search=None):
        raise RuntimeError("no keys")

    monkeypatch.setattr(ea, "ask_oci_grok_frontier", fake_ask)
    result = ea.run_external_audit("owner", "repo", "main", paths=["a.move"])
    assert result["provider"] is None
    assert "unavailable" in result["verdict_summary"]


# ── Move Prover wiring ───────────────────────────────────────────────────────

def test_derive_move_toml_candidates_from_sources_ancestor():
    candidates = ea._derive_move_toml_candidates(["clmm/sources/actions/trade.move"])
    assert candidates == ["clmm/Move.toml", "clmm/move.toml"]


def test_derive_move_toml_candidates_root_level_sources():
    candidates = ea._derive_move_toml_candidates(["sources/trade.move"])
    assert candidates == ["Move.toml", "move.toml"]


def test_derive_move_toml_candidates_dedupes_across_paths():
    candidates = ea._derive_move_toml_candidates(
        ["clmm/sources/a.move", "clmm/sources/actions/b.move"])
    assert candidates == ["clmm/Move.toml", "clmm/move.toml"]


def test_derive_move_toml_candidates_skips_paths_without_sources():
    assert ea._derive_move_toml_candidates(["README.md", "flat.move"]) == []


def test_strip_package_root_removes_prefix():
    assert ea._strip_package_root("clmm/sources/a.move", "clmm") == "sources/a.move"


def test_strip_package_root_noop_without_prefix():
    assert ea._strip_package_root("sources/a.move", "") == "sources/a.move"


def test_run_external_audit_wires_move_prover_when_toml_found(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))

    def fake_fetch(owner, repo, ref, p, timeout=15):
        if p.endswith("Move.toml"):
            return "[package]\nname = \"mmt_v3\"\n"
        if p == "clmm/move.toml":
            return None
        return f"module mmt_v3::x {{}} // {p}"

    monkeypatch.setattr(ea, "fetch_file", fake_fetch)
    monkeypatch.setattr(ea, "ask_oci_grok_frontier",
                        lambda system, prompt, max_tokens=None, temperature=None:
                        ("## Executive Summary\nClean.", "oci_grok"))

    captured = {}

    def fake_scaffold_and_prove(files, move_toml_content, focus_note=""):
        captured["files"] = files
        captured["move_toml"] = move_toml_content
        return {"ran": True, "prover": {"returncode": 0, "output": "1 verified"}}

    monkeypatch.setattr(ea, "scaffold_and_prove", fake_scaffold_and_prove)
    result = ea.run_external_audit("mmt-finance", "v3-core", "main",
                                    paths=["clmm/sources/actions/trade.move"])
    assert result["move_prover_ran"] is True
    assert captured["files"] == {"sources/actions/trade.move": "module mmt_v3::x {} // clmm/sources/actions/trade.move"}
    assert "mmt_v3" in captured["move_toml"]
    content = (tmp_path / "audits").iterdir().__next__().read_text()
    assert "Formal Verification (Move Prover" in content
    assert "1 verified" in content


def test_run_external_audit_reports_missing_move_toml(monkeypatch, tmp_path):
    monkeypatch.setattr(ea, "AUDIT_DIR", str(tmp_path / "audits"))
    monkeypatch.setattr(ea, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(ea, "fetch_file",
                        lambda owner, repo, ref, p, timeout=15: None if "toml" in p.lower() else f"// {p}")
    monkeypatch.setattr(ea, "ask_oci_grok_frontier",
                        lambda system, prompt, max_tokens=None, temperature=None: ("Clean.", "oci_grok"))
    result = ea.run_external_audit("mmt-finance", "v3-core", "main",
                                    paths=["clmm/sources/actions/trade.move"])
    assert result["move_prover_ran"] is False
    content = (tmp_path / "audits").iterdir().__next__().read_text()
    assert "could not locate this package's real Move.toml" in content
