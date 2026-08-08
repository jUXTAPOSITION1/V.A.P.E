#!/usr/bin/env python3
"""
VAPE Memory SQLite Index — queryable recall over the append-only JSONL memory.

Design (matches VAPE's model): ZERO new dependencies (stdlib `sqlite3` only),
NON-destructive (JSONL files stay the source of truth), rebuildable any time.
The append-only logs remain the audit trail; this DB is a derived, queryable
projection so agents can ask real questions instead of scanning flat files:

  "high-confidence Base findings in the last 30 days"
  "every CAUTION/REJECT investigation verdict"
  "count findings by category/severity"

Usage:
  python -m skillforge.memory.index_db build          # (re)build data/memory.db
  python -m skillforge.memory.index_db query "<text>" [--category finding] [--days 30]
  python -m skillforge.memory.index_db stats

It reuses the retriever's normalizer so legacy + new schemas both index cleanly.
Full-text search uses SQLite FTS5 when available, else a LIKE fallback.
"""
import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DB_PATH = os.path.join(ROOT, "data", "memory.db")

try:
    from skillforge.memory.retriever import _load_all_entries
except Exception:  # pragma: no cover - allow direct execution
    from retriever import _load_all_entries  # type: ignore


def _fts_available(conn):
    try:
        conn.execute("CREATE VIRTUAL TABLE _fts_probe USING fts5(x)")
        conn.execute("DROP TABLE _fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def _connect():
    # This index is explicitly a derived, rebuildable projection (see module
    # docstring) -- the JSONL files remain the real source of truth. A
    # read-only DB_PATH parent (e.g. this package installed into
    # site-packages, as mcp_servers/vape_mcp.py's PyPI distribution now is)
    # must degrade to "no Memory index available here", not crash query()/
    # stats()/build() outright over a directory that's pure convenience.
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"memory index unavailable: cannot create {os.path.dirname(DB_PATH)!r}: {e}") from e
    return sqlite3.connect(DB_PATH)


def build():
    """Rebuild the SQLite projection from the JSONL memory files."""
    entries = _load_all_entries()
    conn = _connect()
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS entries;
        CREATE TABLE entries (
            rowid       INTEGER PRIMARY KEY,
            id          TEXT,
            category    TEXT,
            title       TEXT,
            content     TEXT,
            source      TEXT,
            tags        TEXT,
            confidence  REAL,
            severity    TEXT,
            timestamp   TEXT,
            metadata    TEXT
        );
        CREATE INDEX idx_category   ON entries(category);
        CREATE INDEX idx_confidence ON entries(confidence);
        CREATE INDEX idx_timestamp  ON entries(timestamp);
        CREATE INDEX idx_severity   ON entries(severity);
        """
    )
    rows = []
    for e in entries:
        meta = e.get("metadata") or {}
        rows.append((
            e.get("id", ""),
            e.get("category", ""),
            e.get("title", ""),
            e.get("content", ""),
            e.get("source", ""),
            ",".join(e.get("tags", []) or []),
            float(e.get("confidence", 0) or 0),
            str(meta.get("severity", "") or ""),
            e.get("timestamp", ""),
            json.dumps(meta, default=str),
        ))
    cur.executemany(
        "INSERT INTO entries "
        "(id,category,title,content,source,tags,confidence,severity,timestamp,metadata) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        rows,
    )

    fts = _fts_available(conn)
    if fts:
        cur.executescript(
            """
            DROP TABLE IF EXISTS entries_fts;
            CREATE VIRTUAL TABLE entries_fts USING fts5(
                title, content, tags, content='entries', content_rowid='rowid'
            );
            INSERT INTO entries_fts(rowid, title, content, tags)
                SELECT rowid, title, content, tags FROM entries;
            """
        )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    conn.close()
    return {"db": os.path.relpath(DB_PATH, ROOT), "indexed": n, "fts": fts}


def query(text="", category=None, days=None, min_confidence=0.0, limit=20):
    """Query the index. Returns a list of dict rows. Auto-builds if missing."""
    if not os.path.exists(DB_PATH):
        build()
    conn = _connect()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    where, params = [], []

    use_fts = False
    if text:
        try:
            conn.execute("SELECT 1 FROM entries_fts LIMIT 1")
            use_fts = True
        except sqlite3.OperationalError:
            use_fts = False

    if text and use_fts:
        base = ("SELECT e.* FROM entries_fts f JOIN entries e ON e.rowid=f.rowid "
                "WHERE entries_fts MATCH ?")
        params.append(_fts_query(text))
    else:
        base = "SELECT * FROM entries e WHERE 1=1"
        if text:
            where.append("(title LIKE ? OR content LIKE ? OR tags LIKE ?)")
            like = f"%{text}%"
            params += [like, like, like]

    if category:
        where.append("category = ?")
        params.append(category)
    if min_confidence:
        where.append("confidence >= ?")
        params.append(float(min_confidence))
    if days:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()
        where.append("timestamp >= ?")
        params.append(cutoff)

    sql = base + ("".join(f" AND {w}" for w in where))
    sql += " ORDER BY confidence DESC, timestamp DESC LIMIT ?"
    params.append(int(limit))

    rows = [dict(r) for r in cur.execute(sql, params).fetchall()]
    conn.close()
    for r in rows:
        r["tags"] = [t for t in (r.get("tags") or "").split(",") if t]
        try:
            r["metadata"] = json.loads(r.get("metadata") or "{}")
        except Exception:
            r["metadata"] = {}
    return rows


def _fts_query(text):
    """Sanitize free text into a safe FTS5 OR-query of prefix tokens."""
    toks = [t for t in "".join(c if c.isalnum() else " " for c in text).split() if t]
    return " OR ".join(f"{t}*" for t in toks) or text


def stats():
    if not os.path.exists(DB_PATH):
        build()
    conn = _connect()
    cur = conn.cursor()
    out = {"total": cur.execute("SELECT COUNT(*) FROM entries").fetchone()[0]}
    out["by_category"] = dict(cur.execute(
        "SELECT category, COUNT(*) FROM entries GROUP BY category").fetchall())
    out["by_severity"] = dict(cur.execute(
        "SELECT severity, COUNT(*) FROM entries WHERE severity!='' GROUP BY severity"
    ).fetchall())
    out["high_confidence"] = cur.execute(
        "SELECT COUNT(*) FROM entries WHERE confidence >= 0.8").fetchone()[0]
    conn.close()
    return out


def main():
    ap = argparse.ArgumentParser(description="VAPE Memory SQLite index")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("build")
    q = sub.add_parser("query")
    q.add_argument("text", nargs="?", default="")
    q.add_argument("--category")
    q.add_argument("--days", type=int)
    q.add_argument("--min-confidence", type=float, default=0.0)
    q.add_argument("--limit", type=int, default=20)
    sub.add_parser("stats")
    args = ap.parse_args()

    if args.cmd == "build":
        print(json.dumps(build(), indent=2))
    elif args.cmd == "query":
        print(json.dumps(query(args.text, args.category, args.days,
                               args.min_confidence, args.limit), indent=2))
    elif args.cmd == "stats":
        print(json.dumps(stats(), indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
