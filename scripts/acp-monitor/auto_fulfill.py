#!/usr/bin/env python3
"""
ACP auto-fulfiller — settle the 6 zero-LLM offerings end to end, no model wake.

Reads the action queue produced by triage.py, and for each pending job whose
offering has a deterministic real-data handler in agents/acp_fulfill.py:
  - job.created  -> acp provider set-budget   (price = offering priceValue)
  - job.funded   -> run handler -> acp provider submit (real deliverable)
  - mark done in state.json, log to intel/catalog + lessons.jsonl

Offerings needing real reasoning/heavy tools (deep_contract_audit, forensics_deep,
wallet_recon, tx_decode, whale_watch, bulk_safety_bundle, community_intel_broadcast)
are LEFT in the queue with escalate=True for the LLM handler. This module never
touches those — it only auto-clears the cheap deterministic ones.

ZERO LLM. Real data only. Idempotent (checks state.json done/budgeted).
The ACP CLI does ALL signing/submitting; we never handle keys.

Usage:
  python3 auto_fulfill.py            # process queue for real
  python3 auto_fulfill.py --dry-run  # show what it WOULD do, no CLI writes
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

DIR = "/home/node/.openclaw/acp-monitor"
WS = "/home/node/.openclaw/workspace"
REPO = "/home/node/.openclaw/repos/vape"
QUEUE = os.path.join(DIR, "action-queue.jsonl")
STATE = os.path.join(DIR, "state.json")
CATALOG = os.path.join(REPO, "intel/catalog/investigation-catalog.md")
LESSONS = os.path.join(REPO, "skillforge/memory/lessons.jsonl")

sys.path.insert(0, REPO)
try:
    from agents.acp_fulfill import fulfill, HANDLERS
except Exception as e:
    print(json.dumps({"error": f"cannot import acp_fulfill: {e}"}))
    sys.exit(2)

# Offering -> price (USDC). Refreshed from `acp offering list`; kept here so set-budget
# never needs a network round-trip. Update if you reprice offerings.
PRICE = {
    "token_safety_check": "0.02", "liquidity_check": "0.02", "rug_pull_alert": "0.03",
    "exploit_check": "0.01", "safety_preflight": "0.05", "market_intel": "0.15",
    "wallet_recon": "0.03", "tx_decode": "0.05", "whale_watch": "0.10",
    "deep_contract_audit": "1", "forensics_deep": "2", "bulk_safety_bundle": "0.50",
    "community_intel_broadcast": "0.10", "partner_referral": "0.01",
}

# Only these settle with no model. Everything else -> escalate to LLM handler.
AUTO = set(HANDLERS.keys())  # token_safety/liquidity/rug_pull/exploit/safety_preflight/market_intel

DRY = "--dry-run" in sys.argv


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE))
        except Exception:
            pass
    return {"jobs": {}, "updated": now()}


def save_state(s):
    s["updated"] = now()
    tmp = STATE + ".tmp"
    json.dump(s, open(tmp, "w"), indent=2)
    os.replace(tmp, STATE)


def read_queue():
    if not os.path.exists(QUEUE):
        return []
    items = []
    for line in open(QUEUE):
        line = line.strip()
        if line:
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items


def rewrite_queue(remaining):
    tmp = QUEUE + ".tmp"
    with open(tmp, "w") as f:
        for it in remaining:
            f.write(json.dumps(it) + "\n")
    os.replace(tmp, QUEUE)


def offering_of(item):
    """Best-effort: extract the offering name from the event payload."""
    ev = item.get("event", item)
    e = ev.get("event", ev) if isinstance(ev, dict) else {}
    for path in (e, ev, item):
        if not isinstance(path, dict):
            continue
        for k in ("offering", "offeringName", "packageName", "serviceName", "name"):
            v = path.get(k)
            if v and str(v) in PRICE:
                return str(v)
        # nested requirement sometimes carries it
        req = path.get("requirement") or path.get("serviceRequirement")
        if isinstance(req, dict):
            for k in ("offering", "type", "service"):
                if req.get(k) in PRICE:
                    return req[k]
    # Fallback: ACP job events don't carry the offering name inline — it lives in
    # the on-chain job `description` (set to offering.name at creation). Resolve it
    # from job history so single-offering jobs (e.g. exploit_check 64403) settle
    # instead of being dropped/escalated.
    jid = str(item.get("jobId") or (ev.get("onChainJobId") if isinstance(ev, dict) else "") or "")
    chain = 8453
    if isinstance(ev, dict):
        chain = ev.get("chainId") or ev.get("chain_id") or (e.get("chainId") if isinstance(e, dict) else None) or 8453
    if jid:
        name = _offering_from_history(jid, chain)
        if name:
            return name
    return None


_HIST_CACHE = {}


def _offering_from_history(jid, chain=8453):
    """Look up a job's offering name from its on-chain description via ACP history.
    Cached per job. Best-effort and network-guarded — never raises."""
    if jid in _HIST_CACHE:
        return _HIST_CACHE[jid]
    name = None
    try:
        p = subprocess.run(
            ["acp", "job", "history", "--job-id", str(jid),
             "--chain-id", str(chain), "--json"],
            cwd=WS, capture_output=True, text=True, timeout=30)
        if p.returncode == 0 and p.stdout.strip():
            d = json.loads(p.stdout)
            blob = json.dumps(d)
            # direct description field
            for entry in d.get("entries", []):
                ev = entry.get("event", {})
                for k in ("description", "offering", "serviceName", "packageName"):
                    v = ev.get(k) or entry.get(k)
                    if v and str(v) in PRICE:
                        name = str(v)
                        break
                if name:
                    break
            # else scan the whole blob for any known offering token
            if not name:
                for cand in PRICE:
                    if cand in blob:
                        name = cand
                        break
    except Exception:
        pass
    _HIST_CACHE[jid] = name
    return name


def requirement_of(item):
    ev = item.get("event", item)
    e = ev.get("event", ev) if isinstance(ev, dict) else {}
    for path in (e, ev, item):
        if isinstance(path, dict):
            for k in ("requirement", "serviceRequirement", "input", "params"):
                if path.get(k):
                    return path[k]
    return item  # fall back to whole item (acp_fulfill._addr scans strings)


def acp(args, timeout=120):
    """Run an ACP CLI command from the workspace. Returns (ok, stdout, stderr)."""
    if DRY:
        return True, json.dumps({"dryRun": True, "cmd": args}), ""
    try:
        p = subprocess.run(["acp"] + args, cwd=WS, capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def set_budget(jid, offering, chain):
    amt = PRICE.get(offering)
    return acp(["provider", "set-budget", "--job-id", str(jid),
                "--amount", amt, "--chain-id", str(chain), "--json"])


def submit(jid, deliverable, chain):
    text = json.dumps(deliverable) if not isinstance(deliverable, str) else deliverable
    return acp(["provider", "submit", "--job-id", str(jid),
                "--deliverable", text, "--chain-id", str(chain), "--json"])


def log_catalog(jid, offering, deliverable):
    if DRY:
        return
    try:
        os.makedirs(os.path.dirname(CATALOG), exist_ok=True)
        verdict = ""
        if isinstance(deliverable, dict):
            d = deliverable.get("deliverable", deliverable)
            verdict = d.get("verdict") or d.get("combined") or d.get("rug_risk") or ""
        with open(CATALOG, "a") as f:
            f.write(f"\n- {now()} | job `{jid}` | **{offering}** | {verdict} | auto-fulfilled (zero-LLM)")
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(LESSONS), exist_ok=True)
        with open(LESSONS, "a") as f:
            f.write(json.dumps({"ts": now(), "job": jid, "offering": offering,
                                "outcome": "auto_submitted", "bounty_usd": PRICE.get(offering),
                                "path": "zero-llm"}) + "\n")
    except Exception:
        pass


def main():
    state = load_state()
    queue = read_queue()
    if not queue:
        print(json.dumps({"ts": now(), "queue": 0, "auto": 0, "escalate": 0}))
        return

    remaining = []
    summary = {"auto_budgeted": [], "auto_submitted": [], "escalate": [], "skipped": []}

    for item in queue:
        jid = str(item.get("jobId") or "")
        action = item.get("action")
        phase = item.get("phase", "")
        chain = 8453
        ev = item.get("event", {})
        if isinstance(ev, dict):
            chain = ev.get("chainId") or ev.get("chain_id") or 8453

        offering = offering_of(item)
        j = state["jobs"].setdefault(jid, {"first_seen": now(), "events": []})

        # Not one of our deterministic offerings -> escalate to LLM handler.
        if not offering or offering not in AUTO:
            item["escalate"] = True
            remaining.append(item)
            summary["escalate"].append({"jobId": jid, "offering": offering, "phase": phase})
            continue

        if j.get("done"):
            summary["skipped"].append({"jobId": jid, "why": "already done"})
            continue

        if action == "set-budget":
            if j.get("budgeted"):
                summary["skipped"].append({"jobId": jid, "why": "already budgeted"})
                continue
            ok, out, err = set_budget(jid, offering, chain)
            if ok:
                j["budgeted"] = True
                j["offering"] = offering
                j["last_seen"] = now()
                summary["auto_budgeted"].append({"jobId": jid, "offering": offering,
                                                 "amount": PRICE[offering]})
            else:
                item["escalate"] = True
                item["error"] = err[:200]
                remaining.append(item)
                summary["escalate"].append({"jobId": jid, "offering": offering,
                                            "why": "set-budget failed", "err": err[:120]})

        elif action == "submit":
            req = requirement_of(item)
            result = fulfill(offering, req)
            if result.get("status") not in ("ok",):
                # handler couldn't produce real data -> escalate, never submit junk
                item["escalate"] = True
                item["error"] = result.get("error") or result.get("note")
                remaining.append(item)
                summary["escalate"].append({"jobId": jid, "offering": offering,
                                            "why": "handler not ok", "detail": result.get("status")})
                continue
            ok, out, err = submit(jid, result, chain)
            if ok:
                j["done"] = True
                j["offering"] = offering
                j["submitted_at"] = now()
                log_catalog(jid, offering, result)
                summary["auto_submitted"].append({"jobId": jid, "offering": offering})
            else:
                item["escalate"] = True
                item["error"] = err[:200]
                remaining.append(item)
                summary["escalate"].append({"jobId": jid, "offering": offering,
                                            "why": "submit failed", "err": err[:120]})
        else:
            remaining.append(item)
            summary["skipped"].append({"jobId": jid, "why": f"unknown action {action}"})

    save_state(state)
    rewrite_queue(remaining)

    print(json.dumps({"ts": now(), "dry_run": DRY,
                      "queue_in": len(queue), "queue_out": len(remaining),
                      "auto_budgeted": len(summary["auto_budgeted"]),
                      "auto_submitted": len(summary["auto_submitted"]),
                      "escalated": len(summary["escalate"]),
                      "detail": summary}, indent=2))


if __name__ == "__main__":
    main()
