"""
VAPE Engagements — revives intel/engagements/.

What was there before (now moved to intel/archive/legacy-seed-engagements/,
never deleted): a templated "SomeProtocol" Code4rena stub with a fake scope
URL, cold-outreach email drafts to real DeFi hack victims sent from a
personal gmail address, and an engagement-log.jsonl recording those as if
they were real actions. None of it was ever backed by live code — a
repo-wide search turns up zero references to intel/engagements/ outside
that directory itself. It's pre-repo seed data from the same "ad hoc
Claude Code session" era flagged in security_sweep.py's module docstring,
not something VAPE's current pipeline ever produced.

This module replaces it with something real: for every high-fit bounty-radar
lead VAPE is actually tracking (intel/bounty-radar/opportunities.json), it
records what VAPE's own automated pipeline genuinely did about it — never
a fabricated account signup or an email nobody sent.

  - defillama-hack incident leads: the real record is
    skillforge/memory/attack_response_state.json, written by
    agents/security_sweep.py's attempt_incident_forensics() (also the
    action step agents/scout.py's _act_on_incidents() delegates to hourly).
    resolved=True means a real agents/investigate.py investigation ran —
    cite the real address/verdict/report. resolved=False means a real
    search ran and honestly found no verifiable on-chain target. Neither
    key present yet means it hasn't been attempted this incident's way
    through the pipeline (chain unsupported, below the age/value gate, or
    simply not reached yet).
  - static seed-platform leads (Immunefi, Cantina, Sherlock, HackerOne,
    HackenProof, AgentArena): VAPE has no real account or submission
    mechanism for any of these today — the honest record is "tracked for
    visibility, no automated engagement path," not a fictional signup
    checklist.

Output is a single always-current intel/engagements/STATUS.md (overwritten
each run — a snapshot, not a growing pile of near-duplicate dated files)
plus an idempotent intel/engagements/engagement-log.jsonl that gains a new
line only the first time a given lead's status changes (matching the same
idempotent-state-file pattern as attack_response_state.json/lessons.jsonl
elsewhere in this repo) — a real history of status transitions, not a
replay of the same snapshot every cycle.

Usage: python -m agents.engagements
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import intel_common as ic  # noqa: E402

INTEL_DIR = os.path.join(ic.ROOT, "intel", "engagements")
STATUS_PATH = os.path.join(INTEL_DIR, "STATUS.md")
LOG_PATH = os.path.join(INTEL_DIR, "engagement-log.jsonl")
LOG_STATE_PATH = os.path.join(ic.ROOT, "skillforge", "memory", "engagement_log_state.json")
OPPORTUNITIES_PATH = os.path.join(ic.ROOT, "intel", "bounty-radar", "opportunities.json")
RESPONSE_STATE_PATH = os.path.join(ic.ROOT, "skillforge", "memory", "attack_response_state.json")

FIT_THRESHOLD = 50  # matches scout.py's own digest convention

# Platforms bundled in as static seed data at repo import (no public,
# keyless, stable API to poll — see agents/scout.py's module docstring).
# VAPE has no real account/submission mechanism for any of these.
STATIC_SEED_PLATFORMS = {
    "immunefi", "cantina", "sherlock", "hackerone", "hackenproof", "agentarena", "code4rena",
}

_ID_RE = re.compile(r"^defillama-hack:(.+)-(\d+)$")


def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _incident_state_key(opp):
    """Reconstruct attempt_incident_forensics()'s own state key
    (f"{date}:{name}") from an opportunities.json entry's id
    (f"defillama-hack:{name}-{date_unix}") — the two modules key their
    state differently, so this is the one place that has to bridge them."""
    m = _ID_RE.match(opp.get("id", ""))
    if not m:
        return None
    name, date_unix = m.group(1), m.group(2)
    try:
        date_str = datetime.fromtimestamp(int(date_unix), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None
    return f"{date_str}:{name}"


def _engagement_for(opp, response_state):
    platform = opp.get("platform", "")
    if platform == "defillama-hack":
        key = _incident_state_key(opp)
        resolved = response_state.get(key) if key else None
        if resolved is None:
            return {"status": "not_yet_attempted"}
        if resolved.get("resolved"):
            return {
                "status": "investigated",
                "address": resolved.get("address"),
                "chain": resolved.get("chain", "8453"),
                "verdict": resolved.get("verdict"),
                "report": resolved.get("report"),
                "checked_at": resolved.get("checked_at"),
            }
        return {"status": "no_target_found", "checked_at": resolved.get("checked_at")}
    if platform in STATIC_SEED_PLATFORMS:
        return {"status": "tracked_only",
                "note": "No automated engagement path — would need a real account/manual "
                        "submission, not simulated by VAPE."}
    return {"status": "tracked_only", "note": "No automated engagement path for this platform yet."}


def build_engagements(opportunities, response_state):
    """Pure: one real engagement record per high-fit lead. No LLM, no
    fabricated action — see module docstring for the per-platform rule."""
    out = []
    for opp in opportunities:
        if (opp.get("fitScore") or 0) < FIT_THRESHOLD:
            continue
        out.append({
            "lead": opp.get("name"),
            "platform": opp.get("platform"),
            "prizeUsd": opp.get("prizeUsd", 0),
            "fitScore": opp.get("fitScore", 0),
            "url": opp.get("url"),
            "engagement": _engagement_for(opp, response_state),
        })
    out.sort(key=lambda e: e["fitScore"], reverse=True)
    return out


def _render_status_md(engagements):
    now = datetime.now(timezone.utc)
    L = [f"# VAPE Engagement Status — {now.strftime('%Y-%m-%dT%H:%M:%SZ')}", "",
         f"Real record of what VAPE's automated pipeline has actually done about each "
         f"tracked lead with fit>={FIT_THRESHOLD}. Never a fabricated account signup or "
         "an email nobody sent — see agents/engagements.py's module docstring.", ""]
    if not engagements:
        L.append("No leads currently meet the fit threshold.")
        L.append("")
        return "\n".join(L)

    investigated = [e for e in engagements if e["engagement"]["status"] == "investigated"]
    no_target = [e for e in engagements if e["engagement"]["status"] == "no_target_found"]
    not_yet = [e for e in engagements if e["engagement"]["status"] == "not_yet_attempted"]
    tracked = [e for e in engagements if e["engagement"]["status"] == "tracked_only"]

    if investigated:
        L += ["## Real investigations launched", ""]
        for e in investigated:
            eng = e["engagement"]
            L.append(f"- **{e['lead']}** (${e['prizeUsd']:,.0f}, fit {e['fitScore']}) — "
                      f"address `{eng['address']}` (chain {eng['chain']}), "
                      f"verdict **{eng['verdict']}** — [report]({eng['report']})")
        L.append("")
    if no_target:
        L += ["## Searched, no verifiable on-chain target found", ""]
        for e in no_target:
            L.append(f"- {e['lead']} (${e['prizeUsd']:,.0f}, fit {e['fitScore']}) — "
                      f"checked {e['engagement'].get('checked_at', '?')}, honestly unresolved.")
        L.append("")
    if not_yet:
        L += ["## Not yet attempted this cycle", ""]
        for e in not_yet:
            L.append(f"- {e['lead']} (${e['prizeUsd']:,.0f}, fit {e['fitScore']}, {e['platform']})")
        L.append("")
    if tracked:
        L += ["## Tracked for visibility only (no automated engagement path)", ""]
        for e in tracked:
            L.append(f"- [{e['lead']}]({e['url']}) — {e['platform']}, "
                      f"${e['prizeUsd']:,.0f}, fit {e['fitScore']}")
        L.append("")
    return "\n".join(L)


def _load_log_state():
    return _load_json(LOG_STATE_PATH, {})


def _save_log_state(state):
    os.makedirs(os.path.dirname(LOG_STATE_PATH), exist_ok=True)
    with open(LOG_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _append_log_on_change(engagements, log_state):
    """Idempotent: appends a real JSONL line only the first time a given
    lead's status actually changes (not every cycle it's re-evaluated) —
    same pattern as attack_response_state.json/lessons.jsonl elsewhere."""
    new_lines = []
    for e in engagements:
        key = f"{e['platform']}:{e['lead']}"
        status = e["engagement"]["status"]
        if log_state.get(key) == status:
            continue
        log_state[key] = status
        new_lines.append(json.dumps({
            "ts": ic.now_iso(), "lead": e["lead"], "platform": e["platform"],
            "prizeUsd": e["prizeUsd"], "fitScore": e["fitScore"], "engagement": e["engagement"],
        }))
    if new_lines:
        os.makedirs(INTEL_DIR, exist_ok=True)
        with open(LOG_PATH, "a") as f:
            for line in new_lines:
                f.write(line + "\n")
    return len(new_lines)


def run():
    opportunities = _load_json(OPPORTUNITIES_PATH, [])
    response_state = _load_json(RESPONSE_STATE_PATH, {})
    engagements = build_engagements(opportunities, response_state)

    os.makedirs(INTEL_DIR, exist_ok=True)
    with open(STATUS_PATH, "w") as f:
        f.write(_render_status_md(engagements))

    log_state = _load_log_state()
    new_count = _append_log_on_change(engagements, log_state)
    _save_log_state(log_state)

    print(f"[engagements] {len(engagements)} tracked lead(s) at fit>={FIT_THRESHOLD}, "
          f"{new_count} new status change(s) logged")
    return engagements


if __name__ == "__main__":
    run()
