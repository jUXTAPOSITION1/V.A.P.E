#!/usr/bin/env python3
"""
Scaffolds a throwaway Foundry project from a real on-chain contract's
verified source, so Halmos (and Echidna/forge fuzzing) — which need a
compiled project with real test/property functions, unlike Slither's
address-based mode — have something concrete to run against.

Extends agents/deep_dive_audit.py's existing Slither-only static analysis
with a second, independent layer: bounded symbolic testing. Real, no
fabrication end to end except one deliberate exception, clearly marked:

  1. Source: the target's own verified source via
     data_fetchers.get_contract_source() (Etherscan V2) — byte for byte,
     nothing invented. Unverified contracts are reported as such, not
     silently skipped.
  2. Scaffold + compile: real forge build against that real source. If it
     doesn't compile, that's reported honestly as a real failure, not
     papered over.
  3. Properties: THIS is the one LLM-generated piece — there's no way to
     derive candidate Halmos check_* invariants from source-parsing alone.
     Labeled plainly as hypotheses to test, never as findings. Whether they
     even compile, and whether Halmos actually holds them, is what turns
     them into a real signal — not the drafting itself.
  4. Analysis: a real `halmos` run against the drafted properties.

Needs ETHERSCAN_API_KEY and a real `forge`/`halmos` on PATH. This sandbox's
egress proxy blocks GitHub release-binary downloads (Foundry ships as a
release tarball, not a pip package like Halmos), so the actual forge build +
halmos run can only be smoke-tested on a normal GitHub Actions runner or the
training GPU box — the parsing/scaffolding logic below is what
tests/test_scaffold_foundry_target.py covers hermetically.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from agents import data_fetchers as DF
    from agents.llm import ask_oci_grok_frontier
except Exception:
    import data_fetchers as DF
    from llm import ask_oci_grok_frontier

FOUNDRY_TOML_TEMPLATE = """[profile.default]
src = "src"
test = "test"
out = "out"
libs = ["lib"]
solc_version = "{solc_version}"
"""
# Deliberately no `ffi = true` and no `fs_permissions` entry above — Foundry
# denies both the ffi and filesystem cheatcodes by default unless a profile
# explicitly opts in. This project scaffolds and RUNS an LLM-drafted exploit
# test (run_forge_test_exploit() below) against a real contract's real
# verified source, which is attacker-controlled input (anyone can deploy a
# contract with a prompt-injection payload embedded in its source comments,
# hoping to steer the draft into exfiltrating something) — never opt into
# either cheatcode class here.

# Environment-variable read cheatcodes (vm.envString/vm.envUint/etc.) are
# NOT gated by a foundry.toml flag the way ffi/fs are — they always work,
# reading the real OS process environment of whatever ran `forge test`. See
# _forge_subprocess_env() below for why that subprocess never gets a real
# secret to read in the first place, rather than trying to scrub one out of
# forge's output after the fact.

HALMOS_DRAFT_SYSTEM = """You are VAPE, drafting HYPOTHESES for symbolic testing — not
findings. Given a real, verified smart contract's source, write 2-4 Halmos
symbolic test functions (Solidity, in a contract extending forge-std's Test,
each named check_<name>_<behavior>(...) per Halmos's own naming convention)
that test concrete, checkable invariants you can see directly in the given
code — access control on a privileged function, balance/supply conservation
across a transfer, a state invariant that should never flip. Never invent a
function, storage variable, or behavior the source doesn't actually show.
If nothing concrete stands out, write a short comment saying so instead of
padding with a generic template. Output ONLY the Solidity file contents
(starting with '// SPDX-License-Identifier' and a pragma line) — no prose
outside the code."""

EXPLOIT_DRAFT_SYSTEM = """You are VAPE, drafting a REAL, EXECUTABLE proof-of-concept
exploit test for a live bug-bounty submission — this is the primary deliverable of a
paid bounty-audit engagement, not a hypothesis exercise.

Given a real, verified smart contract's source (already deployed on-chain at a known
address) and any static/symbolic-analysis findings already surfaced, write ONE Foundry
test contract (Solidity, extending forge-std's Test) that:
- Targets the real deployed contract directly at its actual address (declare
  `address constant TARGET = <the given address>;` and wrap it with the real
  interface/contract type from the given source) — the test runner supplies
  `--fork-url` for the whole run, so real on-chain state is already live; you do not
  need vm.createSelectFork() yourself.
- Contains exactly one test function, test_exploit_<short_name>(), that attempts to
  concretely exploit a real vulnerability you can point to in the given source —
  drain funds, bypass access control, manipulate a price/oracle read, break an
  invariant, etc. Use only real function signatures from the given source — never
  invent an interface member that isn't shown.
- Asserts the exploit's actual impact directly (e.g. attacker balance increased,
  protocol balance decreased, a should-be-guarded state changed) so a passing test IS
  the proof of impact, not a placeholder assertion.
- If, after actually reasoning through the code, you find no concretely exploitable
  path (this is a legitimate, honest outcome — most audited contracts are not
  exploitable), output NO Solidity code at all: just the single line
  `NO_EXPLOIT_FOUND: <one-sentence reason>` — never pad with a fake or trivial
  "exploit" just to produce code.

Never fabricate a function, storage layout, or balance that the given source doesn't
actually show. Output ONLY the Solidity file contents (starting with
'// SPDX-License-Identifier' and a pragma line) or the single NO_EXPLOIT_FOUND line —
no prose outside of that."""


def _sanitize_path(path):
    """Strips leading slashes/parent-dir segments from an Etherscan-supplied
    file path before it's used to write a file — cheap insurance against a
    malformed path escaping the scaffold directory, not a claim that
    Etherscan's own verified source is adversarial."""
    path = path.replace("\\", "/").lstrip("/")
    parts = [p for p in path.split("/") if p not in ("", ".", "..")]
    return "/".join(parts) or "Unknown.sol"


def parse_verified_source(source_code, contract_name):
    """Turns Etherscan's raw SourceCode field into {relpath: content}.
    Handles both a plain single-file source and Etherscan's own
    double-brace-wrapped Standard JSON Input multi-file format. Never
    fabricates a file — unparseable input returns {} so the caller reports
    a real "could not parse" failure instead of scaffolding garbage."""
    if not source_code:
        return {}
    text = source_code.strip()
    if text.startswith("{{") and text.endswith("}}"):
        # Etherscan's own quirk: wraps Standard JSON Input in one extra pair
        # of braces versus solc --standard-json's real shape.
        text = text[1:-1]
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except (ValueError, TypeError):
            return {}
        sources = parsed.get("sources")
        if not isinstance(sources, dict):
            return {}
        out = {}
        for path, entry in sources.items():
            content = entry.get("content") if isinstance(entry, dict) else None
            if content:
                out[_sanitize_path(path)] = content
        return out
    name = contract_name or "Contract"
    return {f"{name}.sol": source_code}


def _compiler_to_solc_version(compiler):
    """Etherscan's CompilerVersion looks like 'v0.8.19+commit.7dd6d404' —
    Foundry's solc_version wants just '0.8.19'. Falls back to a documented
    default (not a silent guess presented as fact) when unparseable."""
    if compiler:
        m = re.match(r"v?(\d+\.\d+\.\d+)", compiler)
        if m:
            return m.group(1)
    return "0.8.19"


def scaffold_project(files, compiler_version, out_dir):
    """Writes verified source into out_dir/src/ plus a minimal foundry.toml.
    An empty `files` dict still scaffolds a valid (source-less) project —
    the next real step (forge build) is what honestly fails on that, rather
    than this function silently declaring success on nothing."""
    src_dir = os.path.join(out_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "test"), exist_ok=True)
    for relpath, content in files.items():
        full = os.path.join(src_dir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    with open(os.path.join(out_dir, "foundry.toml"), "w", encoding="utf-8") as f:
        f.write(FOUNDRY_TOML_TEMPLATE.format(solc_version=_compiler_to_solc_version(compiler_version)))
    return out_dir


def run_forge_build(project_dir, timeout=180):
    try:
        p = subprocess.run(["forge", "build"], cwd=project_dir, capture_output=True,
                           text=True, timeout=timeout)
        return {"ok": p.returncode == 0, "output": (p.stdout + p.stderr)[-3000:]}
    except FileNotFoundError:
        return {"ok": False, "output": "forge not installed in this environment"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": f"forge build timed out after {timeout}s"}


def draft_symbolic_properties(files, contract_name):
    """Real check #3 (see module docstring): the one LLM-generated piece.
    Returns (code_or_none, provider_or_reason). Uses ask_oci_grok_frontier()
    (OCI Grok 4.3 primary, matching agents/scaffold_move_target.py's sibling
    draft function and the rest of VAPE's report-generation surface) rather
    than a bare ask_frontier() call — real, previously-live inconsistency
    fixed 2026-07-25: this was the one drafting step in the bounty-audit
    pipeline still bypassing OCI Grok entirely."""
    source_excerpt = "\n\n".join(f"// {path}\n{content}" for path, content in list(files.items())[:5])[:20000]
    user = f"Contract: {contract_name or 'unknown'}\n\n{source_excerpt}"
    try:
        code, provider = ask_oci_grok_frontier(HALMOS_DRAFT_SYSTEM, user, max_tokens=2000, temperature=0.2)
    except Exception as e:
        return None, f"LLM unavailable: {e}"
    match = re.search(r"```(?:solidity)?\n(.*?)```", code, re.DOTALL)
    if match:
        code = match.group(1)
    return code.strip(), provider


def run_halmos(project_dir, timeout=600):
    try:
        p = subprocess.run(["halmos"], cwd=project_dir, capture_output=True, text=True, timeout=timeout)
        return {"ran": True, "returncode": p.returncode, "output": (p.stdout + p.stderr)[-5000:]}
    except FileNotFoundError:
        return {"ran": False, "reason": "halmos not installed in this environment"}
    except subprocess.TimeoutExpired:
        return {"ran": True, "returncode": None, "output": f"halmos timed out after {timeout}s"}


def draft_exploit_test(files, contract_name, address, extra_context=""):
    """The one LLM-generated piece of the exploit-PoC pipeline (mirrors
    draft_symbolic_properties()'s own role for Halmos). Returns
    (code_or_none, provider_or_reason) — `code` is None both when the LLM is
    unavailable AND when it honestly found no exploitable path, so callers
    must inspect the reason string to tell those two apart if needed. Uses
    ask_oci_grok_frontier() — see draft_symbolic_properties()'s docstring
    for why (OCI Grok primary, matching the rest of this offering's report
    generation, not a bare frontier-chain call)."""
    source_excerpt = "\n\n".join(f"// {path}\n{content}" for path, content in list(files.items())[:5])[:20000]
    user = f"ADDRESS: {address}\nContract: {contract_name or 'unknown'}\n\n{source_excerpt}"
    if extra_context:
        user += f"\n\n=== PRIOR STATIC/SYMBOLIC ANALYSIS (context only, not verified findings) ===\n{extra_context[:3000]}"
    try:
        code, provider = ask_oci_grok_frontier(EXPLOIT_DRAFT_SYSTEM, user, max_tokens=2500, temperature=0.2)
    except Exception as e:
        return None, f"LLM unavailable: {e}"
    if "NO_EXPLOIT_FOUND" in code:
        m = re.search(r"NO_EXPLOIT_FOUND:\s*(.+)", code)
        return None, "no exploit found: " + (m.group(1).strip() if m else "no reason given")
    match = re.search(r"```(?:solidity)?\n(.*?)```", code, re.DOTALL)
    if match:
        code = match.group(1)
    return code.strip(), provider


def _forge_subprocess_env():
    """A minimal environment for running the LLM-drafted exploit test — NOT
    the full inherited os.environ. The test contract is Solidity generated
    from a real target contract's verified source (attacker-controlled: any
    address's own Etherscan-verified source can carry a prompt-injection
    payload in its comments, aimed at getting the draft to embed something
    like vm.envString("SOME_SECRET")), and Foundry's env-read cheatcodes
    (unlike ffi/fs, see FOUNDRY_TOML_TEMPLATE's comment) aren't gated by any
    config flag — they just read whatever's really in the process
    environment. This CI job's real environment holds every LLM-provider key
    plus GITHUB_TOKEN (.github/workflows/deep-dive-bounty.yml's `env:`
    block); forge's captured stdout/stderr becomes part of `test_result`,
    which flows straight into the audit report this same job commits to a
    PUBLIC repo. Passing a bare, secret-free environment closes that
    exfiltration path at the source, rather than trying to regex-scrub a
    secret back out of forge's output after the fact once it may already be
    committed to git history. PATH/HOME (needed for forge/solc to run at
    all) are the only two carried over unconditionally, plus whichever of
    TMPDIR/TEMP/TERM/LANG happen to be set (harmless, not secrets, and
    occasionally needed by a toolchain's own temp-file or locale handling)."""
    safe_keys = ("PATH", "HOME", "TMPDIR", "TEMP", "TERM", "LANG")
    return {k: os.environ[k] for k in safe_keys if k in os.environ}


def run_forge_test_exploit(project_dir, fork_url, timeout=300):
    """Actually RUNS the drafted exploit test against the real chain's forked
    state — `--fork-url` forks for the whole test run, entirely local and
    read-only against the real chain (no transaction is ever broadcast to
    it), matching VAPE's white-hat-only principle. A passing test (rc 0)
    means the drafted attack's own assertions held after its actions ran —
    real, concrete impact evidence, not a narrative claim. Runs with a
    secret-free environment (_forge_subprocess_env()) — see that function's
    docstring for why."""
    try:
        p = subprocess.run(
            ["forge", "test", "--match-path", "test/Exploit.t.sol", "--fork-url", fork_url, "-vvv"],
            cwd=project_dir, capture_output=True, text=True, timeout=timeout,
            env=_forge_subprocess_env(),
        )
        return {"ran": True, "passed": p.returncode == 0, "returncode": p.returncode,
                "output": (p.stdout + p.stderr)[-6000:]}
    except FileNotFoundError:
        return {"ran": False, "reason": "forge not installed in this environment"}
    except subprocess.TimeoutExpired:
        return {"ran": True, "passed": False, "returncode": None,
                "reason": f"forge test timed out after {timeout}s"}


def scaffold_and_run_exploit_poc(address, chain_id=8453, rpc_url=None, workdir=None,
                                  pre_fetched_src=None, extra_context=""):
    """The primary deliverable of a paid bounty-audit engagement: a REAL,
    forge-executed exploit proof-of-concept run against the target's actual
    forked on-chain state — not a narrative-only description. Never raises to
    its caller (mirrors scaffold_and_analyze()'s own honest-failure
    convention); every stage failure is a real, reported reason.

    `workdir`, when given an already-scaffolded project_dir (e.g. from a
    prior scaffold_and_analyze() call for the same address in the same run),
    reuses it instead of scaffolding + building a second throwaway project —
    scaffold_project()'s file writes are idempotent so this is safe even if
    that prior project already has its own Symbolic.t.sol test file sitting
    alongside the new Exploit.t.sol this writes."""
    src = pre_fetched_src if pre_fetched_src is not None else DF.get_contract_source(address, chain_id)
    if not isinstance(src, dict) or src.get("error"):
        reason = src.get("error") if isinstance(src, dict) else str(src)
        return {"ran": False, "reason": f"source lookup failed: {reason}"}
    if not src.get("verified") or not src.get("source_code"):
        return {"ran": False, "reason": "contract unverified or no source available"}
    if not rpc_url:
        return {"ran": False, "reason": f"no known RPC endpoint for chain {chain_id}"}

    files = parse_verified_source(src["source_code"], src.get("contract_name"))
    if not files:
        return {"ran": False, "reason": "verified source could not be parsed into any file"}

    out_dir = workdir or tempfile.mkdtemp(prefix="vape-foundry-exploit-")
    scaffold_project(files, src.get("compiler"), out_dir)

    build = run_forge_build(out_dir)
    if not build["ok"]:
        return {"ran": False, "reason": "scaffolded project does not compile",
                "forge_output": build["output"], "project_dir": out_dir}

    code, provider = draft_exploit_test(files, src.get("contract_name"), address, extra_context)
    if not code:
        return {"ran": False, "reason": provider or "no exploit drafted", "project_dir": out_dir}

    with open(os.path.join(out_dir, "test", "Exploit.t.sol"), "w", encoding="utf-8") as f:
        f.write(code)

    build2 = run_forge_build(out_dir)
    if not build2["ok"]:
        return {"ran": False, "reason": "LLM-drafted exploit test failed to compile",
                "drafted_code": code, "forge_output": build2["output"], "project_dir": out_dir}

    test_result = run_forge_test_exploit(out_dir, rpc_url)
    return {"ran": True, "project_dir": out_dir, "drafted_by": provider,
            "drafted_code": code, "test_result": test_result}


def scaffold_and_analyze(address, chain_id=8453, workdir=None, pre_fetched_src=None):
    """Orchestrates the full pipeline. Never raises to its caller — every
    stage failure is a real, reported reason (matching every other agent's
    "a tool outage must never sink the caller" convention), not an
    exception the audit script would have to guard against separately.

    pre_fetched_src lets a caller that already called get_contract_source()
    for its own purposes (e.g. deep_dive_audit.py, which needs it for the
    frontier-LLM prompt regardless of whether symbolic testing runs) pass
    that result through instead of hitting Etherscan a second time."""
    src = pre_fetched_src if pre_fetched_src is not None else DF.get_contract_source(address, chain_id)
    if not isinstance(src, dict) or src.get("error"):
        reason = src.get("error") if isinstance(src, dict) else str(src)
        return {"ran": False, "reason": f"source lookup failed: {reason}"}
    if not src.get("verified") or not src.get("source_code"):
        return {"ran": False, "reason": "contract unverified or no source available"}

    files = parse_verified_source(src["source_code"], src.get("contract_name"))
    if not files:
        return {"ran": False, "reason": "verified source could not be parsed into any file"}

    out_dir = workdir or tempfile.mkdtemp(prefix="vape-foundry-scaffold-")
    scaffold_project(files, src.get("compiler"), out_dir)

    build = run_forge_build(out_dir)
    if not build["ok"]:
        return {"ran": False, "reason": "scaffolded project does not compile",
                "forge_output": build["output"], "project_dir": out_dir}

    code, provider = draft_symbolic_properties(files, src.get("contract_name"))
    if not code:
        return {"ran": False, "reason": provider or "no properties drafted", "project_dir": out_dir}

    with open(os.path.join(out_dir, "test", "Symbolic.t.sol"), "w", encoding="utf-8") as f:
        f.write(code)

    build2 = run_forge_build(out_dir)
    if not build2["ok"]:
        return {"ran": False, "reason": "LLM-drafted properties failed to compile",
                "drafted_code": code, "forge_output": build2["output"], "project_dir": out_dir}

    halmos_result = run_halmos(out_dir)
    return {"ran": True, "project_dir": out_dir, "drafted_by": provider,
            "drafted_code": code, "halmos": halmos_result}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Scaffold a Foundry project from a verified contract and run Halmos.")
    ap.add_argument("address")
    ap.add_argument("--chain", type=int, default=8453)
    args = ap.parse_args()
    print(json.dumps(scaffold_and_analyze(args.address, args.chain), indent=2, default=str))
