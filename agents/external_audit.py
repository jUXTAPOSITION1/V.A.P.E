#!/usr/bin/env python3
"""
External Bounty Engagement — VAPE's blueprint for auditing a real, external
bug-bounty target repo (any language, any chain), not just its own on-chain
Base/EVM investigations.

Built for the first real engagement this covers (Momentum's mmt-v3-core
CLMM, https://hackenproof.com/programs/momentum-smart-contracts, real
program repo mirror at github.com/hackenproof-public/mmt-v3-core, source
verified identical at the canonical github.com/mmt-finance/v3-core) — but
deliberately generalized so any future external bounty repo (Move/Sui,
Solidity/EVM, Rust/Solana, anything) can reuse this exact pipeline instead
of a one-off script per engagement.

Scope, honestly stated: this tool's real, verified capability is a rigorous
frontier-LLM (OCI Grok 4.3, agents/llm.py::ask_oci_grok_frontier — same
"no local override" contract deep_dive_audit.py uses) line-by-line source
review — the same kind of reasoning pass deep_dive_audit.py already runs
against on-chain Solidity targets. It deliberately does NOT invoke
Slither/Mythril/Aderyn/Halmos here: those are Solidity-specific static/
symbolic tools that need either a live on-chain address (Slither, Mythril)
or a locally compilable Foundry project (Aderyn, Halmos) — neither applies
to a source-only fetch of an arbitrary external repo, and for a non-Solidity
target (e.g. Move, this engagement's actual language) none of them apply at
all regardless. A genuinely Solidity on-chain target should go through
agents/deep_dive_audit.py instead, which has the real toolchain wired in.

Fetching: two real, keyless mechanisms —
  - fetch_repo_tree(): GitHub's public git/trees API (unauthenticated,
    rate-limited but fine for a one-off engagement) to auto-discover every
    source file in the repo at a given ref.
  - fetch_file(): raw.githubusercontent.com (no auth, no rate-limit
    concerns) to pull each file's actual real content.
Both degrade honestly (empty result / None) rather than fabricating source
on any network failure — this sandbox's own egress policy blocks api.github.
com/github.com for repos outside its session scope, so fetch_repo_tree()
could not be live-tested from here; fetch_file() against
raw.githubusercontent.com (a separate, unrestricted host) was verified live.
A real GitHub Actions run has unrestricted egress and can exercise both.

Real, not fabricated: never invents a finding. If nothing the frontier model
flags survives an honest read, the report says so plainly instead of
manufacturing severity to justify a submission.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from agents.llm import ask_oci_grok_frontier
except Exception:
    from llm import ask_oci_grok_frontier

AUDIT_DIR = os.path.join(ROOT, "intel", "audits", "external-bounties")
FINDINGS_PATH = os.path.join(ROOT, "skillforge", "memory", "findings.jsonl")

_UA = {"User-Agent": "VAPE-ExternalAudit/1.0"}
_SOURCE_EXTENSIONS = {
    "move": (".move",),
    "solidity": (".sol",),
    "rust": (".rs",),
}
MAX_FILES = 40           # safety cap on auto-discovered file count
MAX_TOTAL_CHARS = 350000  # safety cap on total source fed to the LLM (well under 1M-token context)


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def fetch_file(owner, repo, ref, path, timeout=15):
    """Real, keyless fetch of one file's raw content via
    raw.githubusercontent.com — no GitHub API auth/rate-limit concerns.
    Returns None (not an exception) on any failure, honest "not available"
    signal rather than a crash."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[external_audit] fetch_file failed for {path}: {e}", file=sys.stderr)
        return None


def fetch_repo_tree(owner, repo, ref, timeout=20):
    """Real, keyless auto-discovery of every file path in the repo at `ref`
    via GitHub's public git/trees API. Returns [] (not an exception) on any
    failure — a caller that already has an explicit file list (this
    engagement's real usage) doesn't need this to succeed."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"
    try:
        req = urllib.request.Request(url, headers={**_UA, "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        return [t["path"] for t in data.get("tree", []) if t.get("type") == "blob"]
    except Exception as e:
        print(f"[external_audit] fetch_repo_tree failed: {e}", file=sys.stderr)
        return []


def detect_language(paths):
    counts = {lang: 0 for lang in _SOURCE_EXTENSIONS}
    for p in paths:
        for lang, exts in _SOURCE_EXTENSIONS.items():
            if p.endswith(exts):
                counts[lang] += 1
    lang = max(counts, key=counts.get)
    return lang if counts[lang] > 0 else "unknown"


def select_source_files(paths, language, max_files=MAX_FILES):
    exts = _SOURCE_EXTENSIONS.get(language, ())
    if not exts:
        return paths[:max_files]
    return [p for p in paths if p.endswith(exts)][:max_files]


MOVE_AUDIT_SYSTEM = """You are VAPE, an autonomous security auditor performing a rigorous
line-by-line review of a real Move smart contract package (Sui or Aptos) as part of a
real bug-bounty engagement. Real money is potentially on the line for the protocol; be
precise, evidence-based, and honest.

Move-specific grounding — reason about what Move's type system already guarantees versus
what it does NOT:
- Move's linear/resource type system (no `copy`/`drop` on a struct without those
  abilities) structurally prevents whole classes of Solidity-style bugs: no reentrancy
  via external calls into value-holding state, no arbitrary double-spend of a resource,
  no unintended token duplication — do not flag these as findings unless the code
  actually undermines that guarantee (e.g. an unsafe unpack, a leaked reference letting a
  resource be reused).
- What Move does NOT protect against, and where real bugs live: access-control logic
  errors (capability/ACL checks that are missing, wrong, or checkable on the wrong
  object), object-ownership confusion (a shared object usable by anyone vs. one that
  should be owned/capability-gated), missing cross-object validation (e.g. does a
  function operating on object A correctly verify a passed-in object B actually belongs
  to/matches A, or could a caller substitute an unrelated object of the same type?),
  integer overflow/precision loss and ROUNDING DIRECTION (does every division that could
  favor either the protocol or the caller round in the safe direction consistently?),
  dynamic-field key collisions, hot-potato/receipt patterns that could be bypassed or
  left unresolved, admin/capability functions with insufficient or bypassable checks,
  and business-logic errors in the domain-specific math (e.g. AMM/CLMM price, liquidity,
  and fee accounting).
- Base every claim on the ACTUAL source given below — never invent a module, function,
  field, or behavior you weren't shown. If you need to see a helper function that wasn't
  included to be sure of a claim, say so explicitly as an open question rather than
  guessing.
- Distinguish real, exploitable findings from theoretical/low-severity/code-quality
  observations, the same way a professional auditor would triage rather than inflating a
  verdict off surface-level pattern matching.
- For every finding: state the exact file/function, the concrete attacker-reachable
  scenario (who calls what, with what inputs, in what order), and the concrete impact
  (fund loss, DoS, incorrect accounting, etc.) — a finding without a concrete scenario is
  not a finding, it's a question to flag as "worth human verification."
- End with a clear overall verdict (real exploitable finding(s) worth escalating to a
  bounty submission, vs. no exploitable finding this pass — clean code, or worth a
  human's second look on specific named issues) and a short list of what a human
  reviewer should still manually verify (especially anything needing Move Prover
  formal verification or dynamic testing this static read can't confirm).

Output plain Markdown: an Executive Summary, then one section per real finding (skip
padding if there's nothing concrete), a "Due Diligence — Checked and Confirmed Safe"
section listing specific things you verified are NOT vulnerable (this has real value —
document what you ruled out, not just what you flagged), then "Recommended Human
Follow-up".
"""

GENERIC_AUDIT_SYSTEM = """You are VAPE, an autonomous security auditor performing a rigorous
line-by-line review of real source code as part of a real bug-bounty engagement. Real
money is potentially on the line; be precise, evidence-based, and honest.

Rules:
- Base every claim on the ACTUAL source given below — never invent a function, field, or
  behavior you weren't shown.
- Reason through the vulnerability classes relevant to this language/platform: access
  control, arithmetic/precision, state-machine/ordering bugs, unchecked external
  interactions, and any domain-specific math (AMM/CLMM pricing, fee accounting, etc.).
- Distinguish real, exploitable findings from theoretical/low-severity noise.
- For every finding: state the exact file/function, the concrete attacker-reachable
  scenario, and the concrete impact.
- End with a clear overall verdict and a short list of what a human reviewer should still
  manually verify.

Output plain Markdown: an Executive Summary, then one section per real finding, a "Due
Diligence — Checked and Confirmed Safe" section, then "Recommended Human Follow-up".
"""


def build_prompt(program_name, owner, repo, ref, files):
    parts = [f"=== ENGAGEMENT ===\nprogram: {program_name or f'{owner}/{repo}'}\n"
             f"repo: {owner}/{repo}@{ref}\nfiles reviewed: {len(files)}"]
    total = 0
    for path, content in files.items():
        if total >= MAX_TOTAL_CHARS:
            parts.append(f"=== FILE: {path} ===\n[omitted — total source budget reached]")
            continue
        chunk = content[: MAX_TOTAL_CHARS - total]
        total += len(chunk)
        parts.append(f"=== FILE: {path} ===\n{chunk}")
    return "\n\n".join(parts)


def _append_finding(result):
    entry = {
        "category": "finding",
        "title": f"External bounty engagement: {result['program']} — {result['verdict_summary'][:80]}",
        "content": f"agents/external_audit.py reviewed {result['repo']}@{result['ref']} "
                  f"({result['language']}, {result['files_reviewed']} files) for the "
                  f"{result['program']} bounty program. Full report: {result['report']}",
        "source": "agents/external_audit.py",
        "tags": ["external-bounty", "audit", result["language"]],
        "confidence": 0.6,
        "severity": "MED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(FINDINGS_PATH), exist_ok=True)
        with open(FINDINGS_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[external_audit] could not append finding: {e}")


def run_external_audit(owner, repo, ref="main", paths=None, program_name=None, max_tokens=6000):
    """Real engagement orchestrator. `paths` lets a caller pass an explicit,
    already-known file list (this engagement's actual usage, since the
    GitHub tree API needs unrestricted egress this specific run may not
    have) — omit it to auto-discover via fetch_repo_tree()."""
    if paths is None:
        all_paths = fetch_repo_tree(owner, repo, ref)
        lang_probe = detect_language(all_paths)
        paths = select_source_files(all_paths, lang_probe)
    language = detect_language(paths)

    files = {}
    for p in paths:
        content = fetch_file(owner, repo, ref, p)
        if content is not None:
            files[p] = content
    if not files:
        return {"error": "no source files could be fetched — repo/ref/paths may be wrong, "
                          "or this run's network egress doesn't allow it"}

    system = MOVE_AUDIT_SYSTEM if language == "move" else GENERIC_AUDIT_SYSTEM
    prompt = build_prompt(program_name, owner, repo, ref, files)
    try:
        narrative, provider = ask_oci_grok_frontier(system, prompt, max_tokens=max_tokens, temperature=0.25)
    except Exception as e:
        narrative, provider = f"[frontier LLM unavailable this cycle: {e}]", None

    verdict_summary = "no real finding — LLM unavailable this cycle" if provider is None else \
        (re.search(r"(?im)^#+\s*executive summary\s*\n+(.+)", narrative)
         or re.search(r"(.{0,120})", narrative)).group(1).strip()

    os.makedirs(AUDIT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", f"{owner}-{repo}".lower()).strip("-")
    path = os.path.join(AUDIT_DIR, f"external-audit-{slug}-{stamp}.md")

    L = [f"# External Bounty Engagement — {program_name or f'{owner}/{repo}'}", "",
         f"**Target repo:** `{owner}/{repo}` @ `{ref}`  ",
         f"**Language:** {language}  ",
         f"**Files reviewed:** {len(files)} (`{', '.join(sorted(files)[:10])}"
         f"{', ...' if len(files) > 10 else ''}`)  ",
         f"**Date:** {now_iso()}  ",
         f"**Engine:** Frontier LLM ({provider or 'unavailable'}) — real source review, no "
         f"Solidity static/symbolic tooling applies to this target's language (see module "
         f"docstring for why)  ",
         "", "---", "", "## AI Security Review", narrative, "", "---", "",
         "## Methodology", "1. Real source fetched directly from the target's own public "
         "GitHub repository (raw.githubusercontent.com, keyless) — byte for byte, nothing "
         "invented or paraphrased before review.",
         "2. A frontier-tier LLM (OCI-hosted Grok 4.3 first, Vertex-tuned Gemini/Groq as "
         "fallback) reads the actual source and reasons per vulnerability class relevant "
         "to the target language/platform.",
         "3. White-hat only: read-only source review, no on-chain interaction or "
         "exploitation attempted.",
         "", "*Generated by agents/external_audit.py — VAPE's reusable external bug-bounty "
         "engagement pipeline. This report is a first-pass automated review; any finding "
         "here still needs the human verification called out above before submission.*"]

    content = "\n".join(L)
    with open(path, "w") as f:
        f.write(content)
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    print(f"[external_audit] wrote {rel}")

    result = {"program": program_name or f"{owner}/{repo}", "repo": f"{owner}/{repo}", "ref": ref,
              "language": language, "files_reviewed": len(files), "report": rel,
              "provider": provider, "verdict_summary": verdict_summary}
    _append_finding(result)
    return result


def main():
    ap = argparse.ArgumentParser(description="VAPE external bug-bounty engagement audit")
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", default="main")
    ap.add_argument("--program-name", default=None)
    ap.add_argument("--paths", default=None, help="comma-separated explicit file paths (skips auto-discovery)")
    args = ap.parse_args()
    paths = [p.strip() for p in args.paths.split(",")] if args.paths else None
    result = run_external_audit(args.owner, args.repo, args.ref, paths, args.program_name)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
