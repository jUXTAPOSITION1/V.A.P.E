"""
VAPE Reviewer — an in-house, security-forward automated PR review bot.

CodeRabbit already reviews every PR on this repo, but it's a third-party
SaaS app with no knowledge of VAPE's own design laws (never fabricate data,
honest {error} degradation, x402 payment-verification correctness,
untrusted-data framing for anything an LLM here consumes). This fills that
specific gap: turn a PR's real diff into a posted review comment, combining
a fast deterministic security-pattern pass (scripts/code_lint.py) with an
LLM pass grounded in the actual diff plus this repo's own real security
posture — not a generic checklist.

Same design laws as every other agent here:
- Advisory only, never a merge gate (matches how this repo already
  describes CodeRabbit itself — see docs/SECURITY_PROTOCOL.md).
- Never auto-applies a fix. agents/self_improve.py already owns that job,
  gated behind its own PR + human review. This module only reports.
- Never checks out or executes the PR's own code. Every read here — the
  diff, each changed file's content — comes from GitHub's REST API via
  skillforge/mcp.py's GitHubMCPWrapper (get_pr_files/get_pr_head_sha/
  read_file), which is text-only. The workflow that calls this
  (.github/workflows/vape-reviewer.yml) triggers on `pull_request`, never
  `pull_request_target`, and checks out only this repo's own base-branch
  copy of this file — the exact same "never run fork-controlled code with
  real secrets" property scripts/security_lint.py itself enforces on every
  other workflow.
- Never raises past main(). A failed run posts an honest "review
  unavailable this cycle" comment rather than going silent — same law every
  data fetcher in this repo already follows.

Usage: python3 -m agents.code_review --pr <number>
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from agents.llm import ask_safe, FRONTIER_ORDER  # noqa: E402
from skillforge.mcp import GitHubMCPWrapper  # noqa: E402
import code_lint  # noqa: E402

# Optional Memory integration (same guarded-import pattern skillforge/mcp.py
# already uses) — lets a human-verified false positive on a deterministic
# finding "stick" across future runs instead of getting re-flagged and
# re-litigated on every PR that touches the same file/pattern.
try:
    from skillforge.memory.retriever import append_to_memory, search_memory
except Exception:
    append_to_memory = None
    search_memory = None

REPO_SLUG = "jUXTAPOSITION1/V.A.P.E"

# Kept short and specific rather than a generic OWASP checklist — this is
# what actually distinguishes this reviewer from a generic tool: real rules
# this repo has actually adopted (docs/SECURITY_PROTOCOL.md), stated so the
# LLM judges a diff against what THIS codebase considers correct, not a
# textbook default.
REPO_SECURITY_LAWS = """\
This repo's real, adopted security/design laws (not aspirational):
- Every data-fetching function returns real data or an honest {"error": ...}
  dict — it never fabricates, never silently returns empty on a real failure.
- Untrusted external content (on-chain token/contract names, verified-source
  comments, anything an LLM here reads that didn't originate from this
  process) must be explicitly framed as untrusted data in any LLM prompt
  that includes it, never concatenated in as if it were an instruction.
- GitHub Actions workflows: never `pull_request_target` combined with a job
  that references secrets; every third-party action pinned to a commit SHA,
  not a mutable tag, in any job with secrets; no `${{ github.event.* }}`/
  `${{ inputs.* }}` spliced directly into a `run:` shell block — route
  through `env:` first; every job with secrets needs `persist-credentials:
  false` on checkout.
- x402/ACP payment or settlement code: verify before granting access/data,
  never trust a client-supplied "paid" flag, log the payment proof/tx hash.
- No secrets, private keys, or API keys ever committed as literals —
  env vars / GitHub secrets / `wrangler secret put` only.
- Any value that ends up in a filesystem path (os.path.join/open/Path) and
  ultimately traces back to a scraped/fetched/API-sourced field (not a
  value this process itself generated) needs a sanitizing call before
  being spliced in — check every field going into the SAME path template
  got the same treatment, not just some of them. Real, shipped miss this
  reviewer should have caught: agents/hack_agent.py's report-path f-string
  wrapped one sibling field in `_slug()` and left the other (an incident's
  reported date) unsanitized right next to it (fixed, PR #372's follow-up).
"""

MAX_DIFF_CHARS = 40000  # same courtesy-truncation pattern agents/run.py's market_context already uses

# Hidden marker identifying VAPE Reviewer's own comment on a PR, so re-runs
# (triggered on `synchronize` — every push) update that one comment in place
# instead of piling up a new comment per push. Directly modeled on CodeRabbit's
# own observed behavior on this repo: one evolving comment per PR, edited
# across pushes, not a new one each time.
COMMENT_MARKER = "<!-- vape-reviewer:auto -->"


def _gh():
    return GitHubMCPWrapper()


def find_existing_comment_id(pr_number):
    """This bot's own prior comment on the PR, if any (identified by
    COMMENT_MARKER), so post_review_comment can edit it in place. Returns
    None on any failure — falls back to creating a new comment, never
    raises."""
    ok, comments = _gh().list_issue_comments(REPO_SLUG, pr_number)
    if not ok:
        return None
    for c in comments:
        if COMMENT_MARKER in (c.get("body") or ""):
            return c.get("id")
    return None


def fetch_pr_head_and_files(pr_number):
    """(head_sha, [{"path", "status", "patch"}], error) for a PR — two
    read-only GitHub API calls (skillforge/mcp.py's GitHubMCPWrapper),
    never a local checkout of the PR's own code."""
    gh = _gh()
    ok_head, head_sha = gh.get_pr_head_sha(REPO_SLUG, pr_number)
    ok_files, files = gh.get_pr_files(REPO_SLUG, pr_number)
    if not ok_head and not ok_files:
        return None, [], "GitHub API unreachable or PR not found"
    return (head_sha if ok_head else None), (files if ok_files else []), None


def build_diff_text(files):
    """Reconstructs a diff-like text from GitHub's own per-file patches —
    real content GitHub already computed, not this process diffing
    anything itself. Close enough to unified-diff format for an LLM to
    read; not meant to be a byte-exact `git diff` reproduction."""
    parts = []
    for f in files:
        patch = f.get("patch") or "(binary or too large for GitHub to show a patch)"
        parts.append(f"diff --git a/{f['path']} b/{f['path']} [{f.get('status', 'modified')}]\n{patch}")
    return "\n\n".join(parts)


def fetch_file_at_ref(path, ref):
    """Real file content at a specific ref via the Contents API (already-
    established GitHubMCPWrapper.read_file, used elsewhere by
    agents/self_improve.py/build_request.py) — text only, never a local
    checkout of the PR's code. Returns None on any failure (deleted file,
    binary, rate limit, etc.) rather than raising."""
    ok, content = _gh().read_file(REPO_SLUG, path, ref=ref)
    return content if ok else None


def run_deterministic_pass(head_sha, files):
    """code_lint's checks against each changed file's real content at the
    PR's head — imported and called directly, not subprocessed."""
    findings = []
    if not head_sha:
        return findings
    for f in files:
        path = f.get("path")
        if not path or f.get("status") == "removed" or os.path.splitext(path)[1] not in code_lint.SOURCE_EXTS:
            continue
        text = fetch_file_at_ref(path, head_sha)
        if text is None:
            continue
        code_lint.lint_text(path, text, findings)
    return annotate_reviewed_exceptions(findings)


# ============================================================================
# Learned exceptions — teaching VAPE Reviewer from a human-verified false
# positive so it stops re-flagging the exact same file/pattern every PR.
#
# This is deliberately narrow: a "lesson" only ever suppresses re-alarm on
# the SAME (path, rule) pair a human actually looked at and confirmed safe
# in context (e.g. hire.js's innerHTML sinks are always fed through
# escapeHtml() at the call site, a shape code_lint's own docstring already
# says it can't trace). It never silently drops the finding — the
# deterministic scan still reports it, still feeds the LLM pass, and the
# comment still shows it; it's annotated as "previously reviewed", not
# deleted. A different file hitting the same regex, or the same file
# hitting a different rule, gets no special treatment and is reviewed
# fresh, matching this repo's "PR-gated, never auto-apply/auto-suppress"
# law (agents/self_improve.py) applied to review findings instead of code
# changes.
# ============================================================================

REVIEWED_EXCEPTION_TAG = "vape-reviewer-exception"

# Ordered (substring-in-message, stable rule tag) pairs — one per code_lint.py
# check. Matched top-to-bottom so more specific substrings can precede a
# broader one if that's ever needed; order doesn't matter today since the
# four checks produce disjoint message shapes.
_RULE_SIGNATURES = [
    ("innerHTML assigned directly from", "innerhtml-bare-var"),
    ("assigned a literal string that looks like a real secret", "hardcoded-secret-literal"),
    ("called on a dynamically-built string", "eval-exec-dynamic"),
    ("pickle.loads() on a non-literal", "pickle-loads-non-literal"),
    ("given a dynamically-built command string", "os-system-shell-injection"),
    ("shell=True) given a dynamically-built command", "subprocess-shell-injection"),
]


def _rule_tag_for_message(msg):
    for substring, tag in _RULE_SIGNATURES:
        if substring in msg:
            return tag
    return "other"


def record_reviewed_exception(path, msg, note, source="human-review"):
    """Teach VAPE Reviewer that this exact (path, rule) finding is a
    verified false positive, so future runs annotate rather than re-alarm.
    Returns True on success, False if Memory is unavailable or the write
    failed — never raises (same law as every other Memory-touching call in
    this repo, see skillforge/mcp.py's own guarded append_to_memory use)."""
    if not append_to_memory:
        return False
    rule_tag = _rule_tag_for_message(msg)
    entry = append_to_memory(
        category="lesson",
        title=f"Reviewed exception: {rule_tag} in {path}",
        content=note,
        source=source,
        tags=[REVIEWED_EXCEPTION_TAG, rule_tag],
        confidence=0.9,
        metadata={"path": path, "rule_tag": rule_tag, "original_finding": msg},
    )
    return bool(entry)


def _find_reviewed_exception(path, msg):
    """The recorded note for this (path, rule) pair, or None. Matches on
    metadata["path"] exactly (not a substring/fuzzy match) — a lesson about
    docs/assets/hire.js says nothing about any other file, even one with an
    identical pattern, until a human reviews that file too."""
    if not search_memory:
        return None
    rule_tag = _rule_tag_for_message(msg)
    try:
        hits = search_memory(rule_tag, category="lesson", tags=[REVIEWED_EXCEPTION_TAG, rule_tag], max_results=10)
    except Exception:
        return None
    for hit in hits:
        if hit.get("metadata", {}).get("path") == path and hit.get("metadata", {}).get("rule_tag") == rule_tag:
            return hit.get("content") or "previously reviewed"
    return None


def annotate_reviewed_exceptions(findings):
    """Marks findings that match a previously-recorded, human-verified
    exception — informational only, never removes or downgrades severity
    (that CI-exit-code gate already only trips on HIGH/CRITICAL, and
    code_lint's innerHTML check is MEDIUM to begin with)."""
    annotated = []
    for sev, path, lineno, msg in findings:
        note = _find_reviewed_exception(path, msg)
        if note:
            msg = f"{msg} [Previously reviewed and confirmed a false positive in this file: {note}]"
        annotated.append((sev, path, lineno, msg))
    return annotated


def _format_deterministic_findings(findings):
    if not findings:
        return "None."
    return "\n".join(f"- [{sev}] `{path}:{lineno}` — {msg}" for sev, path, lineno, msg in findings)


def build_review_prompt(diff, deterministic_findings):
    system = (
        "You are VAPE Reviewer, an automated code-review pass on your OWN real, "
        "live codebase — not a generic example project. The actual stack: Python "
        "stdlib agents (agents/*.py), a Cloudflare Workers/Deno Hono TypeScript "
        "API (worker/src/*.ts), and a vanilla JS/HTML static site with no build "
        "step (docs/assets/*.js). There is no Django/Flask/Express/ORM/user-model "
        "anywhere in this project. Only comment on code literally shown in the "
        "diff below — never invent a file or describe behavior you weren't shown. "
        "If the diff has no real issue, say so plainly under each heading rather "
        "than inventing generic advice to fill space.\n\n"
        + REPO_SECURITY_LAWS
    )
    diff_text = diff if len(diff) <= MAX_DIFF_CHARS else diff[:MAX_DIFF_CHARS] + "\n... (diff truncated)"
    prompt = (
        "=== DETERMINISTIC SCAN FINDINGS (already found by a separate pattern-"
        "matcher — don't re-derive these, just factor them into your judgment; "
        "some may be non-issues in context, e.g. a documented, reviewed "
        "exception) ===\n"
        f"{_format_deterministic_findings(deterministic_findings)}\n\n"
        "=== THE ACTUAL DIFF ===\n"
        f"```diff\n{diff_text}\n```\n\n"
        "=== YOUR TASK ===\n"
        "Review this diff. Reply in exactly this Markdown structure:\n\n"
        "## Summary\n"
        "(1-3 plain-language sentences on what this diff actually does and why — "
        "the kind of thing a reviewer wants to know before reading any code, "
        "not a restatement of the diff stat)\n\n"
        "## Changes\n"
        "(one bullet per changed file: `path` — a specific one-line description "
        "of what changed in it, not a generic \"updated file\")\n\n"
        "## Security\n"
        "(injection, secrets, auth/authz, data-fabrication-law violations, "
        "untrusted-data framing gaps, x402/ACP payment-verification issues, "
        "path traversal — especially a field spliced into a path/filename "
        "with NO sanitizing call around it while a sibling field in the same "
        "template gets one, which is exactly the shape this repo has "
        "actually shipped before — or \"Nothing found.\")\n\n"
        "## Correctness\n"
        "(real logic bugs, missing error handling, edge cases — or \"Nothing found.\")\n\n"
        "## Notes\n"
        "(anything else worth a human's attention, or \"None.\")"
    )
    return system, prompt


def review_pr_diff(diff, deterministic_findings):
    """Never raises — returns (markdown_text, provider_or_none)."""
    system, prompt = build_review_prompt(diff, deterministic_findings)
    return ask_safe(system, prompt, tier="frontier", provider_order=FRONTIER_ORDER, max_tokens=1200)


def post_review_comment(pr_number, body):
    """Updates this bot's own existing comment on the PR in place if one is
    found (via COMMENT_MARKER), otherwise creates it — so `synchronize`
    re-runs on every push don't pile up a new comment each time."""
    body_with_marker = f"{COMMENT_MARKER}\n{body}"
    existing_id = find_existing_comment_id(pr_number)
    if existing_id:
        return _gh().update_issue_comment(REPO_SLUG, existing_id, body_with_marker)
    return _gh().create_pr_comment(REPO_SLUG, pr_number, body_with_marker)


def build_comment_body(deterministic_findings, llm_text, llm_provider):
    header = "## 🛡️ VAPE Reviewer\n\n*Advisory only — not a merge gate. Findings below are automated; use judgment.*\n\n"
    det_section = (
        f"### Deterministic scan ({len(deterministic_findings)} finding(s))\n"
        f"{_format_deterministic_findings(deterministic_findings)}\n\n"
    )
    llm_section = (
        f"### LLM review{f' (via {llm_provider})' if llm_provider else ' (unavailable this run)'}\n"
        f"{llm_text}\n"
    )
    return header + det_section + llm_section


def run(pr_number):
    """The full pipeline for one PR. Never raises — every real failure
    degrades to an honest comment explaining what couldn't run, same law
    every other data path in this repo follows."""
    head_sha, files, err = fetch_pr_head_and_files(pr_number)
    if err:
        post_review_comment(pr_number, "## 🛡️ VAPE Reviewer\n\n"
                                        f"Review unavailable this run ({err}).")
        return False

    diff = build_diff_text(files)
    deterministic_findings = run_deterministic_pass(head_sha, files)
    llm_text, llm_provider = review_pr_diff(diff, deterministic_findings)

    body = build_comment_body(deterministic_findings, llm_text, llm_provider)
    posted, post_err = post_review_comment(pr_number, body)
    if not posted:
        print(f"[code_review] failed to post comment: {post_err}", file=sys.stderr)
    return posted


def main():
    ap = argparse.ArgumentParser(description="VAPE Reviewer — automated security-forward PR review")
    ap.add_argument("--pr", required=True, type=int, help="pull request number")
    args = ap.parse_args()
    # Advisory only, never a merge gate (see module docstring) — run() already
    # degrades any handled failure (GitHub API unreachable, comment-post
    # failure) into an honest posted comment rather than raising, so exit 0
    # either way. A transient GitHub outage shouldn't turn this check red;
    # only a genuinely unexpected crash (a real bug, not an external failure)
    # should, so the CI job actually flags something worth looking at.
    try:
        run(args.pr)
    except Exception as e:
        print(f"[code_review] unexpected crash: {e}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
