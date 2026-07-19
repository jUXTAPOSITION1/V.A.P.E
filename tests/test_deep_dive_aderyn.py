"""Tests for deep_dive_audit.py's Aderyn wiring: _run_aderyn()'s toolchain/
project-dir gates (mirrors _run_slither's/_run_symbolic's/_run_mythril's own
"skip cleanly if the toolchain isn't here this run" pattern) and
build_prompt()'s new ADERYN section. Aderyn reuses the SAME scaffolded
Foundry project _run_symbolic already built — no on-chain address is passed
to it directly.
"""
import json
import os
import shutil
import subprocess

from agents import deep_dive_audit as dda


def test_run_aderyn_reports_missing_binary(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = dda._run_aderyn(str(tmp_path))
    assert result == {"ran": False, "reason": "aderyn not installed in this environment this run"}


def test_run_aderyn_reports_missing_project_dir(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")
    result = dda._run_aderyn(None)
    assert result["ran"] is False
    assert "no scaffolded Foundry project available" in result["reason"]


def test_run_aderyn_reports_nonexistent_project_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")
    result = dda._run_aderyn(str(tmp_path / "does-not-exist"))
    assert result["ran"] is False
    assert "no scaffolded Foundry project available" in result["reason"]


def test_run_aderyn_builds_correct_command_and_cwd(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")
    captured = {}

    def fake_run(cmd, cwd, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        out_path = cmd[cmd.index("--output") + 1]
        with open(out_path, "w") as f:
            json.dump({"issue_count": {"high": 0, "low": 0}, "high_issues": {"issues": []},
                       "low_issues": {"issues": []}}, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_aderyn(str(tmp_path), timeout=99)
    assert captured["cmd"][0] == "aderyn"
    assert "--output" in captured["cmd"]
    assert "--skip-cloc" in captured["cmd"]
    assert "--no-snippets" in captured["cmd"]
    assert captured["cwd"] == str(tmp_path)
    assert captured["timeout"] == 99
    assert result == {"ran": True, "ok": True, "counts": {"high": 0, "low": 0}, "findings": [], "total": 0}


def test_run_aderyn_parses_real_json_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")
    payload = {
        "files_summary": {"total_source_units": 3, "total_sloc": 120},
        "files_details": {},
        "issue_count": {"high": 1, "low": 2},
        "high_issues": {"issues": [
            {"title": "Reentrancy Vulnerability", "description": "External call before state update.",
             "detector_name": "reentrancy", "instances": [{"contract_path": "src/Token.sol", "line_no": 42}]},
        ]},
        "low_issues": {"issues": [
            {"title": "Floating Pragma", "description": "Pragma is floating.",
             "detector_name": "floating-pragma", "instances": [{"contract_path": "src/Token.sol", "line_no": 1}]},
            {"title": "Unused Import", "description": "Import is unused.",
             "detector_name": "unused-import", "instances": [{"contract_path": "src/Token.sol", "line_no": 2}]},
        ]},
    }

    def fake_run(cmd, cwd, capture_output, text, timeout):
        out_path = cmd[cmd.index("--output") + 1]
        with open(out_path, "w") as f:
            json.dump(payload, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_aderyn(str(tmp_path))
    assert result["ran"] is True
    assert result["ok"] is True
    assert result["total"] == 3
    assert result["counts"] == {"high": 1, "low": 2}
    assert result["findings"][0] == {"severity": "High", "title": "Reentrancy Vulnerability",
                                      "description": "External call before state update."}
    assert len(result["findings"]) == 3


def test_run_aderyn_handles_invalid_json_output(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")

    def fake_run(cmd, cwd, capture_output, text, timeout):
        # out_path is left as an empty file — no valid JSON written.
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="aderyn crashed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_aderyn(str(tmp_path))
    assert result["ran"] is True
    assert result["ok"] is False
    assert "no valid JSON" in result["reason"]


def test_run_aderyn_handles_timeout(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")

    def fake_run(cmd, cwd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_aderyn(str(tmp_path), timeout=50)
    assert result == {"ran": True, "ok": False, "reason": "aderyn timed out after 50s"}


def test_run_aderyn_never_raises_on_unexpected_error(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")

    def fake_run(cmd, cwd, capture_output, text, timeout):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_aderyn(str(tmp_path))
    assert result == {"ran": True, "ok": False, "reason": "unexpected"}


def test_run_aderyn_cleans_up_temp_output_file(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/aderyn")
    seen_path = {}

    def fake_run(cmd, cwd, capture_output, text, timeout):
        out_path = cmd[cmd.index("--output") + 1]
        seen_path["path"] = out_path
        with open(out_path, "w") as f:
            json.dump({"issue_count": {}, "high_issues": {"issues": []}, "low_issues": {"issues": []}}, f)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    dda._run_aderyn(str(tmp_path))
    assert not os.path.exists(seen_path["path"])


def _base_prompt_args():
    return dict(
        address="0x" + "1" * 40, chain="8453", gp={}, dex={}, onchain={},
        src={"verified": True, "contract_name": "Token", "compiler": "v0.8.19"},
        corr=[], web_rep={}, slither_result={"ran": False, "reason": "n/a"},
        symbolic_result={"ran": False, "reason": "n/a"},
    )


def test_build_prompt_includes_aderyn_section_when_ran():
    args = _base_prompt_args()
    aderyn_result = {"ran": True, "ok": True, "counts": {"high": 1}, "total": 1,
                      "findings": [{"severity": "High", "title": "Reentrancy", "description": "..."}]}
    prompt = dda.build_prompt(**args, aderyn_result=aderyn_result)
    assert "ADERYN STATIC AST ANALYSIS (real, 1 raw issues)" in prompt
    assert "Reentrancy" in prompt


def test_build_prompt_reports_aderyn_not_available():
    args = _base_prompt_args()
    aderyn_result = {"ran": False, "reason": "aderyn not installed in this environment this run"}
    prompt = dda.build_prompt(**args, aderyn_result=aderyn_result)
    assert "ADERYN STATIC AST ANALYSIS ===\nNot available this run: aderyn not installed" in prompt


def test_build_prompt_defaults_aderyn_result_when_omitted():
    args = _base_prompt_args()
    prompt = dda.build_prompt(**args)
    assert "ADERYN STATIC AST ANALYSIS ===\nNot available this run: unknown" in prompt
