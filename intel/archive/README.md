# intel/archive/ — cold storage for aged reports

Nothing here is lost, deleted, or fabricated away — this is the same real,
dated report output that used to live loose in `reports/` and
`intel/reports/`, folded into one compressed tarball per (category, month)
once it aged past its retention window. It keeps the working tree browsable
and fast (fewer loose files, quicker `git` operations and glob/jsonl scans)
without giving up a single byte of the audit trail.

Written by [`scripts/archive_reports.py`](../../scripts/archive_reports.py)
on the weekly [`archive-reports.yml`](../../.github/workflows/archive-reports.yml)
schedule.

## What's here

- `*-YYYY-MM.tar.gz` — every archived report for that category and month,
  stored verbatim (byte-identical to the original file).
- `index.json` — the queryable manifest: for every archived report, its
  `file`, `date`, `type`, `title`, `threat`, `summary`, `tarball`, and a
  `sha256` of the original bytes. Nothing in the archive is findable only by
  cracking open a tarball — the metadata a reader (or VAPE itself) would want
  stays in plain JSON.

## Restore a single report

```bash
python - <<'PY'
import json, tarfile
name = "security-2026-06-10-08.md"          # the report you want back
rec = next(r for r in json.load(open("intel/archive/index.json"))["archived"] if r["file"] == name)
with tarfile.open(rec["tarball"]) as tf:
    open(name, "wb").write(tf.extractfile(name).read())
print("restored", name, "— verify sha256:", rec["sha256"])
PY
```

## Restore a whole month

```bash
tar -xzf intel/archive/intel_reports-2026-06.tar.gz -C intel/reports/
```

## Why tarballs, not deletion or a rewritten history

The originals stay in git history regardless; archiving is about the *working
tree*, not the past. A monthly tarball is written at most a few times (only
while its month is the retention boundary) and then frozen, so it adds far
less commit churn than hundreds of individually-committed loose files — while
keeping everything transparent, in-repo, and trivially reversible, exactly
the project's real-data-only ethos.
