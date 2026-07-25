"""
BOUNTY OPS — Task #197: VAPE's classified, checklist-tracked live bounty-ops
system, built directly on top of agents/scout.py's track/vapeFit fix (Task
#196): opportunities.json now distinguishes real live bounty PROGRAMS
(track="bounty") that genuinely match VAPE's own tooling (Solidity/EVM via
agents/deep_dive_audit.py, or Move/Sui via agents/external_audit.py) from
historical DeFiLlama hack INCIDENTS (track="incident", a separate forensics
workflow with its own home — the Threat Ledger).

This module selects the top VAPE-fit bounty programs and, for each one VAPE
is actually tracking, generates/refreshes a real checklist via Grok 4.3 —
what to actually do, what VAPE tooling to run, what to check against
skillforge/memory/security_standards.json's real vulnerability taxonomy —
and maintains a recurring progress log. Never a fabricated task list: on
any LLM failure the entry is written with an empty checklist and honestly
marked so, exactly like every other LLM call in this repo
(agents/scout.py::_strategic_briefing, agents/external_audit.py, etc).

Cross-references VAPE's own real audit output (intel/audits/poc-reports/,
intel/audits/hack-sweep-reports/, intel/audits/external-bounties/) by
filename token overlap, so a bounty-ops entry links straight to VAPE's real
report the moment one exists — never a fabricated "in progress" claim.

Idempotent, append-only-on-change (same discipline as agents/engagements.py):
- A checklist item's `done` state, once set, is NEVER reset by a later run —
  only genuinely new items (no existing item's text is a close match) get
  appended.
- The checklist TEXT itself is only regenerated (a real LLM call) if the
  program has no checklist yet, or its last generation is more than
  CHECKLIST_REFRESH_DAYS old — recurring, but bounded, matching the "no
  cheap LLM-cost churn on every run" pattern.
- progress_log gains a new entry only when something actually changed this
  run (new program tracked, checklist regenerated, VAPE report newly
  linked) — never a duplicate no-op entry.

Output: intel/bounty-radar/bounty-ops/<slug>.json per tracked program +
intel/bounty-radar/bounty-ops/INDEX.md (human rollup, regenerated each run).

Usage: python -m agents.bounty_ops
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import scout  # noqa: E402  (reuses opportunities.json + its track/vapeFit classification)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOUNTY_OPS_DIR = os.path.join(_REPO_ROOT, "intel", "bounty-radar", "bounty-ops")
INDEX_PATH = os.path.join(BOUNTY_OPS_DIR, "INDEX.md")

# Real, already-committed directories where VAPE's own tooling files a
# report — checked for a name-token match so a bounty-ops entry can link
# straight to VAPE's own real work the moment it exists.
REPORT_DIRS = [
    ("intel/audits/poc-reports", "audit"),
    ("intel/audits/hack-sweep-reports", "hack-sweep"),
    ("intel/audits/external-bounties", "external-audit"),
]

MAX_TRACKED = 12                # bounded — one real LLM call per NEW/stale entry, not unbounded spend
CHECKLIST_REFRESH_DAYS = 7      # how often a program's checklist text gets regenerated
BOUNTY_FIT_THRESHOLD = scout.BOUNTY_FIT_THRESHOLD_DIGEST

CHECKLIST_SYSTEM = (
    "You are VAPE's bounty-ops planner. VAPE is an autonomous security agent whose only real "
    "tooling is: agents/deep_dive_audit.py (Solidity/EVM — recon, Slither, Halmos symbolic "
    "execution, Mythril, Aderyn static AST analysis, frontier-LLM review) and "
    "agents/external_audit.py (Move/Sui — source fetch, Move Prover/sui-prover formal "
    "verification where applicable, frontier-LLM review). Given one real bug-bounty program's "
    "details below, write a short, concrete, ORDERED checklist (6-10 items) of what VAPE should "
    "actually do to engage with it for real — starting from confirming real scope/rules, through "
    "which of the two tools above to run and on what target, to what to check manually against a "
    "real vulnerability taxonomy (access control, oracle trust, reentrancy, business logic), to "
    "what a real submission requires. If the program's URL below doesn't tell you enough to "
    "confirm current scope/rules/payout tiers, make the first checklist item an explicit "
    "instruction to verify that directly against the program's real page before doing anything "
    "else — never guess at scope/rules/payout details you weren't actually given. One item "
    "per line, each starting with '- '. No preamble, "
    "no numbering, no markdown headers — just the bullet lines."
)


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return s or "unknown"


def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def select_candidates(opportunities, limit=MAX_TRACKED):
    """Real, VAPE-fit, live bounty programs only — track="bounty" +
    vapeFit=True (agents/scout.py's classification), ranked by
    bountyFitScore, deduped by id. Never an incident, never a non-fit
    program regardless of its headline dollar size."""
    fit = [o for o in opportunities
           if o.get("track") == "bounty" and o.get("vapeFit")
           and o.get("bountyFitScore", 0) >= BOUNTY_FIT_THRESHOLD]
    fit.sort(key=lambda o: o.get("bountyFitScore", 0), reverse=True)
    seen_ids = set()
    out = []
    for o in fit:
        if o.get("id") in seen_ids:
            continue
        seen_ids.add(o.get("id"))
        out.append(o)
        if len(out) >= limit:
            break
    return out


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(text):
    return set(_TOKEN_RE.findall(str(text).lower()))


def find_vape_report(name):
    """Name-token overlap match against VAPE's own real, already-committed
    report directories. Returns (relative_path, kind) or (None, None) — no
    match is an honest "not engaged yet," never fabricated."""
    name_tokens = _tokens(name) - {"smart", "contracts", "contract", "protocol", "the", "and"}
    if not name_tokens:
        return None, None
    # Fewer distinctive tokens (e.g. just "smardex") need a lower bar than a
    # multi-word name — a single match on a genuinely distinctive token is
    # still meaningful since generic filler words are already stripped above.
    required = 1 if len(name_tokens) <= 2 else 2
    best = (None, None, 0)
    for rel_dir, kind in REPORT_DIRS:
        abs_dir = os.path.join(_REPO_ROOT, rel_dir)
        if not os.path.isdir(abs_dir):
            continue
        for fname in os.listdir(abs_dir):
            if not fname.endswith(".md"):
                continue
            file_tokens = _tokens(fname)
            overlap = len(name_tokens & file_tokens)
            if overlap >= required and overlap > best[2]:
                best = (os.path.join(rel_dir, fname), kind, overlap)
    return best[0], best[1]


def _parse_checklist_text(text):
    items = []
    for line in (text or "").splitlines():
        line = line.strip()
        if line.startswith(("- ", "* ")):
            item_text = line[2:].strip()
        elif re.match(r"^\d+[.)]\s+", line):
            item_text = re.sub(r"^\d+[.)]\s+", "", line).strip()
        else:
            continue
        if item_text:
            items.append(item_text)
    return items


def generate_checklist(candidate):
    """Real OCI Grok 4.3 call (via ask_oci_grok_safe, tier="frontier" +
    FRONTIER_ORDER — same as every other narrative call in this repo) —
    returns a list of checklist item strings, or [] on any unavailability/
    failure. Never fabricates items when the LLM is unreachable. search is
    intentionally omitted (defaults False) — passing it would skip past OCI
    Grok/Vertex entirely into the free FRONTIER_ORDER chain (neither has a
    search-grounding equivalent — see agents/llm.py::ask_oci_grok()'s own
    docstring); CHECKLIST_SYSTEM instead tells the model to make "verify
    current scope/rules" an explicit checklist item rather than guessing."""
    try:
        from agents.llm import ask_oci_grok_safe, FRONTIER_ORDER
    except Exception:
        return []
    user = (
        f"Program: {candidate.get('name')}\n"
        f"Platform: {candidate.get('platform')}\n"
        f"URL: {candidate.get('url')}\n"
        f"Prize: ${candidate.get('prizeUsd', 0):,.0f}\n"
        f"Why it fits VAPE: {candidate.get('vapeFitReason', '')}\n"
        f"Tags: {', '.join(candidate.get('tags', []))}\n"
    )
    try:
        text, _provider = ask_oci_grok_safe(CHECKLIST_SYSTEM, user, tier="frontier",
                                             provider_order=FRONTIER_ORDER, max_tokens=700, temperature=0.3)
    except Exception as e:
        print(f"[bounty_ops] checklist generation failed for {candidate.get('name')}: {e}")
        return []
    if not text or text.startswith("[llm unavailable"):
        return []
    return _parse_checklist_text(text)


def _merge_checklist_items(existing_items, new_texts):
    """Never resets a done flag, never drops an existing item. Only appends
    genuinely new item text (no existing item is an exact match)."""
    existing_texts = {i["item"] for i in existing_items}
    merged = list(existing_items)
    added = 0
    for t in new_texts:
        if t not in existing_texts:
            merged.append({"item": t, "done": False})
            added += 1
    return merged, added


def _append_progress(entry, event):
    log = entry.setdefault("progress", [])
    if log and log[-1].get("event") == event:
        return False
    log.append({"ts": scout._now_iso(), "event": event})
    return True


def build_entry(candidate, existing):
    """Pure-ish (one possible real LLM call) construction of one bounty-ops
    JSON record. `existing` is the prior on-disk record for this program
    (or None) — checklist done-state and progress history are always
    preserved across regeneration."""
    now = time.time()
    entry = existing.copy() if existing else {
        "id": candidate.get("id"), "checklist": [], "progress": [],
        "checklistGeneratedAt": None, "vapeReportUrl": None,
    }
    changed_anything = existing is None

    entry.update({
        "id": candidate.get("id"),
        "name": candidate.get("name"),
        "platform": candidate.get("platform"),
        "url": candidate.get("url"),
        "prizeUsd": candidate.get("prizeUsd", 0),
        "bountyFitScore": candidate.get("bountyFitScore", 0),
        "vapeFitReason": candidate.get("vapeFitReason", ""),
        "tags": candidate.get("tags", []),
        "updatedAt": scout._now_iso(),
    })

    if existing is None:
        _append_progress(entry, f"Started tracking as a real Bounty Op (fit {candidate.get('bountyFitScore', 0)}).")

    needs_checklist = (
        not entry.get("checklist")
        or not entry.get("checklistGeneratedAt")
        or (now - entry["checklistGeneratedAt"]) > CHECKLIST_REFRESH_DAYS * 86400
    )
    if needs_checklist:
        new_texts = generate_checklist(candidate)
        if new_texts:
            entry["checklist"], added = _merge_checklist_items(entry.get("checklist", []), new_texts)
            entry["checklistGeneratedAt"] = now
            changed_anything = True
            if added:
                _append_progress(entry, f"Checklist refreshed — {added} new item(s) from Grok 4.3.")

    report_path, report_kind = find_vape_report(candidate.get("name", ""))
    if report_path and entry.get("vapeReportUrl") != report_path:
        entry["vapeReportUrl"] = report_path
        entry["vapeReportKind"] = report_kind
        changed_anything = True
        _append_progress(entry, f"Linked VAPE's own real {report_kind} report: {report_path}")

    return entry, changed_anything


def _render_index(entries):
    now = datetime.now(timezone.utc)
    L = [f"# VAPE Bounty Ops — {now.strftime('%Y-%m-%dT%H:%M:%SZ')}", "",
         "Real, classified, checklist-tracked live bug-bounty programs VAPE has actually vetted "
         "as matching its own tooling (Solidity/EVM via agents/deep_dive_audit.py, or Move/Sui via "
         "agents/external_audit.py) — never historical exploits (those live in the Threat Ledger) "
         "and never a post-incident recovery/negotiation offer regardless of its headline dollar "
         "size. See agents/scout.py and agents/bounty_ops.py for the real classification/scoring "
         "and checklist-generation logic.", ""]
    if not entries:
        L.append("No program currently clears the Bounty Ops fit threshold.")
        L.append("")
        return "\n".join(L)
    entries = sorted(entries, key=lambda e: e.get("bountyFitScore", 0), reverse=True)
    for e in entries:
        done = sum(1 for i in e.get("checklist", []) if i.get("done"))
        total = len(e.get("checklist", []))
        prize = f"${e['prizeUsd']:,.0f}" if e.get("prizeUsd") else "—"
        L.append(f"## [{e['name']}]({e.get('url', '#')}) — {e.get('platform', '')}, {prize}, fit {e.get('bountyFitScore', 0)}")
        L.append(f"- Why it fits: {e.get('vapeFitReason', '')}")
        L.append(f"- Checklist progress: {done}/{total}" if total else "- Checklist: not yet generated")
        if e.get("vapeReportUrl"):
            L.append(f"- VAPE's own report: [{e['vapeReportKind']}]({e['vapeReportUrl']})")
        L.append("")
    return "\n".join(L)


def run(limit=MAX_TRACKED):
    opportunities = _load_json(scout.OPPORTUNITIES_PATH, [])
    if not isinstance(opportunities, list):
        opportunities = []
    candidates = select_candidates(opportunities, limit=limit)

    os.makedirs(BOUNTY_OPS_DIR, exist_ok=True)
    new_count, updated_count = 0, 0
    entries = []
    for c in candidates:
        slug = _slug(c.get("name", c.get("id", "unknown")))
        path = os.path.join(BOUNTY_OPS_DIR, f"{slug}.json")
        existing = _load_json(path, None)
        entry, changed = build_entry(c, existing)
        entries.append(entry)
        if changed:
            _save_json(path, entry)
            if existing is None:
                new_count += 1
            else:
                updated_count += 1

    with open(INDEX_PATH, "w") as f:
        f.write(_render_index(entries))

    print(f"[bounty_ops] {len(candidates)} VAPE-fit bounty program(s) tracked, "
          f"{new_count} newly tracked, {updated_count} updated this run.")
    return {"tracked": len(candidates), "new": new_count, "updated": updated_count}


if __name__ == "__main__":
    run()
