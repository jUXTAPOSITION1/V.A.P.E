"""Tests for agents/scaffold_foundry_target.py's pure parsing/scaffolding
logic — the only parts this sandbox can exercise hermetically. forge/halmos
themselves can't run here (Foundry's release-binary download is blocked by
this sandbox's egress proxy; see the module's own docstring), so
run_forge_build()/run_halmos() are exercised only for their FileNotFoundError
fallback path, not a real compile/symbolic-execution run.
"""
import json

from agents import scaffold_foundry_target as sft


# ── _sanitize_path ───────────────────────────────────────────────────────────

def test_sanitize_path_strips_leading_slash():
    assert sft._sanitize_path("/src/Token.sol") == "src/Token.sol"


def test_sanitize_path_strips_parent_dir_segments():
    assert sft._sanitize_path("../../etc/passwd") == "etc/passwd"


def test_sanitize_path_handles_backslashes():
    assert sft._sanitize_path("src\\Token.sol") == "src/Token.sol"


def test_sanitize_path_falls_back_on_empty():
    assert sft._sanitize_path("///") == "Unknown.sol"


# ── _compiler_to_solc_version ────────────────────────────────────────────────

def test_compiler_to_solc_version_parses_etherscan_format():
    assert sft._compiler_to_solc_version("v0.8.19+commit.7dd6d404") == "0.8.19"


def test_compiler_to_solc_version_handles_no_leading_v():
    assert sft._compiler_to_solc_version("0.8.24+commit.abcdef12") == "0.8.24"


def test_compiler_to_solc_version_falls_back_on_unparseable():
    assert sft._compiler_to_solc_version("garbage") == "0.8.19"


def test_compiler_to_solc_version_falls_back_on_none():
    assert sft._compiler_to_solc_version(None) == "0.8.19"


# ── parse_verified_source ────────────────────────────────────────────────────

def test_parse_verified_source_plain_single_file():
    files = sft.parse_verified_source("pragma solidity ^0.8.0;\ncontract C {}", "MyToken")
    assert files == {"MyToken.sol": "pragma solidity ^0.8.0;\ncontract C {}"}


def test_parse_verified_source_plain_single_file_defaults_name():
    files = sft.parse_verified_source("contract C {}", None)
    assert files == {"Contract.sol": "contract C {}"}


def test_parse_verified_source_etherscan_double_brace_multi_file():
    # Etherscan's own quirk: one extra pair of braces around a real Standard
    # JSON Input document.
    inner = {
        "sources": {
            "contracts/Token.sol": {"content": "contract Token {}"},
            "contracts/lib/Safe.sol": {"content": "library Safe {}"},
        }
    }
    wrapped = "{" + json.dumps(inner) + "}"
    files = sft.parse_verified_source(wrapped, "Token")
    assert files == {
        "contracts/Token.sol": "contract Token {}",
        "contracts/lib/Safe.sol": "library Safe {}",
    }


def test_parse_verified_source_sanitizes_paths_in_multi_file_input():
    inner = {"sources": {"/../../etc/Evil.sol": {"content": "contract Evil {}"}}}
    wrapped = "{" + json.dumps(inner) + "}"
    files = sft.parse_verified_source(wrapped, "Evil")
    assert files == {"etc/Evil.sol": "contract Evil {}"}


def test_parse_verified_source_skips_entries_with_no_content():
    inner = {"sources": {"A.sol": {"content": "contract A {}"}, "B.sol": {}}}
    wrapped = "{" + json.dumps(inner) + "}"
    files = sft.parse_verified_source(wrapped, "A")
    assert files == {"A.sol": "contract A {}"}


def test_parse_verified_source_empty_input_returns_empty():
    assert sft.parse_verified_source(None, "X") == {}
    assert sft.parse_verified_source("", "X") == {}


def test_parse_verified_source_unparseable_json_returns_empty():
    assert sft.parse_verified_source("{not valid json", "X") == {}


def test_parse_verified_source_json_without_sources_key_returns_empty():
    assert sft.parse_verified_source("{" + json.dumps({"foo": "bar"}) + "}", "X") == {}


# ── scaffold_project ──────────────────────────────────────────────────────────

def test_scaffold_project_writes_files_and_foundry_toml(tmp_path):
    files = {"Token.sol": "contract Token {}", "lib/Safe.sol": "library Safe {}"}
    out = sft.scaffold_project(files, "v0.8.19+commit.7dd6d404", str(tmp_path))

    assert (tmp_path / "src" / "Token.sol").read_text() == "contract Token {}"
    assert (tmp_path / "src" / "lib" / "Safe.sol").read_text() == "library Safe {}"
    toml = (tmp_path / "foundry.toml").read_text()
    assert 'solc_version = "0.8.19"' in toml
    assert out == str(tmp_path)


def test_scaffold_project_handles_empty_files_dict(tmp_path):
    sft.scaffold_project({}, None, str(tmp_path))
    assert (tmp_path / "src").is_dir()
    assert (tmp_path / "test").is_dir()
    assert (tmp_path / "foundry.toml").exists()


# ── run_forge_build / run_halmos fallback paths ─────────────────────────────

def test_run_forge_build_reports_missing_binary_cleanly(tmp_path, monkeypatch):
    import subprocess

    def _raise(*a, **k):
        raise FileNotFoundError()
    monkeypatch.setattr(subprocess, "run", _raise)
    result = sft.run_forge_build(str(tmp_path))
    assert result == {"ok": False, "output": "forge not installed in this environment"}


def test_run_halmos_reports_missing_binary_cleanly(tmp_path, monkeypatch):
    import subprocess

    def _raise(*a, **k):
        raise FileNotFoundError()
    monkeypatch.setattr(subprocess, "run", _raise)
    result = sft.run_halmos(str(tmp_path))
    assert result == {"ran": False, "reason": "halmos not installed in this environment"}


# ── scaffold_and_analyze — orchestration short-circuits ──────────────────────

def test_scaffold_and_analyze_reports_unverified_contract(monkeypatch):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"verified": False, "source_code": None})
    result = sft.scaffold_and_analyze("0xdead")
    assert result == {"ran": False, "reason": "contract unverified or no source available"}


def test_scaffold_and_analyze_reports_unparseable_source(monkeypatch):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"verified": True, "source_code": "{not json",
                                               "contract_name": "X", "compiler": "v0.8.19"})
    result = sft.scaffold_and_analyze("0xdead")
    assert result["ran"] is False
    assert "could not be parsed" in result["reason"]


def test_scaffold_and_analyze_reports_source_lookup_error(monkeypatch):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"error": "no api key"})
    result = sft.scaffold_and_analyze("0xdead")
    assert result["ran"] is False
    assert "source lookup failed" in result["reason"]


def test_scaffold_and_analyze_uses_pre_fetched_src_without_refetching(monkeypatch):
    def _boom(addr, chain):
        raise AssertionError("should not re-fetch when pre_fetched_src is given")
    monkeypatch.setattr(sft.DF, "get_contract_source", _boom)
    result = sft.scaffold_and_analyze(
        "0xdead", pre_fetched_src={"verified": False, "source_code": None})
    assert result == {"ran": False, "reason": "contract unverified or no source available"}
