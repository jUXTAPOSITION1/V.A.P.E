#!/usr/bin/env python3
"""
VAPE Intel Index Builder — zero-LLM, pure parsing.

Scans the repo's produced artifacts and emits a rich, machine-readable index the
GitHub Pages dashboard fetches to render pro, linkable summaries:

  data/intel-index.json
    - investigations : deep-investigation records (verdict, score, findings, links)
    - reports        : intel/reports/*.md + reports/bounty_report_*.md metadata
    - broadcasts     : intel/broadcasts/*.md metadata
    - tools          : skillforge tool registry (status, version, tier, purpose)
    - skills         : skillforge/skills/*.md playbooks
    - latest_summary : the freshest investigation + report headline for the hero card

Every entry carries a `url` (GitHub blob link) so the site can deep-link to the
exact source file. Real data only — this reads what VAPE actually produced.
"""
import os
import re
import io
import glob
import json
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "intel-index.json")
REPO = "jUXTAPOSITION1/V.A.P.E"
BLOB = f"https://github.com/{REPO}/blob/main"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path, limit=20000):
    try:
        with io.open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except Exception:
        return ""


def _rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def _first_heading(text, fallback=""):
    for ln in text.splitlines():
        s = ln.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return fallback


def _field(text, *labels):
    """Extract a '**Label:** value' or 'Label: value' field from markdown."""
    for label in labels:
        m = re.search(rf"\*?\*?{re.escape(label)}\*?\*?\s*[:：]\s*(.+)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip().strip("*").strip()
    return None


def _clean(p):
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", p)
    clean = re.sub(r"[*_`>#]", "", clean)
    return " ".join(clean.split())


def _verdict_rationale(text, max_len=300):
    """Investigation reports don't have an 'Executive Summary' heading, so the
    generic _summary() falls back to the leading '- Target: 0x... - Chain: ...'
    metadata bullets — restating fields already shown structurally, and
    dragging a bare 42-char address into free-flowing summary text (which
    overflows narrow mobile cards with no wrap opportunity). Pull the actual
    '## Verdict Rationale' bullets instead: the real "why", address-free."""
    m = re.search(r"##\s*Verdict Rationale\s*\n+(.+?)(?:\n##\s|\Z)", text, re.DOTALL)
    if not m:
        return None
    bullets = [_clean(ln).lstrip("- ").strip() for ln in m.group(1).splitlines() if ln.strip().startswith("-")]
    joined = " · ".join(b for b in bullets if b)
    return joined[:max_len] if joined else None


def _summary(text, max_len=340):
    """Prefer prose under a Summary/Executive Summary heading; else first
    substantive paragraph (skipping headings, tables, code fences)."""
    # 1) content right after a Summary-style heading
    m = re.search(r"#+\s*\S*\s*(?:Executive Summary|Summary|Overview)\s*\n+(.+?)(?:\n#+\s|\Z)",
                  text, re.IGNORECASE | re.DOTALL)
    if m:
        block = m.group(1)
        # collapse bullet lists / prose into one line
        parts = [_clean(ln) for ln in block.splitlines()
                 if ln.strip() and not ln.strip().startswith(("|", "---", "```"))]
        joined = " ".join(p for p in parts if len(p) > 3)
        if len(joined) > 40:
            return joined[:max_len]
    # 2) fallback: first substantive paragraph
    skip = False
    for para in re.split(r"\n\s*\n", text):
        p = para.strip()
        if p.startswith("```"):
            skip = not skip
            continue
        if skip or not p:
            continue
        if p.startswith("#") or p.startswith("|") or p.startswith(">") or p.startswith("---"):
            continue
        clean = _clean(p)
        if len(clean) > 40:
            return clean[:max_len]
    return ""


def _date_from_name(name):
    # intel: type-YYYY-MM-DD-HH.md ; bounty: bounty_report_YYYYMMDD_HHMMSS.md
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})-(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:00Z"
    m = re.search(r"(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}Z"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", name)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00Z"
    return ""


THREAT_RX = re.compile(r"(CRITICAL|HIGH|MEDIUM|LOW|ALL CLEAR|NEUTRAL|RISK-ON|RISK-OFF)", re.I)


def _threat(text):
    m = re.search(r"(?:Threat Level|Risk posture|Verdict|Market Mood|posture)\s*(?:is|:|：)?\s*\**\s*"
                  r"(CRITICAL|HIGH|MEDIUM|LOW|ALL CLEAR|RISK-ON|RISK-OFF|NEUTRAL|"
                  r"BULLISH|BEARISH|FEAR|GREED|PROCEED|CAUTION|REJECT)", text, re.I)
    return m.group(1).upper() if m else None


def scan_reports():
    """intel/reports/*.md + reports/bounty_report_*.md -> metadata list."""
    out = []
    patterns = [
        ("intel", "intel/reports/*.md"),
        ("bounty", "reports/bounty_report_*.md"),
    ]
    for kind, pat in patterns:
        for fp in glob.glob(os.path.join(ROOT, pat)):
            name = os.path.basename(fp)
            txt = _read(fp)
            rtype = kind
            if kind == "intel":
                mt = re.match(r"([a-z]+)-", name)
                rtype = mt.group(1) if mt else "intel"
            out.append({
                "kind": kind,
                "type": rtype,
                "file": name,
                "title": _first_heading(txt, name),
                "date": _date_from_name(name),
                "threat": _threat(txt),
                "summary": _summary(txt),
                "url": f"{BLOB}/{_rel(fp)}",
                "bytes": os.path.getsize(fp),
            })
    out.sort(key=lambda r: r["date"], reverse=True)
    return out


def scan_broadcasts():
    out = []
    for fp in glob.glob(os.path.join(ROOT, "intel/broadcasts/*.md")):
        name = os.path.basename(fp)
        txt = _read(fp)
        out.append({
            "file": name,
            "title": _first_heading(txt, name),
            "date": _date_from_name(name),
            "summary": _summary(txt),
            "url": f"{BLOB}/{_rel(fp)}",
        })
    out.sort(key=lambda r: r["date"], reverse=True)
    return out


def scan_investigations():
    """Structured investigation records from intel/investigations/*.md (new deep
    investigations) + the legacy catalog table rows."""
    out = []
    # 1) dedicated investigation reports
    for fp in sorted(glob.glob(os.path.join(ROOT, "intel/investigations/*.md")), reverse=True):
        name = os.path.basename(fp)
        txt = _read(fp)
        verdict_raw = _field(txt, "Verdict") or ""
        vm = re.search(r"(PROCEED|CAUTION|REJECT)", verdict_raw, re.I)
        score_raw = _field(txt, "Safety Score", "Score") or ""
        sm = re.search(r"(\d{1,3})", score_raw)
        target_raw = _field(txt, "Target") or ""
        target = re.sub(r"[`*]", "", target_raw).strip()
        title = _first_heading(txt, name)
        sym_m = re.search(r"Investigation\s*[—-]\s*(.+)$", title)
        symbol = sym_m.group(1).strip() if sym_m else None
        out.append({
            "source": "report",
            "file": name,
            "title": title,
            "symbol": symbol,
            "date": _field(txt, "Date", "Cycle") or _date_from_name(name),
            "target": target or None,
            "chain": re.sub(r"[`*]", "", _field(txt, "Chain") or "").strip() or None,
            "verdict": vm.group(1).upper() if vm else None,
            "score": sm.group(1) if sm else None,
            "summary": _verdict_rationale(txt) or _summary(txt),
            "url": f"{BLOB}/{_rel(fp)}",
        })
    # 2) legacy catalog table
    cat = os.path.join(ROOT, "intel/catalog/investigation-catalog.md")
    if os.path.exists(cat):
        for ln in _read(cat).splitlines():
            cells = [c.strip() for c in ln.split("|") if c.strip()]
            if len(cells) >= 6 and re.match(r"\d{4}-\d{2}-\d{2}", cells[0]):
                target_cell = cells[2] if len(cells) > 2 else ""
                tm = re.match(r"(0x[a-fA-F0-9]{40})\s*(?:\(([^)]+)\))?", target_cell)
                out.append({
                    "source": "catalog",
                    "date": cells[0],
                    "job_id": cells[1] if len(cells) > 1 else None,
                    "target": tm.group(1) if tm else (target_cell or None),
                    "symbol": tm.group(2) if tm and tm.group(2) else None,
                    "offering": cells[3] if len(cells) > 3 else None,
                    "verdict": cells[4] if len(cells) > 4 else None,
                    "key_finding": cells[5] if len(cells) > 5 else None,
                    "url": f"{BLOB}/intel/catalog/investigation-catalog.md",
                })
    return out


def scan_tools():
    p = os.path.join(ROOT, "skillforge/memory/tools-registry.json")
    tools = []
    try:
        reg = json.load(open(p))
    except Exception:
        return tools
    for tier, items in (reg.get("tiers") or {}).items():
        seq = items if isinstance(items, list) else list(items.values())
        for t in seq:
            if not isinstance(t, dict):
                continue
            wrapper = t.get("wrapper")
            tools.append({
                "name": t.get("name"),
                "tier": tier,
                "status": t.get("status"),
                "version": t.get("version"),
                "purpose": t.get("purpose"),
                "repo": t.get("repo"),
                "known_limitation": bool(t.get("known_limitation")),
                "url": f"{BLOB}/skillforge/{wrapper}" if wrapper else t.get("repo"),
            })
    return tools


def scan_skills():
    out = []
    for fp in glob.glob(os.path.join(ROOT, "skillforge/skills/*.md")):
        txt = _read(fp)
        out.append({
            "file": os.path.basename(fp),
            "title": _first_heading(txt, os.path.basename(fp)),
            "summary": _summary(txt, 220),
            "url": f"{BLOB}/{_rel(fp)}",
        })
    out.sort(key=lambda s: s["title"])
    return out


def main():
    reports = scan_reports()
    broadcasts = scan_broadcasts()
    investigations = scan_investigations()
    tools = scan_tools()
    skills = scan_skills()

    latest_report = reports[0] if reports else None
    latest_invest = next((i for i in investigations if i.get("source") == "report"), None) \
        or (investigations[0] if investigations else None)

    by_type = {}
    for r in reports:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1

    index = {
        "generated": now(),
        "repo": REPO,
        "counts": {
            "reports": len(reports),
            "reports_by_type": by_type,
            "broadcasts": len(broadcasts),
            "investigations": len(investigations),
            "tools": len(tools),
            "tools_verified": sum(1 for t in tools if t.get("status") == "verified"),
            "skills": len(skills),
        },
        "latest_summary": {
            "investigation": latest_invest,
            "report": latest_report,
        },
        "investigations": investigations[:40],
        "reports": reports[:60],
        "broadcasts": broadcasts[:30],
        "tools": tools,
        "skills": skills,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(index, f, indent=2)
    print(json.dumps({"wrote": _rel(OUT), **index["counts"]}, indent=2))


if __name__ == "__main__":
    main()
