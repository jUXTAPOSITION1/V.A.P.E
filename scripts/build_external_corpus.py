#!/usr/bin/env python3
"""
Fetches real external security ground truth VAPE didn't produce itself, and
caches it as data/finetune/external_corpus.jsonl — same chat-messages schema
and same honesty discipline as scripts/build_finetune_dataset.py's other
sources: every row's label traces to an independently-verified real outcome
(an official CVSS severity, a real audit contest's judged risk category),
never an LLM's guess or a fabricated ground truth.

Why this is a SEPARATE script rather than folded straight into
build_finetune_dataset.py: that script is deliberately offline/deterministic
— it only reads already-committed repo files and runs in seconds with zero
external dependency. This script does real network I/O against external
services (rate-limited, occasionally flaky) and is meant to run occasionally
on its own schedule, caching results into a new committed file that
build_finetune_dataset.py then reads like any other local source (see its
collect_external()).

Sources (v1 — only ones whose real structure was actually verified; more may
be added later, never on a guess):

  cve        NVD's public CVE API (services.nvd.nist.gov), keyword-filtered
             to blockchain/smart-contract/DeFi terms. Label = the CVE's own
             official CVSS baseSeverity metric — never re-derived.

  code4rena  Pre-~2023 code-423n4/<contest>-findings repos, which committed a
             data/*.json index per finding (auditor handle, risk category,
             a link to the real GitHub Issue) before Code4rena moved findings
             entirely into GitHub Issues with no local index. For repos in
             CODE4RENA_FINDINGS_REPOS below, this fetches that index, then the
             real Issue title+body it points to. Label = the contest's own
             judged risk category (H=High / M=Medium) — never re-guessed;
             Gas/QA/invalid findings are skipped since they're not risk-rated.

NOT included despite being asked for ("all of the above, everything
possible"): SWC Registry and Sherlock's per-contest judging repos. Both were
investigated — SWC's expected entries/ path 404s under the registry's current
default branch (it's also been unmaintained since 2020, which cuts against
using it for a "current threat patterns" agent anyway), and Sherlock's
numbered `NNN-{H,M}/` directories were confirmed to exist but the exact
filename inside each wasn't. Rather than ship a parser built on a guess that
would silently produce zero (or wrong) rows, these are left for a follow-up
once verified — this file's docstring should be updated the moment they are.

This script needs real internet access to services.nvd.nist.gov and
api.github.com — it will NOT run from a network-policy-restricted sandbox;
only from a normal GitHub Actions runner or the training GPU box. Its own
tests (tests/test_build_external_corpus.py) are hermetic — they feed the
transform functions real captured API response shapes, no live network call.

Usage:
  python scripts/build_external_corpus.py                # fetch + merge + write
  python scripts/build_external_corpus.py --max-cve 100 --max-c4r 20
  python scripts/build_external_corpus.py --stats         # print cached counts, fetch nothing
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
OUT_PATH = os.path.join(_REPO_ROOT, "data", "finetune", "external_corpus.jsonl")

NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
CVE_KEYWORDS = [
    "smart contract", "solidity", "ethereum", "defi protocol",
    "blockchain wallet", "erc-20", "web3",
]

# Verified real repos using the old data/*.json + issueUrl index format (see
# module docstring). Add more here ONLY after confirming the same structure —
# most post-2023 contests moved findings entirely into GitHub Issues with no
# local data/ index, which this fetcher does not handle and would silently
# return zero rows for.
CODE4RENA_FINDINGS_REPOS = [
    "code-423n4/2023-01-numoen-findings",
]

_UA = {"User-Agent": "VAPE-training-corpus/1.0 (+github.com/jUXTAPOSITION1/V.A.P.E)"}

_SEVERITY_SYSTEM = (
    "You are VAPE, an autonomous on-chain security investigator. Given a "
    "real, published vulnerability disclosure, classify its severity based "
    "strictly on the evidence in the disclosure."
)


def _get_json(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={**_UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


# ---------------------------------------------------------------------------
# CVE (NVD)
# ---------------------------------------------------------------------------

def cve_to_row(cve_item):
    """One NVD API `vulnerabilities[]` entry -> one training row, or None if
    it lacks an English description or an official CVSS severity (never
    invent either)."""
    cve = cve_item.get("cve", cve_item)
    cve_id = cve.get("id")
    descs = cve.get("descriptions") or []
    desc = next((d.get("value") for d in descs if d.get("lang") == "en"), None)
    if not cve_id or not desc:
        return None

    metrics = cve.get("metrics") or {}
    severity = None
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key)
        if entries:
            data = entries[0].get("cvssData", {})
            severity = data.get("baseSeverity") or entries[0].get("baseSeverity")
            if severity:
                break
    if not severity:
        return None

    return {
        "messages": [
            {"role": "system", "content": _SEVERITY_SYSTEM},
            {"role": "user", "content": f"Vulnerability disclosure ({cve_id}):\n{desc}"},
            {"role": "assistant", "content": f"Severity: {severity.upper()}"},
        ],
        "source": "cve", "source_id": cve_id,
    }


def fetch_cve_entries(max_results=200, sleep_s=6.5):
    """Paginated NVD keyword search across CVE_KEYWORDS. sleep_s keeps every
    call safely under NVD's unauthenticated 5-requests-per-30s limit — this
    is meant to run occasionally (a scheduled workflow), not repeatedly."""
    rows, seen_ids = [], set()
    for kw in CVE_KEYWORDS:
        if len(rows) >= max_results:
            break
        url = f"{NVD_API}?keywordSearch={urllib.parse.quote(kw)}&resultsPerPage=50"
        try:
            data = _get_json(url)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            print(f"[build_external_corpus] cve fetch failed for {kw!r}: {e}", file=sys.stderr)
            continue
        for item in data.get("vulnerabilities", []):
            row = cve_to_row(item)
            if row and row["source_id"] not in seen_ids:
                seen_ids.add(row["source_id"])
                rows.append(row)
        time.sleep(sleep_s)
    return rows[:max_results]


# ---------------------------------------------------------------------------
# Code4rena
# ---------------------------------------------------------------------------

def code4rena_finding_to_row(repo, index_entry, issue_body):
    """One data/*.json index entry + its linked Issue body -> one training
    row, or None for anything that isn't a real judged High/Medium risk
    finding (Gas/QA/invalid are skipped — they were never risk-rated, so
    there is no real label to assign)."""
    risk = index_entry.get("risk")
    if risk not in ("H", "M") or not issue_body:
        return None
    title = index_entry.get("title") or ""
    label = {"H": "HIGH", "M": "MEDIUM"}[risk]
    return {
        "messages": [
            {"role": "system", "content": _SEVERITY_SYSTEM},
            {"role": "user", "content": f"Audit finding ({repo}) — {title}:\n{issue_body}"},
            {"role": "assistant", "content": f"Severity: {label}"},
        ],
        "source": "code4rena", "source_id": f"{repo}#{index_entry.get('issueId')}",
    }


def fetch_code4rena_findings(repos=None, max_per_repo=30, sleep_s=1.5):
    """Two-hop fetch per repo: list data/*.json -> for each real H/M entry,
    fetch the linked GitHub Issue for its real title+body. Unauthenticated
    GitHub API is rate-limited to 60 req/hour, so max_per_repo keeps a single
    run well within that."""
    repos = repos if repos is not None else CODE4RENA_FINDINGS_REPOS
    rows = []
    for repo in repos:
        try:
            listing = _get_json(f"https://api.github.com/repos/{repo}/contents/data")
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            print(f"[build_external_corpus] code4rena listing failed for {repo}: {e}", file=sys.stderr)
            continue
        if not isinstance(listing, list):
            print(f"[build_external_corpus] unexpected listing shape for {repo}, skipping", file=sys.stderr)
            continue
        json_files = [f for f in listing if isinstance(f, dict) and f.get("name", "").endswith(".json")]
        n = 0
        for f in json_files:
            if n >= max_per_repo:
                break
            try:
                index_entry = _get_json(f["download_url"])
            except (urllib.error.URLError, TimeoutError, ValueError, OSError, KeyError):
                continue
            if index_entry.get("risk") not in ("H", "M"):
                continue
            issue_id = index_entry.get("issueId")
            if not issue_id:
                continue
            try:
                issue = _get_json(f"https://api.github.com/repos/{repo}/issues/{issue_id}")
                time.sleep(sleep_s)
            except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
                print(f"[build_external_corpus] issue fetch failed {repo}#{issue_id}: {e}", file=sys.stderr)
                continue
            row = code4rena_finding_to_row(repo, index_entry, issue.get("body"))
            if row:
                rows.append(row)
                n += 1
    return rows


# ---------------------------------------------------------------------------
# Cache merge + CLI
# ---------------------------------------------------------------------------

def _load_cached():
    if not os.path.exists(OUT_PATH):
        return []
    rows = []
    with open(OUT_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def merge_rows(cached, fresh):
    """Fresh rows win on (source, source_id) collision (in case a label
    changed upstream), everything else from cached is kept — this is a
    growing cache across occasional runs, not a full rebuild each time
    (NVD/GitHub rate limits make a full rebuild every run impractical)."""
    by_key = {(r["source"], r["source_id"]): r for r in cached}
    for r in fresh:
        by_key[(r["source"], r["source_id"])] = r
    return sorted(by_key.values(), key=lambda r: (r["source"], r["source_id"]))


def _source_counts(rows):
    counts = {}
    for r in rows:
        counts[r["source"]] = counts.get(r["source"], 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser(description="Fetch + cache VAPE's external training corpus.")
    ap.add_argument("--max-cve", type=int, default=200)
    ap.add_argument("--max-c4r", type=int, default=30)
    ap.add_argument("--stats", action="store_true", help="print cached counts, fetch nothing")
    args = ap.parse_args()

    if args.stats:
        cached = _load_cached()
        print(f"cached: {len(cached)} example(s) — {_source_counts(cached)}")
        return

    cached = _load_cached()
    fresh = fetch_cve_entries(max_results=args.max_cve) + fetch_code4rena_findings(max_per_repo=args.max_c4r)
    merged = merge_rows(cached, fresh)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in merged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"fetched {len(fresh)} fresh, cache now {len(merged)} total — {_source_counts(merged)}")
    print(f"wrote {os.path.relpath(OUT_PATH, _REPO_ROOT)}")


if __name__ == "__main__":
    main()
