#!/usr/bin/env python3
"""
Scaffolds a real local Move package from an external repo's already-fetched
source (agents/external_audit.py) so sui-prover — which needs a real
Move.toml-rooted package directory, not loose in-memory files — has
something concrete to run formal verification against.

Extends agents/external_audit.py's frontier-LLM-only review with a second,
independent layer for Move targets: bounded formal verification. Real, no
fabrication end to end except one deliberate exception, clearly marked —
same discipline as agents/scaffold_foundry_target.py's Halmos pipeline for
Solidity, which this mirrors:

  1. Source: the exact files agents/external_audit.py already fetched byte
     for byte from raw.githubusercontent.com (including the target's own
     real Move.toml, fetched the same way — never synthesized) — nothing
     invented.
  2. Scaffold: writes those files into a real directory tree under
     sources/, using each file's real relative path, plus the target's own
     real Move.toml written back unmodified.
  3. Specs: THIS is the one LLM-generated piece. Move Prover only proves
     properties actually written in Move's spec language (MSL) — a real
     target repo with zero existing `spec` blocks (Momentum's mmt-v3-core,
     confirmed by inspection, is exactly this case) gives sui-prover nothing
     to check beyond generic default-abort framework analysis. A frontier
     LLM drafts candidate `spec` blocks (aborts_if/ensures) for a handful of
     the most security-relevant functions already identified in the
     narrative review, labeled plainly as HYPOTHESES to check, never as
     established findings — mirrors scaffold_foundry_target.py's Halmos
     check_* drafting step exactly.
  4. Prove: a real `sui-prover` run against the scaffolded package + the
     drafted spec module.

Needs `sui-prover` on PATH. Deliberately NOT auto-installed by any workflow
in this repo: as of this module's writing, asymptotic-code/sui-prover
publishes no Linux release artifact (macOS Homebrew only) and depends on
the Boogie verification engine + Z3 SMT solver — a from-source build in CI
would be multi-minute and fragile, unlike this repo's other best-effort
tools (Slither/Mythril/Aderyn/Halmos), which all install in well under a
minute via pip/a release binary. A real live-verified run needs a runner
with sui-prover pre-installed (a dedicated one-time setup, same pattern as
the LoRA fine-tuning GPU box) — this sandbox's own egress policy also
blocks the hosts needed to attempt that install here. The scaffolding/
prompt-construction/output-parsing logic below is what
tests/test_scaffold_move_target.py covers hermetically; report any real
compile/prove failure honestly rather than papering over it, exactly like
scaffold_foundry_target.py's forge-build step.
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
    from agents.llm import ask_oci_grok_frontier
except Exception:
    from llm import ask_oci_grok_frontier

MOVE_SPEC_DRAFT_SYSTEM = """You are VAPE, drafting HYPOTHESES for Move Prover formal
verification — not findings. Given real, verified Move source from a security review
already in progress, write 2-4 Move specification blocks (MSL: `spec module { ... }` or
per-function `spec fun_name { aborts_if ...; ensures ...; }`) that formally state concrete,
checkable properties you can see directly in the given code — an invariant that should
never be violated (e.g. a resource-conservation property, an access-control precondition,
a bound on an arithmetic result), stated as `aborts_if`/`ensures`/`requires` clauses.
Reference only modules, functions, and fields that actually appear in the given source —
never invent one. If nothing concrete stands out, write a short comment saying so instead
of padding with a generic template. Output ONLY the Move spec module's file contents
(starting with the real `module` declaration this spec targets, e.g.
`spec mmt_v3::trade { ... }`) — no prose outside the code, no markdown fences."""


def write_move_toml(out_dir, move_toml_content):
    """Writes the target's own real, already-fetched Move.toml unmodified —
    never a synthesized one, since Sui's dependency-resolution details
    (framework versions, published-at addresses) are exactly the kind of
    thing worth getting from the real source, not guessing."""
    with open(os.path.join(out_dir, "Move.toml"), "w", encoding="utf-8") as f:
        f.write(move_toml_content)


def scaffold_package(files, move_toml_content, out_dir):
    """Writes each already-fetched {relpath: content} pair into out_dir at
    its real relative path (relpath is expected to start with the package
    root, e.g. "sources/actions/trade.move"), plus the real Move.toml. An
    empty `files` dict still scaffolds a valid (source-less) package — the
    next real step (sui-prover itself) is what honestly fails on that,
    rather than this function silently declaring success on nothing."""
    for relpath, content in files.items():
        full = os.path.join(out_dir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
    write_move_toml(out_dir, move_toml_content)
    return out_dir


def draft_move_specs(files, focus_note=""):
    """Real step #3 (see module docstring): the one LLM-generated piece.
    Returns (code_or_none, provider_or_reason)."""
    source_excerpt = "\n\n".join(f"// {path}\n{content}" for path, content in list(files.items())[:6])[:24000]
    user = f"{focus_note}\n\n{source_excerpt}" if focus_note else source_excerpt
    try:
        code, provider = ask_oci_grok_frontier(MOVE_SPEC_DRAFT_SYSTEM, user, max_tokens=2000, temperature=0.2)
    except Exception as e:
        return None, f"LLM unavailable: {e}"
    match = re.search(r"```(?:move)?\n(.*?)```", code, re.DOTALL)
    if match:
        code = match.group(1)
    return code.strip(), provider


def run_sui_prover(project_dir, timeout=300):
    """Real `sui-prover` run against the scaffolded package. Never a hard
    dependency (see module docstring for why this isn't auto-installed) —
    returns a clean {"ran": False, ...} if it isn't on PATH this run."""
    import shutil
    if not shutil.which("sui-prover"):
        return {"ran": False, "reason": "sui-prover not installed in this environment this run "
                                         "(no Linux release published; needs a from-source build "
                                         "with Boogie + Z3 — see module docstring)"}
    try:
        p = subprocess.run(["sui-prover"], cwd=project_dir, capture_output=True, text=True, timeout=timeout)
        return {"ran": True, "returncode": p.returncode, "output": (p.stdout + p.stderr)[-5000:]}
    except subprocess.TimeoutExpired:
        return {"ran": True, "returncode": None, "output": f"sui-prover timed out after {timeout}s"}
    except Exception as e:
        return {"ran": False, "reason": str(e)}


def scaffold_and_prove(files, move_toml_content, workdir=None, focus_note=""):
    """Orchestrates the full pipeline. Never raises to its caller — every
    stage failure is a real, reported reason, matching every other agent's
    "a tool outage must never sink the caller" convention."""
    if not move_toml_content:
        return {"ran": False, "reason": "no Move.toml available — cannot scaffold a real package"}
    if not files:
        return {"ran": False, "reason": "no source files available to scaffold"}

    out_dir = workdir or tempfile.mkdtemp(prefix="vape-move-scaffold-")
    scaffold_package(files, move_toml_content, out_dir)

    code, provider = draft_move_specs(files, focus_note)
    if not code:
        return {"ran": False, "reason": provider or "no spec properties drafted", "project_dir": out_dir}

    spec_path = os.path.join(out_dir, "sources", "vape_prover_specs.move")
    os.makedirs(os.path.dirname(spec_path), exist_ok=True)
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(code)

    prover_result = run_sui_prover(out_dir)
    return {"ran": prover_result.get("ran", False), "project_dir": out_dir, "drafted_by": provider,
            "drafted_code": code, "prover": prover_result}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Scaffold a Move package from fetched source and run sui-prover.")
    ap.add_argument("--files-json", required=True, help="path to a JSON file: {relpath: content}")
    ap.add_argument("--move-toml", required=True, help="path to the real Move.toml file")
    args = ap.parse_args()
    with open(args.files_json) as f:
        files = json.load(f)
    with open(args.move_toml) as f:
        move_toml_content = f.read()
    print(json.dumps(scaffold_and_prove(files, move_toml_content), indent=2, default=str))
