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
    toml = (tmp_path / "foundry.toml").read_text()
    assert "remappings = []" in toml


def test_scaffold_project_writes_remapping_for_bundled_library_import():
    """Real gap this covers (audit-deep-dive-diem-2026-07-21.md): Etherscan's
    multi-file verified source bundles an imported library (e.g.
    OpenZeppelin) under a `sources` key that IS the literal absolute import
    path used elsewhere — forge needs an explicit remapping to resolve that
    import to where scaffold_project() actually wrote the file, or
    `forge build` fails outright with "File not found... Searched the
    following locations: ''" before Halmos/Aderyn ever get a chance to run."""
    files = {
        "contracts/Token.sol": 'import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";\ncontract Token {}',
        "@openzeppelin/contracts/token/ERC20/ERC20.sol": "contract ERC20 {}",
    }
    remappings = sft._generate_remappings(files)
    assert "@openzeppelin/=src/@openzeppelin/" in remappings
    assert "contracts/=src/contracts/" in remappings


def test_generate_remappings_ignores_single_file_at_root():
    assert sft._generate_remappings({"Token.sol": "contract Token {}"}) == []


def test_generate_remappings_empty_input_returns_empty():
    assert sft._generate_remappings({}) == []


# ── _extract_declared_remappings ────────────────────────────────────────────

def test_extract_declared_remappings_reads_settings_remappings():
    """Real gap this covers (audit-validation-diem-2026-07-25.md): a
    contract's OpenZeppelin imports resolve via a dependency-manager-style
    alias (`@openzeppelin/=dependencies/@openzeppelin-contracts@5.0.2/`)
    that has no relation to the bundled files' own top-level path segment
    ('dependencies') — _generate_remappings()'s path-derived heuristic can
    never reconstruct that alias; it has to come from the original
    compiler's own settings.remappings."""
    wrapped = "{" + json.dumps({
        "sources": {"src/Diem.sol": {"content": "contract Diem {}"}},
        "settings": {"remappings": ["@openzeppelin/=dependencies/@openzeppelin-contracts@5.0.2/"]},
    }) + "}"
    assert sft._extract_declared_remappings(wrapped) == [
        "@openzeppelin/=dependencies/@openzeppelin-contracts@5.0.2/"
    ]


def test_extract_declared_remappings_handles_double_brace_wrapping():
    inner = json.dumps({"sources": {}, "settings": {"remappings": ["lib/=deps/lib/"]}})
    assert sft._extract_declared_remappings("{" + inner + "}") == ["lib/=deps/lib/"]


def test_extract_declared_remappings_no_settings_returns_empty():
    wrapped = "{" + json.dumps({"sources": {}}) + "}"
    assert sft._extract_declared_remappings(wrapped) == []


def test_extract_declared_remappings_non_dict_settings_does_not_raise():
    """Real bug this pins (CodeRabbit, PR #277): `settings` present but set
    to a non-dict (string/number/list) used to raise AttributeError from
    `.get("settings", {}).get("remappings")` — the {} default only ever
    applies when the key is absent, not when it's present with the wrong
    type. Must degrade to [] like every other malformed-input case here."""
    for bad_settings in ("a string", 42, ["a", "list"], None):
        wrapped = "{" + json.dumps({"sources": {}, "settings": bad_settings}) + "}"
        assert sft._extract_declared_remappings(wrapped) == []


def test_extract_declared_remappings_rejects_absolute_target_path():
    """Real bug this pins: checking `.startswith('/')`/`'..' in` against the
    RAW `prefix=path` string only ever catches an absolute/traversal
    PREFIX (which no real remapping ever is, e.g. '@openzeppelin/') — it
    never inspects the PATH half, so '@evil/=/etc/' or an empty-prefix
    '=/etc/passwd' sailed straight through untouched. These strings are
    written verbatim into foundry.toml and honored by solc's own import
    resolution when `forge build` runs against a malicious contract's
    self-declared Etherscan verification metadata — an absolute or
    traversal-escaping PATH must be rejected regardless of which side of
    '=' it's on."""
    wrapped = "{" + json.dumps({"sources": {}, "settings": {"remappings": [
        "@evil/=/etc/",
        "@evil2/=/root/.ssh/",
        "=/etc/passwd",
        "../escape/=lib/",
        "@openzeppelin/=dependencies/@openzeppelin-contracts@5.0.2/",
    ]}}) + "}"
    assert sft._extract_declared_remappings(wrapped) == [
        "@openzeppelin/=dependencies/@openzeppelin-contracts@5.0.2/"
    ]


def test_extract_declared_remappings_ignores_malformed_entries():
    wrapped = "{" + json.dumps({"sources": {}, "settings": {"remappings": [
        "ok/=path/", "no-equals-sign", "../escape/=path/", 42, None,
    ]}}) + "}"
    assert sft._extract_declared_remappings(wrapped) == ["ok/=path/"]


def test_extract_declared_remappings_plain_single_file_returns_empty():
    assert sft._extract_declared_remappings("contract C {}") == []


def test_extract_declared_remappings_empty_input_returns_empty():
    assert sft._extract_declared_remappings(None) == []
    assert sft._extract_declared_remappings("") == []


def test_extract_declared_remappings_unparseable_json_returns_empty():
    assert sft._extract_declared_remappings("{not valid json") == []


def test_scaffold_project_declared_remapping_takes_precedence(tmp_path):
    """When Etherscan's own settings.remappings declares an alias, it must
    win over the path-derived guess for the same prefix rather than both
    being written (a Foundry duplicate-remapping-prefix warning at best,
    or the wrong target directory at worst)."""
    files = {"dependencies/oz/ERC20.sol": "contract ERC20 {}"}
    sft.scaffold_project(files, "v0.8.19+commit.7dd6d404", str(tmp_path),
                          declared_remappings=["@openzeppelin/=dependencies/oz/"])
    toml = (tmp_path / "foundry.toml").read_text()
    assert "@openzeppelin/=dependencies/oz/" in toml
    assert "dependencies/=src/dependencies/" in toml


def test_scaffold_project_no_declared_remappings_falls_back_to_derived(tmp_path):
    files = {"lib/Safe.sol": "library Safe {}"}
    sft.scaffold_project(files, None, str(tmp_path), declared_remappings=None)
    toml = (tmp_path / "foundry.toml").read_text()
    assert "lib/=src/lib/" in toml


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


# ── draft_exploit_test ────────────────────────────────────────────────────────

def test_draft_exploit_test_reports_llm_unavailable(monkeypatch):
    def _boom(system, user, **kw):
        raise RuntimeError("no provider configured")
    monkeypatch.setattr(sft, "ask_oci_grok_frontier", _boom)
    code, reason = sft.draft_exploit_test({"Token.sol": "contract Token {}"}, "Token", "0xdead")
    assert code is None
    assert "LLM unavailable" in reason


def test_draft_exploit_test_honors_no_exploit_found(monkeypatch):
    monkeypatch.setattr(sft, "ask_oci_grok_frontier",
                         lambda system, user, **kw: ("NO_EXPLOIT_FOUND: no exploitable path in this contract", "grok"))
    code, reason = sft.draft_exploit_test({"Token.sol": "contract Token {}"}, "Token", "0xdead")
    assert code is None
    assert reason == "no exploit found: no exploitable path in this contract"


def test_draft_exploit_test_strips_markdown_fence(monkeypatch):
    fenced = "```solidity\n// SPDX-License-Identifier: MIT\ncontract Exploit {}\n```"
    monkeypatch.setattr(sft, "ask_oci_grok_frontier", lambda system, user, **kw: (fenced, "grok"))
    code, provider = sft.draft_exploit_test({"Token.sol": "contract Token {}"}, "Token", "0xdead")
    assert code == "// SPDX-License-Identifier: MIT\ncontract Exploit {}"
    assert provider == "grok"


def test_draft_exploit_test_passes_through_unfenced_code(monkeypatch):
    monkeypatch.setattr(sft, "ask_oci_grok_frontier",
                         lambda system, user, **kw: ("// SPDX-License-Identifier: MIT\ncontract Exploit {}", "grok"))
    code, provider = sft.draft_exploit_test({"Token.sol": "contract Token {}"}, "Token", "0xdead")
    assert code == "// SPDX-License-Identifier: MIT\ncontract Exploit {}"


# ── _forge_subprocess_env ────────────────────────────────────────────────────

def test_forge_subprocess_env_strips_secrets(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.setenv("HOME", "/home/x")
    monkeypatch.setenv("XAI_API_KEY_1", "super-secret-key")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_super_secret")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "another-secret")
    env = sft._forge_subprocess_env()
    assert env["PATH"] == "/usr/bin"
    assert env["HOME"] == "/home/x"
    assert "XAI_API_KEY_1" not in env
    assert "GITHUB_TOKEN" not in env
    assert "ETHERSCAN_API_KEY" not in env


def test_forge_subprocess_env_omits_unset_optional_keys(monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("TMPDIR", raising=False)
    env = sft._forge_subprocess_env()
    assert "HOME" not in env
    assert "TMPDIR" not in env
    assert set(env) <= {"PATH", "HOME", "TMPDIR", "TEMP", "TERM", "LANG"}


# ── run_forge_test_exploit ────────────────────────────────────────────────────

def test_run_forge_test_exploit_reports_missing_binary_cleanly(tmp_path, monkeypatch):
    import subprocess

    def _raise(*a, **k):
        raise FileNotFoundError()
    monkeypatch.setattr(subprocess, "run", _raise)
    result = sft.run_forge_test_exploit(str(tmp_path), "https://example-rpc.test")
    assert result == {"ran": False, "reason": "forge not installed in this environment"}


def test_run_forge_test_exploit_reports_timeout(tmp_path, monkeypatch):
    import subprocess

    def _raise(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["forge"], timeout=5)
    monkeypatch.setattr(subprocess, "run", _raise)
    result = sft.run_forge_test_exploit(str(tmp_path), "https://example-rpc.test", timeout=5)
    assert result["ran"] is True
    assert result["passed"] is False
    assert "timed out after 5s" in result["reason"]


def test_run_forge_test_exploit_reports_pass(tmp_path, monkeypatch):
    import subprocess

    def fake_run(cmd, cwd, capture_output, text, timeout, env):
        assert cmd[:2] == ["forge", "test"]
        assert "--fork-url" in cmd
        assert cmd[cmd.index("--fork-url") + 1] == "https://example-rpc.test"
        return subprocess.CompletedProcess(cmd, 0, stdout="test passed", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = sft.run_forge_test_exploit(str(tmp_path), "https://example-rpc.test")
    assert result == {"ran": True, "passed": True, "returncode": 0, "output": "test passed"}


def test_run_forge_test_exploit_reports_failure(tmp_path, monkeypatch):
    import subprocess

    def fake_run(cmd, cwd, capture_output, text, timeout, env):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="test failed")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = sft.run_forge_test_exploit(str(tmp_path), "https://example-rpc.test")
    assert result == {"ran": True, "passed": False, "returncode": 1, "output": "test failed"}


def test_run_forge_test_exploit_never_passes_real_secrets_to_subprocess(tmp_path, monkeypatch):
    """Confirmed real gap (CodeRabbit, PR #275): forge test previously
    inherited the full CI environment, including every LLM-provider key and
    GITHUB_TOKEN — a malicious verified-source prompt injection could steer
    the LLM-drafted test into reading one via vm.envString and leaking it
    into forge's captured output, which flows straight into a committed,
    public report."""
    import subprocess
    monkeypatch.setenv("XAI_API_KEY_1", "super-secret-key")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_super_secret")
    captured = {}

    def fake_run(cmd, cwd, capture_output, text, timeout, env):
        captured["env"] = env
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")
    monkeypatch.setattr(subprocess, "run", fake_run)
    sft.run_forge_test_exploit(str(tmp_path), "https://example-rpc.test")
    assert "XAI_API_KEY_1" not in captured["env"]
    assert "GITHUB_TOKEN" not in captured["env"]


# ── scaffold_and_run_exploit_poc — orchestration short-circuits ─────────────

def test_scaffold_and_run_exploit_poc_reports_unverified_contract(monkeypatch):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"verified": False, "source_code": None})
    result = sft.scaffold_and_run_exploit_poc("0xdead", rpc_url="https://example-rpc.test")
    assert result == {"ran": False, "reason": "contract unverified or no source available"}


def test_scaffold_and_run_exploit_poc_reports_missing_rpc(monkeypatch):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"verified": True, "source_code": "contract C {}",
                                               "contract_name": "C", "compiler": "v0.8.19"})
    result = sft.scaffold_and_run_exploit_poc("0xdead", rpc_url=None)
    assert result == {"ran": False, "reason": "no known RPC endpoint for chain 8453"}


def test_scaffold_and_run_exploit_poc_reports_source_lookup_error(monkeypatch):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"error": "no api key"})
    result = sft.scaffold_and_run_exploit_poc("0xdead", rpc_url="https://example-rpc.test")
    assert result["ran"] is False
    assert "source lookup failed" in result["reason"]


def test_scaffold_and_run_exploit_poc_stops_when_no_exploit_drafted(monkeypatch, tmp_path):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"verified": True, "source_code": "contract C {}",
                                               "contract_name": "C", "compiler": "v0.8.19"})
    monkeypatch.setattr(sft, "run_forge_build", lambda project_dir, timeout=180: {"ok": True, "output": ""})
    monkeypatch.setattr(sft, "draft_exploit_test",
                         lambda files, name, address, extra_context="": (None, "no exploit found: nothing concrete"))
    result = sft.scaffold_and_run_exploit_poc(
        "0xdead", rpc_url="https://example-rpc.test", workdir=str(tmp_path))
    assert result["ran"] is False
    assert result["reason"] == "no exploit found: nothing concrete"
    assert result["project_dir"] == str(tmp_path)


def test_scaffold_and_run_exploit_poc_runs_full_pipeline_on_success(monkeypatch, tmp_path):
    monkeypatch.setattr(sft.DF, "get_contract_source",
                         lambda addr, chain: {"verified": True, "source_code": "contract C {}",
                                               "contract_name": "C", "compiler": "v0.8.19"})
    monkeypatch.setattr(sft, "run_forge_build", lambda project_dir, timeout=180: {"ok": True, "output": ""})
    monkeypatch.setattr(sft, "draft_exploit_test",
                         lambda files, name, address, extra_context="": ("contract Exploit {}", "grok"))
    monkeypatch.setattr(sft, "run_forge_test_exploit",
                         lambda project_dir, fork_url, timeout=300: {"ran": True, "passed": True, "returncode": 0, "output": "ok"})
    result = sft.scaffold_and_run_exploit_poc(
        "0xdead", rpc_url="https://example-rpc.test", workdir=str(tmp_path))
    assert result["ran"] is True
    assert result["drafted_by"] == "grok"
    assert result["drafted_code"] == "contract Exploit {}"
    assert result["test_result"]["passed"] is True
    assert (tmp_path / "test" / "Exploit.t.sol").read_text() == "contract Exploit {}"
