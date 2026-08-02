#!/usr/bin/env python3
"""
VAPE Security Dashboard Builder — zero-LLM, pure aggregation.

Mirrors agents/build_intel_index.py's pattern (pure parsing/aggregation of
real, already-produced artifacts, no LLM call, fully-regenerated output every
run): reads VAPE's own already-real security signals -- the findings ledger
(skillforge/memory/findings.jsonl), its tamper-evidence chain
(skillforge/memory/findings.chain.jsonl), the on-chain attack-intel feed
(data/attack-feed.json), and GitHub's own Actions/Code-Scanning APIs for the
security workflows this repo already runs -- and emits one aggregate JSON
snapshot for the site's Security Dashboard section to render:

  data/security-dashboard.json     -- fully-regenerated snapshot (merge=keep-fresh)
  data/security-dashboard-history.jsonl -- one line appended per run, real
                                            incremental history (merge=union)

Never fabricates a number: every field here traces to a real file this repo
already writes or a real GitHub API response. Where a lane's real signal
can't be reached (e.g. no GITHUB_TOKEN in a local/test run, or a workflow API
call fails), that lane reports null/None rather than inventing a plausible-
looking value -- see _lane_from_workflow_run()'s degradation and the module
docstring's "no fabrication" rule that runs through this whole repo.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from skillforge import findings_chain  # noqa: E402
from skillforge.mcp import GitHubMCPWrapper  # noqa: E402
from agents.security_sweep import ATTACK_PATTERNS  # noqa: E402

FINDINGS_PATH = os.path.join(ROOT, "skillforge", "memory", "findings.jsonl")
ATTACK_FEED_PATH = os.path.join(ROOT, "data", "attack-feed.json")
OUT_PATH = os.path.join(ROOT, "data", "security-dashboard.json")
HISTORY_PATH = os.path.join(ROOT, "data", "security-dashboard-history.jsonl")
REPO = "jUXTAPOSITION1/V.A.P.E"

# Five-bucket severity taxonomy. "INFO" (not the reference dashboard's
# "No-Risk") is the honest label for "no severity signal at all" -- most
# findings.jsonl rows (a routine tool-release log, a PROCEED-verdict
# investigation) never claimed to have been checked-and-cleared, so labeling
# them "No-Risk" would fabricate a claim the data doesn't support.
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

# Real, distinct automated security/quality lanes this repo actually runs --
# VAPE's honest analog to the reference dashboard's Web&API/Cloud/SCA/SAST/
# Container/Infrastructure category cards. No container/cloud-infra lane
# exists because this repo has no such surface -- correctly omitted rather
# than invented.
SECURITY_WORKFLOWS = [
    ("codeql.yml", "Static Analysis (CodeQL)"),
    ("security-lint.yml", "CI / Workflow Hardening"),
    ("vape-reviewer.yml", "Code Review (VAPE Reviewer)"),
    ("dependency-audit.yml", "Dependencies (SCA)"),
    ("scan-parity.yml", "Logic Parity"),
    ("redteam.yml", "AI Red-Team"),
    ("redteam-deep.yml", "AI Red-Team (deep)"),
    ("findings-seal.yml", "Findings Ledger Seal"),
    ("review-ledger.yml", "Review Drift"),
    ("intel-sweeps.yml", "On-Chain Attack Intelligence"),
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path):
    """Every line of a real .jsonl file, malformed lines skipped -- same
    degradation as skillforge/findings_chain.py's own reader. Returns []
    (never raises) if the file doesn't exist yet."""
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    except OSError:
        pass
    return out


def _parse_ts(value):
    """Best-effort ISO-8601 timestamp -> aware datetime, or None. Findings
    across this repo's several direct-write sources aren't perfectly
    consistent about trailing 'Z' vs explicit offset -- normalize both
    rather than crash on whichever a given entry used."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def normalize_severity(entry):
    """Maps VAPE's several real, inconsistent severity signals onto the one
    5-bucket taxonomy above. Real fields, checked in this priority order:

    1. A top-level `severity` key -- written directly (bypassing
       append_to_memory()) by agents/redteam.py, redteam_builder.py,
       cdp_bazaar_check.py, hack_sweep.py, external_audit.py, and
       deep_dive_audit.py. agents/self_improve.py already reads this exact
       top-level field (line ~97) -- real, working precedent this mirrors.
    2. `metadata.verdict` (PROCEED/CAUTION/REJECT) -- written via
       append_to_memory()'s MemoryEntry.to_dict(), which nests all extra
       kwargs under `metadata`; overwhelmingly from agents/investigate.py.
       REJECT->HIGH, CAUTION->MEDIUM, PROCEED->INFO (investigate.py never
       claims a more urgent tier than REJECT, so this never maps to
       CRITICAL).
    3. `tags[]` free-text tokens: "worsened"/"reject"->HIGH,
       "coverage-gap"/"backtest-miss"/"caution"->MEDIUM, "improved"->INFO.
       A bare topical tag like "security" alone is categorization, not a
       rating, and intentionally falls through here.
    4. Fallback -> INFO (no severity signal at all is the honest default).
    """
    severity = entry.get("severity")
    if isinstance(severity, str) and severity.strip():
        s = severity.strip().upper()
        if s == "CRITICAL":
            return "CRITICAL"
        if s == "HIGH":
            return "HIGH"
        if s in ("MEDIUM", "MED"):
            return "MEDIUM"
        if s == "LOW":
            return "LOW"
        if s in ("NONE", "INFO"):
            return "INFO"

    metadata = entry.get("metadata")
    verdict = metadata.get("verdict") if isinstance(metadata, dict) else None
    if isinstance(verdict, str):
        v = verdict.strip().upper()
        if v == "REJECT":
            return "HIGH"
        if v == "CAUTION":
            return "MEDIUM"
        if v == "PROCEED":
            return "INFO"

    tags = entry.get("tags")
    tagset = {str(t).strip().lower() for t in tags} if isinstance(tags, list) else set()
    if tagset & {"worsened", "reject"}:
        return "HIGH"
    if tagset & {"coverage-gap", "backtest-miss", "caution"}:
        return "MEDIUM"
    if "improved" in tagset:
        return "INFO"

    return "INFO"


def _within_days(entry, days, now=None):
    ts = _parse_ts(entry.get("timestamp"))
    if ts is None:
        return False
    now = now or datetime.now(timezone.utc)
    return (now - ts) <= timedelta(days=days)


def build_findings_summary(entries):
    """findings_by_severity (all-time), findings_by_verdict (all-time, from
    metadata.verdict specifically -- the reference dashboard's "Findings per
    Status" analog), and a real daily findings_timeline re-bucketed from
    every entry's own timestamp -- genuinely backfillable today (this repo's
    findings.jsonl already spans ~30 real days), not fabricated history.
    Day (not ISO week) buckets give the Signal Timeline chart enough real
    points to render a genuine per-day marker series rather than a handful
    of flat weekly bars."""
    by_severity = {s: 0 for s in SEVERITIES}
    by_verdict = {"PROCEED": 0, "CAUTION": 0, "REJECT": 0}
    timeline = {}
    for e in entries:
        by_severity[normalize_severity(e)] += 1
        metadata = e.get("metadata")
        verdict = metadata.get("verdict") if isinstance(metadata, dict) else None
        if isinstance(verdict, str) and verdict.strip().upper() in by_verdict:
            by_verdict[verdict.strip().upper()] += 1
        ts = _parse_ts(e.get("timestamp"))
        if ts is not None:
            day = ts.date().isoformat()
            bucket = timeline.setdefault(day, {s: 0 for s in SEVERITIES})
            bucket[normalize_severity(e)] += 1
    findings_timeline = [
        {"period": period, "total": sum(counts.values()), **counts}
        for period, counts in sorted(timeline.items())
    ]
    return by_severity, by_verdict, findings_timeline


def build_findings_recent(entries, limit=150):
    """The most recent real findings, newest first -- backs the Findings
    Ledger table. Every field here is a real value already present on the
    entry (or a value normalize_severity()/the entry's own metadata already
    derives elsewhere in this file); nothing here is synthesized. Entries
    with no parseable timestamp are excluded (there's no honest position to
    place them at in a newest-first ledger), same standard _within_days()
    already applies to the lane calculations above."""
    dated = []
    for e in entries:
        ts = _parse_ts(e.get("timestamp"))
        if ts is None:
            continue
        metadata = e.get("metadata") if isinstance(e.get("metadata"), dict) else {}
        tags = e.get("tags") if isinstance(e.get("tags"), list) else []
        dated.append((ts, {
            "id": e.get("id"),
            "timestamp": e.get("timestamp"),
            "title": e.get("title"),
            "source": e.get("source"),
            "severity": normalize_severity(e),
            "verdict": metadata.get("verdict"),
            "tags": tags,
            "report": metadata.get("report"),
        }))
    dated.sort(key=lambda pair: pair[0], reverse=True)
    return [row for _ts, row in dated[:limit]]


def _lane_from_workflow_run(gh, workflow_file):
    """Real last-run status/timestamp for one workflow via GitHub's Actions
    Runs API, or (None, None) if the call fails (no token, rate limit,
    network) -- degrades honestly rather than fabricating a status."""
    ok, runs = gh.list_workflow_runs(REPO, workflow_file, per_page=1)
    if not ok or not runs:
        return None, None
    run = runs[0]
    return run.get("conclusion"), run.get("run_started_at") or run.get("created_at")


def build_lanes(gh, findings, attack_feed):
    ai_redteam = [e for e in findings if "ai-redteam" in (e.get("tags") or []) and _within_days(e, 30)]
    ai_redteam_by_sev = {s: 0 for s in SEVERITIES}
    for e in ai_redteam:
        ai_redteam_by_sev[normalize_severity(e)] += 1

    code_lint_findings = [e for e in findings if "code-lint" in (e.get("tags") or [])]
    code_lint_open_high = sum(
        1 for e in code_lint_findings if normalize_severity(e) in ("CRITICAL", "HIGH")
    )
    codeql_ok, codeql_alerts = gh.list_code_scanning_alerts(REPO)
    codeql_open = len(codeql_alerts) if codeql_ok else None

    covered = sum(1 for p in ATTACK_PATTERNS if p.get("covered_by"))
    coverage_ratio = (covered / len(ATTACK_PATTERNS)) if ATTACK_PATTERNS else None
    gap_patterns = [
        {"id": p["id"], "label": p["label"]}
        for p in ATTACK_PATTERNS if not p.get("covered_by") and not p.get("out_of_scope")
    ]

    seal_status = findings_chain.verify()

    lessons = [e for e in findings if e.get("category") == "lesson" and _within_days(e, 30)]
    worsened = sum(1 for e in lessons if "worsened" in (e.get("tags") or []))
    improved = sum(1 for e in lessons if "improved" in (e.get("tags") or []))

    lanes = []
    for workflow_file, label in SECURITY_WORKFLOWS:
        conclusion, last_run_at = _lane_from_workflow_run(gh, workflow_file)
        lane = {
            "id": workflow_file.rsplit(".", 1)[0],
            "label": label,
            "source_workflow": workflow_file,
            "last_run_conclusion": conclusion,
            "last_run_at": last_run_at,
        }
        if workflow_file == "codeql.yml":
            lane["headline"] = f"{codeql_open} open alert(s)" if codeql_open is not None else None
            lane["open_alerts"] = codeql_open
            lane["persisted_high_critical_30d"] = code_lint_open_high
        elif workflow_file in ("redteam.yml", "redteam-deep.yml"):
            lane["headline"] = f"{sum(ai_redteam_by_sev.values())} finding(s), 30d"
            lane["severity_breakdown"] = ai_redteam_by_sev
        elif workflow_file == "intel-sweeps.yml":
            lane["headline"] = attack_feed.get("threat_level")
            lane["threat_level"] = attack_feed.get("threat_level")
            lane["coverage_ratio"] = coverage_ratio
            lane["gap_patterns"] = gap_patterns
        elif workflow_file == "findings-seal.yml":
            lane["headline"] = "intact" if seal_status.get("ok") else "BROKEN"
            lane["chain_intact"] = seal_status.get("ok")
        elif workflow_file == "review-ledger.yml":
            lane["headline"] = f"{worsened} worsened / {improved} improved, 30d"
            lane["worsened_30d"] = worsened
            lane["improved_30d"] = improved
        else:
            lane["headline"] = conclusion
        lanes.append(lane)
    return lanes


def build():
    findings = _read_jsonl(FINDINGS_PATH)
    try:
        with open(ATTACK_FEED_PATH) as f:
            attack_feed = json.load(f)
    except (OSError, ValueError):
        attack_feed = {}

    gh = GitHubMCPWrapper()
    findings_by_severity, findings_by_verdict, findings_timeline = build_findings_summary(findings)
    findings_recent = build_findings_recent(findings)
    seal_status = findings_chain.verify()
    lanes = build_lanes(gh, findings, attack_feed)

    dashboard = {
        "generated_at": now_iso(),
        "overall_threat_level": attack_feed.get("threat_level"),
        "findings_by_severity": findings_by_severity,
        "findings_by_verdict": findings_by_verdict,
        "findings_timeline": findings_timeline,
        "findings_recent": findings_recent,
        "ledger_integrity": {
            "chain_intact": seal_status.get("ok"),
            "seals_checked": seal_status.get("seals_checked"),
            "lines_covered": seal_status.get("lines_covered"),
            "unsealed_lines": seal_status.get("unsealed_lines"),
        },
        "lanes": lanes,
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(dashboard, f, indent=2)

    history_row = {
        "ts": dashboard["generated_at"],
        "overall_threat_level": dashboard["overall_threat_level"],
        "findings_by_severity": findings_by_severity,
    }
    with open(HISTORY_PATH, "a") as f:
        f.write(json.dumps(history_row) + "\n")

    print(json.dumps({
        "wrote": os.path.relpath(OUT_PATH, ROOT),
        "overall_threat_level": dashboard["overall_threat_level"],
        "findings_by_severity": findings_by_severity,
        "lanes": len(lanes),
    }, indent=2))
    return dashboard


if __name__ == "__main__":
    build()
