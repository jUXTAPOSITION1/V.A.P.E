#!/usr/bin/env python3
"""ACP job triage — drains the listener's event file, classifies each event,
maintains per-job state, and decides what (if anything) needs the reasoning handler.
ZERO LLM cost: pure parse + state. Prints a JSON summary; exit code signals action.

Exit codes:
  0  nothing actionable (idle)
  10 actionable job event(s) present -> caller should wake the handler
"""
import json, os, subprocess, sys, time
from datetime import datetime, timezone

DIR = "/home/node/.openclaw/acp-monitor"
WS = "/home/node/.openclaw/workspace"
EVENTS = os.path.join(DIR, "events.jsonl")
STATE = os.path.join(DIR, "state.json")
QUEUE = os.path.join(DIR, "action-queue.jsonl")  # actionable items for the handler

# Provider-side phases that need OUR action (we are selling services).
# NOTE: the lightweight listener emits short status phases ("open", "funded",
# "request", ...) as well as full "job.created"/"job.funded" system events.
# Map BOTH so a job is never silently dropped (bug: "open" jobs like exploit_check
# 64403 were classified action=None and never queued -> expired unfulfilled).
ACTION_PHASES = {
    "job.created": "set-budget",     # price the job
    "job.funded": "submit",          # do the work + deliver
    "request": "set-budget",
    "transaction": "submit",
    "open": "set-budget",            # lightweight phase for a newly created job
    "created": "set-budget",
    "funded": "submit",             # lightweight phase for a funded job
    "negotiation": "set-budget",
}

def now(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load_state():
    if os.path.exists(STATE):
        try: return json.load(open(STATE))
        except: pass
    return {"jobs": {}, "updated": now()}

def save_state(s):
    s["updated"] = now()
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=2)
    os.replace(tmp, STATE)

def drain(limit=50):
    """Pull events out of the listener file via the CLI (removes them)."""
    if not os.path.exists(EVENTS) or os.path.getsize(EVENTS) == 0:
        return []
    try:
        p = subprocess.run(
            ["acp", "events", "drain", "--file", EVENTS, "--limit", str(limit), "--json"],
            cwd=WS, capture_output=True, text=True, timeout=60)
        out = p.stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        return data if isinstance(data, list) else data.get("events", data.get("data", []))
    except Exception as e:
        print(f"[triage] drain error: {e}", file=sys.stderr)
        return []

def classify(ev):
    """Return (job_id, phase, action_needed_or_None)."""
    e = ev.get("event", ev)
    jid = str(e.get("jobId") or e.get("job_id") or ev.get("jobId") or "")
    phase = (e.get("type") or e.get("phase") or e.get("status") or ev.get("type") or "").lower()
    action = None
    for key, act in ACTION_PHASES.items():
        if key in phase:
            action = act
            break
    return jid, phase, action

def main():
    state = load_state()
    events = drain()
    actionable = []
    for ev in events:
        jid, phase, action = classify(ev)
        if not jid:
            continue
        j = state["jobs"].setdefault(jid, {"first_seen": now(), "events": []})
        j["last_phase"] = phase
        j["last_seen"] = now()
        j["events"].append({"ts": now(), "phase": phase})
        if action and not j.get("done"):
            j["pending_action"] = action
            actionable.append({"jobId": jid, "phase": phase, "action": action,
                               "event": ev.get("event", ev)})
    save_state(state)

    if actionable:
        with open(QUEUE, "a") as f:
            for a in actionable:
                f.write(json.dumps(a) + "\n")
        print(json.dumps({"ts": now(), "drained": len(events),
                          "actionable": len(actionable),
                          "jobs": [a["jobId"] for a in actionable]}))
        sys.exit(10)
    else:
        print(json.dumps({"ts": now(), "drained": len(events), "actionable": 0}))
        sys.exit(0)

if __name__ == "__main__":
    main()
