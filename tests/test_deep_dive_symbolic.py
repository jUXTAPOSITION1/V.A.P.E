"""Tests for deep_dive_audit.py's Halmos/symbolic-testing wiring: _run_symbolic()'s
toolchain gate (mirrors _run_slither's own "skip cleanly if not installed this
run" pattern) and build_prompt()'s new HALMOS section.
"""
import shutil

from agents import deep_dive_audit as dda


def test_run_symbolic_reports_missing_forge(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = dda._run_symbolic("0x" + "1" * 40, "8453", {"verified": True})
    assert result == {"ran": False, "reason": "forge not installed in this environment this run"}


def test_run_symbolic_reports_missing_halmos_when_forge_present(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/forge" if name == "forge" else None)
    result = dda._run_symbolic("0x" + "1" * 40, "8453", {"verified": True})
    assert result == {"ran": False, "reason": "halmos not installed in this environment this run"}


def test_run_symbolic_calls_scaffold_and_analyze_with_pre_fetched_src(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    captured = {}

    def fake_scaffold(address, chain_id, pre_fetched_src=None):
        captured["address"] = address
        captured["chain_id"] = chain_id
        captured["pre_fetched_src"] = pre_fetched_src
        return {"ran": True, "halmos": {"returncode": 0, "output": "ok"}}

    monkeypatch.setattr(dda, "scaffold_and_analyze", fake_scaffold)
    src = {"verified": True, "contract_name": "Token"}
    result = dda._run_symbolic("0xdead", "8453", src)
    assert result == {"ran": True, "halmos": {"returncode": 0, "output": "ok"}}
    assert captured == {"address": "0xdead", "chain_id": 8453, "pre_fetched_src": src}


def test_run_symbolic_never_raises_on_unexpected_error(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    def _boom(*a, **k):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(dda, "scaffold_and_analyze", _boom)
    result = dda._run_symbolic("0xdead", "8453", {})
    assert result == {"ran": False, "reason": "unexpected"}


def _base_prompt_args():
    return dict(
        address="0x" + "1" * 40, chain="8453", gp={}, dex={}, onchain={},
        src={"verified": True, "contract_name": "Token", "compiler": "v0.8.19"},
        corr=[], web_rep={},
    )


def test_build_prompt_includes_halmos_section_when_ran():
    args = _base_prompt_args()
    symbolic_result = {"ran": True, "drafted_code": "contract X {}",
                        "halmos": {"returncode": 0, "output": "1 passed"}}
    prompt = dda.build_prompt(**args, slither_result={"ran": False, "reason": "n/a"},
                               symbolic_result=symbolic_result)
    assert "HALMOS SYMBOLIC TESTING (real run" in prompt
    assert "1 passed" in prompt
    assert "contract X {}" in prompt


def test_build_prompt_reports_symbolic_not_available():
    args = _base_prompt_args()
    symbolic_result = {"ran": False, "reason": "forge not installed in this environment this run"}
    prompt = dda.build_prompt(**args, slither_result={"ran": False, "reason": "n/a"},
                               symbolic_result=symbolic_result)
    assert "HALMOS SYMBOLIC TESTING ===\nNot available this run: forge not installed" in prompt
