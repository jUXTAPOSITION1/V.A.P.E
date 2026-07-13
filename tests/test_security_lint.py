"""Tests for scripts/security_lint.py — the CI regression guard for
.github/workflows/*.yml. Pure, network-free; exercises the detector
functions directly against small in-memory workflow docs rather than the
real .github/workflows/ directory (that's covered by running the script
itself in CI on every workflow change).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import security_lint as sl


def test_pwn_request_pattern_flagged():
    doc = {
        "on": {"pull_request_target": {}},
        "jobs": {"build": {"steps": [{"run": "echo hi"}], "env": {"TOKEN": "${{ secrets.MY_TOKEN }}"}}},
    }
    findings = []
    sl._check_pwn_request(doc, "fake.yml", findings)
    assert len(findings) == 1
    assert findings[0][0] == "CRITICAL"


def test_pwn_request_without_secrets_not_flagged():
    doc = {
        "on": {"pull_request_target": {}},
        "jobs": {"build": {"steps": [{"run": "echo hi"}]}},
    }
    findings = []
    sl._check_pwn_request(doc, "fake.yml", findings)
    assert findings == []


def test_normal_pull_request_trigger_not_flagged():
    doc = {
        "on": {"pull_request": {}},
        "jobs": {"build": {"steps": [{"run": "echo hi"}], "env": {"TOKEN": "${{ secrets.MY_TOKEN }}"}}},
    }
    findings = []
    sl._check_pwn_request(doc, "fake.yml", findings)
    assert findings == []


def test_unpinned_third_party_action_with_secrets_flagged():
    doc = {
        "jobs": {
            "deploy": {
                "env": {"TOKEN": "${{ secrets.CLOUDFLARE_API_TOKEN }}"},
                "steps": [{"uses": "cloudflare/wrangler-action@v4"}],
            }
        }
    }
    findings = []
    sl._check_unpinned_actions_with_secrets(doc, "fake.yml", findings)
    assert len(findings) == 1
    assert findings[0][0] == "HIGH"


def test_sha_pinned_third_party_action_not_flagged():
    doc = {
        "jobs": {
            "deploy": {
                "env": {"TOKEN": "${{ secrets.CLOUDFLARE_API_TOKEN }}"},
                "steps": [{"uses": "cloudflare/wrangler-action@" + "a" * 40}],
            }
        }
    }
    findings = []
    sl._check_unpinned_actions_with_secrets(doc, "fake.yml", findings)
    assert findings == []


def test_trusted_actions_prefix_never_flagged_even_unpinned():
    doc = {
        "jobs": {
            "build": {
                "env": {"TOKEN": "${{ secrets.SOME_TOKEN }}"},
                "steps": [{"uses": "actions/checkout@v7"}],
            }
        }
    }
    findings = []
    sl._check_unpinned_actions_with_secrets(doc, "fake.yml", findings)
    assert findings == []


def test_unpinned_action_without_secrets_not_flagged():
    doc = {
        "jobs": {
            "typecheck": {
                "steps": [{"uses": "denoland/setup-deno@v2"}],
            }
        }
    }
    findings = []
    sl._check_unpinned_actions_with_secrets(doc, "fake.yml", findings)
    assert findings == []


def test_raw_event_interpolation_in_run_flagged():
    doc = {
        "jobs": {
            "build": {
                "steps": [{"name": "bad", "run": 'echo "${{ github.event.inputs.categories }}"'}],
            }
        }
    }
    findings = []
    sl._check_unsafe_interpolation(doc, "fake.yml", findings)
    assert len(findings) == 1
    assert findings[0][0] == "HIGH"


def test_env_scoped_interpolation_in_run_not_flagged():
    doc = {
        "jobs": {
            "build": {
                "steps": [{
                    "name": "good",
                    "env": {"CATS": "${{ github.event.inputs.categories }}"},
                    "run": 'echo "$CATS"',
                }],
            }
        }
    }
    findings = []
    sl._check_unsafe_interpolation(doc, "fake.yml", findings)
    assert findings == []


def test_missing_permissions_block_flagged():
    findings = []
    sl._check_missing_permissions({"jobs": {}}, "fake.yml", findings)
    assert len(findings) == 1
    assert findings[0][0] == "MEDIUM"


def test_present_permissions_block_not_flagged():
    findings = []
    sl._check_missing_permissions({"permissions": {"contents": "read"}, "jobs": {}}, "fake.yml", findings)
    assert findings == []


def test_real_repo_workflows_pass_clean():
    """The actual regression-guard invariant: every real workflow file in
    this repo today must already be clean (all 4 classes were fixed as
    part of the audit that introduced this linter)."""
    findings = []
    for path in sl._iter_workflow_files(sl.DEFAULT_WORKFLOWS_DIR):
        sl.lint_file(path, findings)
    assert findings == [], f"unexpected findings in real workflows: {findings}"
