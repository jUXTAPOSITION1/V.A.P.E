"""Tests for deep_dive_audit.py's Mythril wiring: _run_mythril()'s toolchain/
RPC gates (mirrors _run_slither's/_run_symbolic's own "skip cleanly if the
toolchain isn't here this run" pattern) and build_prompt()'s new MYTHRIL
section.
"""
import json
import shutil
import subprocess

from agents import deep_dive_audit as dda


def test_run_mythril_reports_missing_myth(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = dda._run_mythril("0x" + "1" * 40, "8453")
    assert result == {"ran": False, "reason": "mythril (myth) not installed in this environment this run"}


def test_run_mythril_reports_unknown_chain(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/myth")
    result = dda._run_mythril("0x" + "1" * 40, "999999")
    assert result == {"ran": False, "reason": "no known RPC endpoint for chain 999999"}


def test_run_mythril_builds_correct_command_for_https_rpc(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/myth")
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        captured["timeout"] = timeout
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"issues": []}), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    address = "0x" + "1" * 40
    result = dda._run_mythril(address, "8453", timeout=200)
    cmd = captured["cmd"]
    assert cmd[:4] == ["myth", "analyze", "-a", address]
    assert "--rpc" in cmd
    rpc_arg = cmd[cmd.index("--rpc") + 1]
    assert ":" in rpc_arg and " " not in rpc_arg
    assert "--rpctls" in cmd
    # Real bug this pins (confirmed against Mythril's own real CLI source,
    # mythril/interfaces/cli.py's get_rpc_parser(): --rpctls is declared
    # type=bool, not action="store_true", so it always consumes the next
    # argv token — a bare `--rpctls` with nothing after it is a real,
    # confirmed argparse error ("expected one argument"), which every real
    # deep-dive audit against an https RPC hit before this fix.
    assert cmd[cmd.index("--rpctls") + 1] == "True"
    assert captured["timeout"] == 200
    assert result == {"ran": True, "ok": True, "counts": {}, "findings": [], "total": 0}


def test_run_mythril_parses_real_jsonv2_issues(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/myth")
    payload = {
        "issues": [
            {"severity": "High", "swcID": "SWC-107", "swcTitle": "Reentrancy",
             "description": {"head": "Reentrancy vulnerability found.", "tail": "more detail"}},
            {"severity": "High", "swcID": "SWC-101", "swcTitle": "Integer Overflow",
             "description": {"head": "Overflow found.", "tail": "more detail"}},
            {"severity": "Low", "swcID": "SWC-103", "swcTitle": "Floating Pragma",
             "description": {"head": "Pragma is floating.", "tail": ""}},
        ]
    }

    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_mythril("0x" + "1" * 40, "8453")
    assert result["ran"] is True
    assert result["ok"] is True
    assert result["total"] == 3
    assert result["counts"] == {"High": 2, "Low": 1}
    assert result["findings"][0]["swc"] == "Reentrancy"
    assert result["findings"][0]["description"] == "Reentrancy vulnerability found."


def test_run_mythril_handles_invalid_json_output(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/myth")

    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 1, stdout="not json", stderr="mythril crashed")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_mythril("0x" + "1" * 40, "8453")
    assert result["ran"] is True
    assert result["ok"] is False
    assert "no valid JSON" in result["reason"]
    assert result["raw_tail"] == "mythril crashed"


def test_append_raw_tail_renders_captured_diagnostic():
    """Confirmed real gap: raw_tail was captured on every tool failure but
    never rendered into the report, making 'no valid JSON' unactionable and
    the report read as incomplete with no way to diagnose why a tool failed."""
    lines = []
    dda._append_raw_tail(lines, {"raw_tail": "mythril crashed: solc not found"})
    joined = "\n".join(lines)
    assert "mythril crashed: solc not found" in joined


def test_append_raw_tail_noop_when_absent():
    lines = []
    dda._append_raw_tail(lines, {"reason": "mythril (myth) not installed in this environment this run"})
    assert lines == []


def test_append_raw_tail_noop_on_blank_tail():
    lines = []
    dda._append_raw_tail(lines, {"raw_tail": "   "})
    assert lines == []


def test_run_mythril_handles_timeout(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/myth")

    def fake_run(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_mythril("0x" + "1" * 40, "8453", timeout=50)
    assert result == {"ran": True, "ok": False, "reason": "mythril timed out after 50s"}


def test_run_mythril_never_raises_on_unexpected_error(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/myth")

    def fake_run(cmd, capture_output, text, timeout):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_mythril("0x" + "1" * 40, "8453")
    assert result == {"ran": True, "ok": False, "reason": "unexpected"}


def _base_prompt_args():
    return dict(
        address="0x" + "1" * 40, chain="8453", gp={}, dex={}, onchain={},
        src={"verified": True, "contract_name": "Token", "compiler": "v0.8.19"},
        corr=[], web_rep={}, slither_result={"ran": False, "reason": "n/a"},
        symbolic_result={"ran": False, "reason": "n/a"},
    )


def test_build_prompt_includes_mythril_section_when_ran():
    args = _base_prompt_args()
    mythril_result = {"ran": True, "ok": True, "counts": {"High": 1}, "total": 1,
                       "findings": [{"severity": "High", "swc": "Reentrancy", "description": "..."}]}
    prompt = dda.build_prompt(**args, mythril_result=mythril_result)
    assert "MYTHRIL SYMBOLIC-EXECUTION SCAN (real, 1 raw issues)" in prompt
    assert "Reentrancy" in prompt


def test_build_prompt_reports_mythril_not_available():
    args = _base_prompt_args()
    mythril_result = {"ran": False, "reason": "mythril (myth) not installed in this environment this run"}
    prompt = dda.build_prompt(**args, mythril_result=mythril_result)
    assert "MYTHRIL SYMBOLIC-EXECUTION SCAN ===\nNot available this run: mythril (myth) not installed" in prompt


def test_build_prompt_defaults_mythril_result_when_omitted():
    args = _base_prompt_args()
    prompt = dda.build_prompt(**args)
    assert "MYTHRIL SYMBOLIC-EXECUTION SCAN ===\nNot available this run: unknown" in prompt
