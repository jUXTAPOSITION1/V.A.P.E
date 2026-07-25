"""Tests for deep_dive_audit.py's Slither wiring: _run_slither()'s toolchain/
key gates (mirrors _run_mythril's/_run_symbolic's own "skip cleanly if the
toolchain isn't here this run" pattern) and the real chain->network-prefix
fix below.

Real, confirmed bug this pins (2026-07-25): Slither had never once
succeeded in production for a non-Ethereum-mainnet target (Base is VAPE's
default chain) — confirmed against crytic-compile's own real source
(crytic_compile/platform/etherscan.py): a bare `0xADDRESS` with no network
prefix always resolves to Etherscan V2 chainid=1 (Ethereum mainnet)
regardless of the contract's actual chain, so a Base-only-verified
contract's lookup always came back "not found".
"""
import json
import shutil
import subprocess

from agents import deep_dive_audit as dda


def test_run_slither_reports_missing_binary(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    result = dda._run_slither("0x" + "1" * 40, "8453")
    assert result == {"ran": False, "reason": "slither not installed in this environment this run"}


def test_run_slither_reports_missing_key(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.delenv("ETHERSCAN_API_KEY", raising=False)
    result = dda._run_slither("0x" + "1" * 40, "8453")
    assert result == {"ran": False, "reason": "no ETHERSCAN_API_KEY — slither needs it to fetch+compile by address"}


def test_run_slither_prefixes_base_target(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "key123")
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"results": {"detectors": []}}), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    address = "0x" + "1" * 40
    dda._run_slither(address, "8453")
    assert captured["cmd"][:2] == ["slither", f"base:{address}"]


def test_run_slither_prefixes_arbitrum_target(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "key123")
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"results": {"detectors": []}}), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    address = "0x" + "2" * 40
    dda._run_slither(address, "42161")
    assert captured["cmd"][:2] == ["slither", f"arbi:{address}"]


def test_run_slither_unknown_chain_passes_bare_address(monkeypatch):
    """A chain with no known Slither network-prefix mapping falls back to a
    bare address rather than guessing a wrong prefix — same as before this
    fix for any chain outside VAPE's own EVM_CHAINS list."""
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "key123")
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"results": {"detectors": []}}), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    address = "0x" + "3" * 40
    dda._run_slither(address, "999999")
    assert captured["cmd"][:2] == ["slither", address]


def test_run_slither_parses_real_findings(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "key123")
    payload = {"results": {"detectors": [
        {"impact": "High", "check": "reentrancy-eth", "description": "Reentrancy in foo()"},
        {"impact": "Medium", "check": "unchecked-transfer", "description": "Unchecked transfer"},
        {"impact": "High", "check": "arbitrary-send", "description": "Arbitrary send"},
    ]}}

    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_slither("0x" + "1" * 40, "8453")
    assert result["ran"] is True and result["ok"] is True
    assert result["total"] == 3
    assert result["counts"] == {"High": 2, "Medium": 1}


def test_run_slither_handles_invalid_json_output(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "key123")

    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Contract source code not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_slither("0x" + "1" * 40, "8453")
    assert result["ran"] is True and result["ok"] is False
    assert "no valid JSON" in result["reason"]
    assert result["raw_tail"] == "Contract source code not found"


def test_run_slither_handles_timeout(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/slither")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "key123")

    def fake_run(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = dda._run_slither("0x" + "1" * 40, "8453", timeout=30)
    assert result == {"ran": True, "ok": False, "reason": "slither timed out after 30s"}
