#!/usr/bin/env python3
"""
VAPE report archiver — tames working-tree file-count sprawl without losing a
single byte of the audit trail or breaking the dashboard.

The problem it solves: reports/ and intel/reports/ are loose-file dumps that
grow ~20-30 files/day. Most of reports/ (repo_review_*, redteam_*,
self_improve_*, skillforge_build_*) is internal cycle output the dashboard
never surfaces (docs/assets/app.js only ever shows the 6 most-recent
reports, and data/intel-index.json is regenerated from live files every run,
so anything archived simply drops out of the index instead of 404-ing a
blob link). Left alone, the tree crosses thousands of files well before the
repo ever approaches a real GitHub size limit — Git browsing, checkout, and
linear jsonl/glob scans all degrade first.

What it does: files older than a retention window are folded into ONE
compressed tarball per (category, month) under intel/archive/, their
metadata is preserved in intel/archive/index.json (so every archived report
stays findable by name/date/type/threat/summary even after the raw file
leaves the live tree), and the loose file is removed. A monthly tarball is
written at most a few times (only while its month is the boundary month),
so history churn drops massively versus committing hundreds of individual
loose files.

Deliberate design choices:
  - Dates are parsed FROM FILENAMES, and the retention cutoff is computed
    relative to the NEWEST report seen, not the wall clock. This repo's
    committed dates run ahead of any given runner's clock; anchoring to the
    data itself is the only correct, skew-proof way to decide "recent".
  - Never touches anything inside the retention window, and never touches
    files that aren't real timestamped report outputs (lists, templates,
    the bounty/ subdir, etc. are left alone by construction — only the
    explicit SOURCES globs are considered).
  - Idempotent: a file already represented in intel/archive/index.json (or
    already gone from the live tree) is skipped, so re-runs are no-ops.
  - Dry-run by DEFAULT. Nothing is moved or deleted without --apply.

Usage:
  python scripts/archive_reports.py                     # dry-run, default 21d
  python scripts/archive_reports.py --retention-days 30 # custom window
  python scripts/archive_reports.py --apply             # actually archive
  python scripts/archive_reports.py --stats             # just print live counts
"""
import argparse
import glob
import hashlib
import io
import json
import os
import re
import tarfile
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_DIR = os.path.join(ROOT, "intel", "archive")
ARCHIVE_INDEX = os.path.join(ARCHIVE_DIR, "index.json")

DEFAULT_RETENTION_DAYS = 21

# Each source: a glob (relative to repo root), the archive "category" that
# groups its tarballs, how to pull a YYYY-MM-DD date out of the basename, and
# an optional per-category retention override in days.
#
# Two tiers of retention, because the two tiers of report have very different
# shelf lives:
#   - Internal cycle outputs (repo_review/redteam/self_improve/... — the bulk
#     of the sprawl, and NOT indexed by the dashboard) are ephemeral churn.
#     Nobody browses a two-week-old repo_review; they get a short window.
#   - Dashboard-indexed reports (bounty_report, intel_reports) get the longer
#     default window so the site's "recent reports" list is never starved.
#     They self-heal out of data/intel-index.json either way, this is a
#     nicety, not a correctness requirement.
_TS_RE = re.compile(r"(\d{4})(\d{2})(\d{2})_\d{6}")          # reports/foo_YYYYMMDD_HHMMSS.md
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")            # intel/reports/foo-YYYY-MM-DD-*.md

_INTERNAL_RETENTION = 7  # ephemeral internal cycle output

SOURCES = [
    # Internal cycle outputs — NOT indexed by the dashboard, short retention.
    {"glob": "reports/repo_review_*.md", "category": "repo_review", "date": "ts", "indexed": False, "retention": _INTERNAL_RETENTION},
    {"glob": "reports/redteam_*.md", "category": "redteam", "date": "ts", "indexed": False, "retention": _INTERNAL_RETENTION},
    {"glob": "reports/self_improve_*.md", "category": "self_improve", "date": "ts", "indexed": False, "retention": _INTERNAL_RETENTION},
    {"glob": "reports/self_pr_proposal_*.md", "category": "self_improve", "date": "ts", "indexed": False, "retention": _INTERNAL_RETENTION},
    {"glob": "reports/skillforge_build_*.md", "category": "skillforge_build", "date": "ts", "indexed": False, "retention": _INTERNAL_RETENTION},
    {"glob": "reports/build_request_*.md", "category": "build_request", "date": "ts", "indexed": False, "retention": _INTERNAL_RETENTION},
    # Indexed by the dashboard — default (longer) retention, self-heals out of the index.
    {"glob": "reports/bounty_report_*.md", "category": "bounty_report", "date": "ts", "indexed": True},
    {"glob": "intel/reports/*.md", "category": "intel_reports", "date": "date", "indexed": True},
]


def _parse_date(basename, mode):
    m = (_TS_RE if mode == "ts" else _DATE_RE).search(basename)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _first_heading(text, fallback):
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip() or fallback
    return fallback


# Tolerates a run of non-letters between the label and the value, so the
# real report headers ("## THREAT LEVEL: 🔴 HIGH", "**Verdict:** ✅ PROCEED")
# still extract — a bare `\s*\**\s*` gap misses the emoji/decoration these
# reports actually use and silently records threat=null.
_THREAT_RE = re.compile(
    r"(?:Threat Level|Risk posture|Verdict|Market Mood|posture)\s*(?:is|:|：)?[^A-Za-z]{0,8}"
    r"(CRITICAL|HIGH|MEDIUM|LOW|ALL CLEAR|RISK-ON|RISK-OFF|NEUTRAL|BULLISH|BEARISH|"
    r"FEAR|GREED|PROCEED|CAUTION|REJECT)", re.I)


def _threat(text):
    m = _THREAT_RE.search(text)
    return m.group(1).upper() if m else None


def _summary(text, limit=280):
    for line in text.splitlines():
        s = line.strip()
        if s and not s.startswith("#") and not s.startswith("**Generated") and not s.startswith("---"):
            return (s[:limit] + "…") if len(s) > limit else s
    return ""


def _load_index():
    try:
        with open(ARCHIVE_INDEX, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {"archived": []}
    except Exception:
        return {"archived": []}


def _collect(default_retention):
    """Return (all_files, newest_date). Each file dict carries the resolved
    absolute path, basename, category, date, indexed flag, and the retention
    (days) that applies to it — per-source override, else the global default."""
    files, newest = [], None
    for src in SOURCES:
        retention = src.get("retention", default_retention)
        for fp in glob.glob(os.path.join(ROOT, src["glob"])):
            if not os.path.isfile(fp):
                continue
            name = os.path.basename(fp)
            d = _parse_date(name, src["date"])
            if d is None:
                continue  # unparseable name — never archive by accident
            files.append({"path": fp, "name": name, "category": src["category"],
                          "date": d, "indexed": src["indexed"], "retention": retention})
            if newest is None or d > newest:
                newest = d
    return files, newest


def stats(default_retention):
    """Print live report counts by category, the retention anchor date, and how
    many reports are already archived — the read-only view, changes nothing."""
    files, newest = _collect(default_retention)
    by_cat = {}
    for f in files:
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    print(f"Live report files under management: {len(files)}")
    print(f"Newest report date (retention anchor): {newest}")
    for cat in sorted(by_cat):
        print(f"  {cat:20s} {by_cat[cat]:4d}")
    idx = _load_index()
    print(f"Already archived (intel/archive/index.json): {len(idx.get('archived', []))}")


def _tarball_path(category, ym):
    return os.path.join(ARCHIVE_DIR, f"{category}-{ym}.tar.gz")


def _archive_into_tarball(tar_path, members, apply):
    """Read-modify-write a gzip tarball, adding `members` (list of (arcname,
    bytes)). gzip streams can't be appended in place, so we recompose: copy
    any existing members, then add the new ones. Cheap because it only ever
    happens per (category, month) and a sealed month is never revisited."""
    existing = {}
    if os.path.exists(tar_path):
        with tarfile.open(tar_path, "r:gz") as tf:
            for m in tf.getmembers():
                existing[m.name] = tf.extractfile(m).read()
    for arcname, data in members:
        existing[arcname] = data  # new content wins on the rare re-add
    if not apply:
        return sorted(existing.keys())
    os.makedirs(os.path.dirname(tar_path), exist_ok=True)
    with tarfile.open(tar_path, "w:gz") as tf:
        for arcname in sorted(existing):
            data = existing[arcname]
            info = tarfile.TarInfo(name=arcname)
            info.size = len(data)
            info.mtime = 0  # deterministic — identical content -> identical tar
            tf.addfile(info, io.BytesIO(data))
    return sorted(existing.keys())


def archive(retention_days, apply):
    """Fold every report older than its category's retention window into the
    matching monthly tarball, record its metadata in index.json, and (when
    apply) remove the live file. Dry-run (apply=False) reports what would move
    and writes nothing. Idempotent — already-archived reports are skipped."""
    files, newest = _collect(retention_days)
    if newest is None:
        print("No report files found — nothing to archive.")
        return
    newest_ord = newest.toordinal()
    idx = _load_index()
    already = {(a["category"], a["file"]) for a in idx.get("archived", [])}

    # Group the archivable files by (category, YYYY-MM). A file is archivable
    # when it's older than ITS OWN category's retention window (internal churn
    # ages out fast; indexed reports linger), measured from the newest report.
    buckets = {}
    for f in files:
        if f["date"].toordinal() >= newest_ord - f["retention"]:
            continue  # inside this category's retention window — leave live
        if (f["category"], f["name"]) in already:
            continue  # idempotent — already archived on a prior run
        ym = f["date"].strftime("%Y-%m")
        buckets.setdefault((f["category"], ym), []).append(f)

    if not buckets:
        print("Nothing to archive: everything is within its category's retention "
              f"window of the newest report ({newest}) or already archived.")
        return

    new_records, archived_paths, total = [], [], 0
    for (category, ym), group in sorted(buckets.items()):
        members = []
        for f in group:
            txt = _read(f["path"])
            members.append((f["name"], txt.encode("utf-8")))
            archived_paths.append(f["path"])
            new_records.append({
                "category": category,
                "file": f["name"],
                "date": f["date"].isoformat(),
                "type": category,
                "title": _first_heading(txt, f["name"]),
                "threat": _threat(txt),
                "summary": _summary(txt),
                "indexed": f["indexed"],
                "tarball": f"intel/archive/{category}-{ym}.tar.gz",
                "sha256": hashlib.sha256(txt.encode("utf-8")).hexdigest(),
            })
        tar_path = _tarball_path(category, ym)
        _archive_into_tarball(tar_path, members, apply)
        total += len(group)
        action = "would archive" if not apply else "archived"
        print(f"{action} {len(group):3d} -> {os.path.relpath(tar_path, ROOT)}")

    if apply:
        # Persist the metadata index BEFORE deleting any live file. The bytes
        # already live in the tarball at this point; if we deleted first and
        # crashed before writing the index, those reports would be recoverable
        # from the tarball but no longer findable by metadata, and a re-run
        # wouldn't fix it (_collect no longer sees the deleted files). Writing
        # the index first means the worst a crash can do is leave a live file
        # that's already safely in a tarball — harmless, and a re-run cleans it.
        idx.setdefault("archived", []).extend(new_records)
        idx["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        idx["retention_days"] = retention_days
        idx["count"] = len(idx["archived"])
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        with open(ARCHIVE_INDEX, "w", encoding="utf-8") as f:
            json.dump(idx, f, indent=2)
        # Now remove exactly the files whose bytes were just written into a
        # tarball — no re-derivation from date/category, so a partial run can
        # never delete a file that wasn't successfully archived first.
        for path in archived_paths:
            os.remove(path)
        print(f"\nArchived {total} file(s); removed from live tree; "
              f"metadata recorded in {os.path.relpath(ARCHIVE_INDEX, ROOT)}.")
    else:
        print(f"\nDRY RUN — {total} file(s) would be archived. Re-run with --apply to execute.")


def main():
    ap = argparse.ArgumentParser(description="Archive old VAPE report files into monthly tarballs.")
    ap.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS,
                    help=f"Keep files newer than this many days live (default {DEFAULT_RETENTION_DAYS}).")
    ap.add_argument("--apply", action="store_true", help="Actually move/delete files (default is dry-run).")
    ap.add_argument("--stats", action="store_true", help="Print live report counts and exit.")
    args = ap.parse_args()
    if args.stats:
        stats(args.retention_days)
        return
    archive(args.retention_days, args.apply)


if __name__ == "__main__":
    main()
