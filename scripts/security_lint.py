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
3. `${{ github.event.* }}` or `${{ inputs.* }}` spliced directly into a
   `run:` step's shell text instead of being routed through `env:` first —
   shell-injection into whatever secrets that job carries (confirmed real:
   `review-ledger.yml` and `x402-index-claim.yml` both did this).
4. A workflow with no top-level `permissions:` block — relies on the
   (often broad) default `GITHUB_TOKEN` instead of least privilege.

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
# Deliberately broad: any of these appearing literally inside a `run:`
# step's text is the exact anti-pattern this guards against, regardless of
# how deeply nested the step is.
UNSAFE_INTERP_RE = re.compile(r"\$\{\{\s*(github\.event\.[^}]*?|inputs\.[^}]*?)\s*\}\}")


def _iter_workflow_files(workflows_dir):
    return sorted(glob.glob(os.path.join(workflows_dir, "*.yml"))) + sorted(
        glob.glob(os.path.join(workflows_dir, "*.yaml"))
    )


def _job_has_secrets(job, raw_job_text):
    if "secrets." in raw_job_text:
        return True
    env = job.get("env") if isinstance(job, dict) else None
    if isinstance(env, dict) and any("secrets." in str(v) for v in env.values()):
        return True
    return False


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
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            uses = step.get("uses")
            if not uses or not isinstance(uses, str):
                continue
            if uses.startswith(TRUSTED_ACTION_PREFIXES):
                continue
            ref = uses.rsplit("@", 1)[-1] if "@" in uses else ""
            if not SHA_RE.match(ref):
                findings.append((
                    "HIGH", path,
                    f"job '{job_name}' step uses '{uses}' (not pinned to a commit SHA) "
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
            if UNSAFE_INTERP_RE.search(run):
                match = UNSAFE_INTERP_RE.search(run).group(0)
                findings.append((
                    "HIGH", path,
                    f"job '{job_name}' step '{step.get('name', '(unnamed)')}' interpolates "
                    f"{match} directly into `run:` — route it through `env:` first.",
                ))


def _check_missing_permissions(doc, path, findings):
    if "permissions" not in doc:
        findings.append((
            "MEDIUM", path,
            "no top-level `permissions:` block — relies on the default token scope "
            "instead of least privilege.",
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
