"""Tests for agents/scaffold_move_target.py — the Move Prover scaffolding
pipeline (mirrors scaffold_foundry_target.py's Halmos pattern for Move
targets). Hermetic: subprocess and the LLM call are both mocked/
monkeypatched, no real network call, no real sui-prover invocation.
"""
import shutil
import subprocess

from agents import scaffold_move_target as smt


def test_write_move_toml_writes_content_unmodified(tmp_path):
    smt.write_move_toml(str(tmp_path), "[package]\nname = \"x\"\n")
    written = (tmp_path / "Move.toml").read_text()
    assert written == "[package]\nname = \"x\"\n"


def test_scaffold_package_writes_files_at_real_relpaths(tmp_path):
    files = {"sources/actions/trade.move": "module x::trade {}",
             "sources/pool.move": "module x::pool {}"}
    out = smt.scaffold_package(files, "[package]\nname = \"x\"\n", str(tmp_path))
    assert out == str(tmp_path)
    assert (tmp_path / "sources" / "actions" / "trade.move").read_text() == "module x::trade {}"
    assert (tmp_path / "sources" / "pool.move").read_text() == "module x::pool {}"
    assert (tmp_path / "Move.toml").exists()


def test_scaffold_package_handles_empty_files_dict(tmp_path):
    smt.scaffold_package({}, "[package]\nname = \"x\"\n", str(tmp_path))
    assert (tmp_path / "Move.toml").exists()
    assert not (tmp_path / "sources").exists()


def test_draft_move_specs_extracts_code_from_markdown_fence(monkeypatch):
    def fake_ask(system, user, max_tokens=None, temperature=None):
        assert "trade.move" in user
        return ("```move\nspec mmt_v3::trade {\n  pragma verify = true;\n}\n```", "oci_grok")

    monkeypatch.setattr(smt, "ask_oci_grok_frontier", fake_ask)
    code, provider = smt.draft_move_specs({"sources/actions/trade.move": "module mmt_v3::trade {}"})
    assert provider == "oci_grok"
    assert code.startswith("spec mmt_v3::trade")


def test_draft_move_specs_handles_llm_failure(monkeypatch):
    def fake_ask(system, user, max_tokens=None, temperature=None):
        raise RuntimeError("no keys")

    monkeypatch.setattr(smt, "ask_oci_grok_frontier", fake_ask)
    code, reason = smt.draft_move_specs({"a.move": "module x {}"})
    assert code is None
    assert "no keys" in reason


def test_run_sui_prover_reports_missing_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = smt.run_sui_prover(str(tmp_path))
    assert result["ran"] is False
    assert "not installed" in result["reason"]


def test_run_sui_prover_runs_and_captures_output(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/sui-prover" if name == "sui-prover" else None)

    def fake_run(cmd, cwd, capture_output, text, timeout):
        assert cmd == ["sui-prover"]
        assert cwd == str(tmp_path)
        return subprocess.CompletedProcess(cmd, 0, stdout="1 verified", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = smt.run_sui_prover(str(tmp_path))
    assert result == {"ran": True, "returncode": 0, "output": "1 verified"}


def test_run_sui_prover_handles_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/sui-prover")

    def fake_run(cmd, cwd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = smt.run_sui_prover(str(tmp_path), timeout=30)
    assert result == {"ran": True, "returncode": None, "output": "sui-prover timed out after 30s"}


def test_scaffold_and_prove_requires_move_toml():
    result = smt.scaffold_and_prove({"a.move": "x"}, None)
    assert result["ran"] is False
    assert "Move.toml" in result["reason"]


def test_scaffold_and_prove_requires_files():
    result = smt.scaffold_and_prove({}, "[package]\nname=\"x\"\n")
    assert result["ran"] is False
    assert "no source files" in result["reason"]


def test_scaffold_and_prove_reports_no_specs_drafted(monkeypatch, tmp_path):
    monkeypatch.setattr(smt, "draft_move_specs", lambda files, focus_note="": (None, "LLM unavailable: boom"))
    result = smt.scaffold_and_prove({"sources/a.move": "module x {}"}, "[package]\nname=\"x\"\n",
                                     workdir=str(tmp_path))
    assert result["ran"] is False
    assert "LLM unavailable" in result["reason"]
    assert result["project_dir"] == str(tmp_path)


def test_scaffold_and_prove_full_pipeline(monkeypatch, tmp_path):
    monkeypatch.setattr(smt, "draft_move_specs",
                        lambda files, focus_note="": ("spec mmt_v3::a { pragma verify = true; }", "oci_grok"))
    monkeypatch.setattr(smt, "run_sui_prover", lambda project_dir, timeout=300: {"ran": True, "returncode": 0,
                                                                                 "output": "1 verified"})
    result = smt.scaffold_and_prove({"sources/a.move": "module mmt_v3::a {}"}, "[package]\nname=\"x\"\n",
                                     workdir=str(tmp_path))
    assert result["ran"] is True
    assert result["drafted_by"] == "oci_grok"
    assert "spec mmt_v3::a" in result["drafted_code"]
    assert result["prover"]["returncode"] == 0
    assert (tmp_path / "sources" / "vape_prover_specs.move").exists()
    assert (tmp_path / "sources" / "a.move").exists()
