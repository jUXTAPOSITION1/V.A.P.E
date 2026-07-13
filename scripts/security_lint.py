#!/usr/bin/env python3
"""Regression guard for .github/workflows/*.yml.

Encodes the exact CI supply-chain / injection risk classes found in the
2026-07-13 repo-wide security audit, so a future PR — including one
self_improve.py or skillforge_build.py opens on its own — can't silently
reintroduce any of them:

1. `pull_request_target` (or `workflow_run`) combined with a job that
   references any `secrets.*` — the classic "pwn request" pattern (fork-
   controlled code running with this repo's real secrets).
2. A third-party action (not `actions/*`, not `github/*`) pinned to a
   mutable tag/branch instead of a commit SHA, in a job that references any
   `secrets.*` — a repointed tag would run arbitrary code with real
   credentials on the next matching trigger (confirmed real class: this is
   exactly how `cloudflare/wrangler-action@v4` was flagged and fixed).
3. `${{ github.event.* }}` or `${{ inputs.* }}` — dot OR bracket/index
   notation (`github['event']['title']` is the same risk as
   `github.event.title`) — spliced directly into a `run:` step's shell text
   instead of being routed through `env:` first — shell-injection into
   whatever secrets that job carries (confirmed real: `review-ledger.yml`
   and `x402-index-claim.yml` both did this).
4. A workflow with no top-level `permissions:` block — relies on the
   (often broad) default `GITHUB_TOKEN` instead of least privilege.
5. A job that references secrets and checks out the repo without
   `persist-credentials: false` — the default persists `GITHUB_TOKEN` in
   local git config for the rest of the job, needlessly widening what a
   later step, a debug artifact, or a logging bug could leak (CWE-522,
   confirmed real across 16 jobs during the CodeRabbit review of the PR
   that introduced this linter).

NOT covered by design: `${{ steps.X.outputs.Y }}` re-interpolated into
`run:` (the exact shape of the real `review-ledger.yml` bug this linter's
own PR fixed by hand) is not flagged here even though it's the same class
of risk when that particular output was itself derived from
`github.event.*`/`inputs.*`. Catching it in general would mean tracing
dataflow across steps, which a line-level regex can't do without constant
false positives — `steps.*.outputs.*` is used everywhere for values that
never touch attacker input. Caught manually this once; a real regression
here needs a human (or a future, smarter tool) to notice.

Pure, network-free, deterministic — reads and pattern-matches YAML text
only, makes no network/LLM calls. Safe to run on every PR.

Usage: python3 scripts/security_lint.py [workflows_dir]
Exit code 0 if clean, 1 if any finding (all classes above are hard fails —
none has a legitimate reason to exist in this repo, so there's no "warn
only" tier here).
"""
import glob
import os
import re
import sys

import yaml

DEFAULT_WORKFLOWS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".github", "workflows",
)

FORK_DANGER_TRIGGERS = {"pull_request_target", "workflow_run"}
TRUSTED_ACTION_PREFIXES = ("actions/", "github/")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
# Anchors on the ROOT context (github.event / inputs) via a lookahead, then
# consumes to the closing `}}` for the finding message — so dot notation
# (github.event.title) and bracket/index notation (github['event']['title'],
# inputs['name']) are both caught, not just dot notation (confirmed real
# gap: CodeRabbit review, PR #157). `\b`/explicit `.`/`[` after the anchor
# keeps `github.sha`, `github.head_ref`, etc. (not attacker-controlled in
# the same way) from false-positiving.
UNSAFE_INTERP_RE = re.compile(
    r"\$\{\{\s*(?=github(?:\.event\b|\[\s*['\"]event['\"])|inputs(?:\.|\[))[^}]*\}\}"
)


def _iter_workflow_files(workflows_dir):
    return sorted(glob.glob(os.path.join(workflows_dir, "*.yml"))) + sorted(
        glob.glob(os.path.join(workflows_dir, "*.yaml"))
    )


def _job_has_secrets(job, raw_job_text):
    if "secrets." in raw_job_text:
        return True
    if isinstance(job, dict) and job.get("secrets") == "inherit":
        return True  # confirmed real gap: reusable-workflow `secrets: inherit`
        # carries every caller secret but never contains the literal
        # substring "secrets." — CodeRabbit review, PR #157.
    env = job.get("env") if isinstance(job, dict) else None
    if isinstance(env, dict) and any("secrets." in str(v) for v in env.values()):
        return True
    return False


def _is_trusted_uses(uses):
    # "./" is a reusable workflow defined IN this repo — reviewed via the
    # same PR process as every other file here, not a third-party supply-
    # chain risk the way an external action/workflow reference is.
    return uses.startswith(TRUSTED_ACTION_PREFIXES) or uses.startswith("./")


def _check_pwn_request(doc, path, findings):
    on = doc.get("on") or doc.get(True)  # PyYAML 5.x parses bare `on:` key as True in some configs
    triggers = set()
    if isinstance(on, dict):
        triggers = set(on.keys())
    elif isinstance(on, list):
        triggers = set(on)
    elif isinstance(on, str):
        triggers = {on}
    danger = triggers & FORK_DANGER_TRIGGERS
    if not danger:
        return
    jobs = doc.get("jobs") or {}
    for job_name, job in jobs.items():
        if isinstance(job, dict) and _job_has_secrets(job, yaml.dump(job)):
            findings.append((
                "CRITICAL", path,
                f"job '{job_name}' runs on trigger(s) {sorted(danger)} and references secrets — "
                "classic pwn-request pattern (fork-controlled code with real secrets).",
            ))


def _check_unpinned_actions_with_secrets(doc, path, findings):
    jobs = doc.get("jobs") or {}
    for job_name, job in (jobs.items() if isinstance(jobs, dict) else []):
        if not isinstance(job, dict):
            continue
        has_secrets = _job_has_secrets(job, yaml.dump(job))
        if not has_secrets:
            continue
        # job.get("uses") is a reusable-workflow call (jobs.<id>.uses) —
        # confirmed real gap: the original version of this check only ever
        # looked at steps[*].uses, so a credentialed reusable-workflow call
        # (which has no "steps" of its own to inspect at all) passed
        # unconditionally regardless of pinning (CodeRabbit review, PR #157).
        job_uses = job.get("uses")
        uses_list = [job_uses] if isinstance(job_uses, str) else []
        for step in job.get("steps") or []:
            if isinstance(step, dict) and isinstance(step.get("uses"), str):
                uses_list.append(step["uses"])
        for uses in uses_list:
            if _is_trusted_uses(uses):
                continue
            ref = uses.rsplit("@", 1)[-1] if "@" in uses else ""
            if not SHA_RE.match(ref):
                findings.append((
                    "HIGH", path,
                    f"job '{job_name}' uses '{uses}' (not pinned to a commit SHA) "
                    "in a job that references secrets — pin to the exact commit.",
                ))


def _check_unsafe_interpolation(doc, path, findings):
    jobs = doc.get("jobs") or {}
    for job_name, job in (jobs.items() if isinstance(jobs, dict) else []):
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            run = step.get("run")
            if not run or not isinstance(run, str):
                continue
            match = UNSAFE_INTERP_RE.search(run)
            if match:
                findings.append((
                    "HIGH", path,
                    f"job '{job_name}' step '{step.get('name', '(unnamed)')}' interpolates "
                    f"{match.group(0)} directly into `run:` — route it through `env:` first.",
                ))


def _check_missing_permissions(doc, path, findings):
    if "permissions" not in doc:
        findings.append((
            "MEDIUM", path,
            "no top-level `permissions:` block — relies on the default token scope "
            "instead of least privilege.",
        ))


def _check_missing_persist_credentials(doc, path, findings):
    jobs = doc.get("jobs") or {}
    for job_name, job in (jobs.items() if isinstance(jobs, dict) else []):
        if not isinstance(job, dict):
            continue
        if not _job_has_secrets(job, yaml.dump(job)):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if not isinstance(uses, str) or not uses.startswith("actions/checkout"):
                continue
            with_block = step.get("with") or {}
            if with_block.get("persist-credentials") is not False:
                findings.append((
                    "MEDIUM", path,
                    f"job '{job_name}' checks out the repo without "
                    "`persist-credentials: false` in a job that references secrets — "
                    "the default persists GITHUB_TOKEN in local git config for the rest "
                    "of the job, needlessly widening what a later step/artifact/logging "
                    "bug could leak (CWE-522).",
                ))


def lint_file(path, findings):
    with open(path) as f:
        text = f.read()
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as e:
        findings.append(("HIGH", path, f"YAML failed to parse: {e}"))
        return
    if not isinstance(doc, dict):
        return
    _check_pwn_request(doc, path, findings)
    _check_unpinned_actions_with_secrets(doc, path, findings)
    _check_unsafe_interpolation(doc, path, findings)
    _check_missing_permissions(doc, path, findings)
    _check_missing_persist_credentials(doc, path, findings)


def main():
    workflows_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WORKFLOWS_DIR
    files = _iter_workflow_files(workflows_dir)
    if not files:
        print(f"No workflow files found under {workflows_dir}")
        return 0
    findings = []
    for path in files:
        lint_file(path, findings)
    if not findings:
        print(f"security_lint: clean — {len(files)} workflow file(s) checked, no findings.")
        return 0
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: severity_order.get(f[0], 9))
    for severity, path, msg in findings:
        print(f"[{severity}] {os.path.relpath(path)}: {msg}")
    print(f"\nsecurity_lint: {len(findings)} finding(s) across {len(files)} workflow file(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
