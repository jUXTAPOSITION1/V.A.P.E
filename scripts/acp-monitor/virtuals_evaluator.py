#!/usr/bin/env python3
"""
VIRTUALS EVALUATOR — VAPE's own paying customer, on ACP rails.

Same real story as agents/data_agent.py (see that module's own docstring for
the full rationale) — the "prove the payment rail end to end, and turn the
proof into a real, growing dataset" pattern — but for the OTHER payment rail
VAPE runs, not a second x402 client. data_agent.py already proves x402 works
by hiring VAPE's own $0.01 market-data offerings against a real Base token on
a fixed cadence; ACP has never had an equivalent, and the "Client side
(hiring other agents)" capability docs/ACP_PROTOCOL.md has documented since
launch has sat [WIP]/unused. This module is that: VAPE, acting as its own ACP
CLIENT, hires one of its own already-live ACP SELLING offerings to evaluate a
real Virtuals Protocol project — the same wallet on both sides of a genuine
on-chain USDC-escrow job (create -> fund -> submit -> complete), at a fixed
cadence of 1 job every 4 hours.

Why this can't just be a GitHub Actions cron like data_agent.py's: ACP
transactions go exclusively through the `acp` CLI (never a raw private key
+ SDK — see docs/ACP_PROTOCOL.md's Security section), signed by a
`restricted`-policy signer that's provisioned per-environment via a one-time
BROWSER approval (acp agent add-signer). That signer only exists on the
persistent host already running the rest of VAPE's ACP automation (the
listener/drain daemons in this same directory — see README.md) — an ephemeral
GitHub Actions runner gets a fresh, unapproved environment every single run,
so it structurally cannot hold that signer. This script is designed to run
on THAT host, invoked the same way as the daemons above (see "Wiring" below),
not as a workflow step.

Candidate sourcing: a real Virtuals-tagged token, resolved the exact same way
agents/data_agent.py::_fresh_candidate()'s virtuals branch already does — the
worker's own free /trending-base feed, filtered to isVirtuals=true — kept as
its own small fetch here (not imported) since this module runs in a different
process/host context than data_agent.py's CI-side one and has no need for
that module's other (non-Virtuals) candidate sources.

Offering picked per run: one of VAPE's own cheap ($0.01-$0.10), address-based,
zero-LLM-at-the-monitor-level ACP offerings (see scripts/acp-monitor/
auto_fulfill.py's AUTO set) — the same monitor already running on this host
catches the funded job and submits a real deliverable with no extra wiring
needed here. dossier_check is the one exception that calls an LLM inside its
own deliverable (still zero-LLM at the monitor-dispatch level); it's kept in
the mix deliberately since it's the one offering actually described as
producing a rounded "evaluation" rather than a single safety flag.

Rate limit (hard cap enforced HERE): exactly 1 job created per invocation,
gated to no more than once every MIN_INTERVAL_SECONDS (4h) regardless of how
often this script is invoked, plus a DAILY_CAP that's just that 4h cadence's
own real ceiling (24h / 4h = 6) — no slack needed since the interval gate
already is the hard limiter; the cap only guards against a clock/state bug
letting the interval check pass more often than it should.

CLI flag disclaimer: `acp client create-job`'s exact flags have never been
pinned down anywhere in this repo before now (docs/index.html's own CLI demo
literally shows `acp client create-job ...` with the args elided) — every
other ACP CLI invocation already merged (scripts/acp-monitor/auto_fulfill.py,
triage.py) only ever needed the PROVIDER-side verbs (set-budget/submit/events
drain/job history), which this repo had already used in production and
confirmed working. The client-side verbs (browse/create-job/fund/complete)
below are constructed by direct analogy to that already-verified flag
grammar (--job-id/--amount/--chain-id/--json, kebab-case subcommands) since
this sandbox has no access to the `acp` binary itself to confirm via --help.
_ACP() below is the single choke point for every invocation, so if any one
flag name is off, there is exactly one place to fix it.

Wiring (manual, one-time, on the ACP host — mirrors keepalive.sh's own cron):
  0 */4 * * * cd /home/node/.openclaw/acp-monitor && python3 virtuals_evaluator.py >> virtuals_evaluator.log 2>&1
Safe to invoke more often than every 4h (e.g. from drain_daemon.sh's existing
120s loop, exactly how data_agent.py rides featured-investigation.yml's much
tighter cadence) — the interval gate below makes any extra call a fast no-op.

Never raises. A CLI/network hiccup here must never be treated as a fatal
error by whatever cron or loop invokes this script.
"""
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

DIR = "/home/node/.openclaw/acp-monitor"
WS = "/home/node/.openclaw/workspace"
REPO = "/home/node/.openclaw/repos/vape"

STATE_PATH = os.path.join(DIR, "virtuals_evaluator_state.json")
SEEN_PATH = os.path.join(DIR, "virtuals_evaluator_seen.json")
LEDGER_PATH = os.path.join(DIR, "virtuals_evaluator_ledger.jsonl")
CATALOG_PATH = os.path.join(REPO, "intel/catalog/investigation-catalog.md")
LESSONS_PATH = os.path.join(REPO, "skillforge/memory/lessons.jsonl")

WORKER_BASE = "https://vape-x402.vapex402.workers.dev"
CHAIN_ID = 8453  # Base mainnet — the only chain /trending-base covers

MIN_INTERVAL_SECONDS = 4 * 3600  # 1 job every 4h, see module docstring
DAILY_CAP = 6                    # exactly the 4h cadence's own ceiling (24/4)
SEEN_COOLDOWN_HOURS = 12         # don't re-evaluate the same project too soon
JOB_POLL_SECONDS = 20
JOB_POLL_ATTEMPTS = 15           # ~5 minutes total budget waiting for submit

# name -> USDC price, matching scripts/acp-monitor/auto_fulfill.py's PRICE map
# exactly (kept in sync manually there too — see that file's own comment).
# Restricted to cheap, address-only, auto-fulfilled (zero-LLM-at-the-monitor-
# level) offerings that make sense as a per-project "evaluation" — see module
# docstring for why dossier_check is included despite being the one that
# calls an LLM inside its own deliverable.
OFFERINGS = {
    "token_safety_check": "0.02",
    "liquidity_check": "0.02",
    "rug_pull_alert": "0.03",
    "exploit_check": "0.01",
    "dossier_check": "0.10",
}

DRY = "--dry-run" in sys.argv


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    print(f"[virtuals_evaluator] {msg}")


# ---------------------------------------------------------------- state/quota

def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def seconds_since_last_attempt():
    last_ts = _load_json(STATE_PATH, {}).get("last_ts")
    if not last_ts:
        return None
    try:
        last = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
    except Exception:
        return None
    return (datetime.now(timezone.utc) - last).total_seconds()


def remaining_today():
    q = _load_json(STATE_PATH, {})
    if q.get("date") != _today():
        return DAILY_CAP
    return max(0, DAILY_CAP - q.get("count", 0))


def mark_attempt():
    q = _load_json(STATE_PATH, {})
    if q.get("date") != _today():
        q = {"date": _today(), "count": 0}
    q["last_ts"] = now_iso()
    _save_json(STATE_PATH, q)


def record_job():
    q = _load_json(STATE_PATH, {})
    if q.get("date") != _today():
        q = {"date": _today(), "count": 0, "last_ts": q.get("last_ts")}
    q["count"] = q.get("count", 0) + 1
    _save_json(STATE_PATH, q)


def log_ledger(entry):
    if DRY:
        return
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


# --------------------------------------------------------- candidate sourcing

def _recently_seen():
    seen = _load_json(SEEN_PATH, {})
    cutoff = datetime.now(timezone.utc) - timedelta(hours=SEEN_COOLDOWN_HOURS)
    kept = {}
    for addr, ts in seen.items():
        try:
            if datetime.fromisoformat(ts.replace("Z", "+00:00")) >= cutoff:
                kept[addr] = ts
        except Exception:
            continue
    return kept


def _mark_seen(address):
    seen = _recently_seen()
    seen[address.lower()] = now_iso()
    _save_json(SEEN_PATH, seen)


def fresh_virtuals_candidate():
    """Real Virtuals-tagged token from the worker's own free /trending-base
    feed, skipping anything evaluated in the last SEEN_COOLDOWN_HOURS.
    Returns (address, symbol, name) or None. Never raises."""
    try:
        import requests
        r = requests.get(f"{WORKER_BASE}/trending-base", timeout=15)
        if r.status_code != 200:
            return None
        tokens = r.json().get("tokens") or []
    except Exception as e:
        log(f"trending-base fetch failed: {e}")
        return None

    seen = _recently_seen()
    virtuals_only = [t for t in tokens if t.get("isVirtuals")]
    for t in virtuals_only:
        tok = t.get("token") or {}
        addr = tok.get("address")
        if not addr or addr.lower() in seen:
            continue
        return addr, tok.get("symbol"), tok.get("name")
    return None


# --------------------------------------------------------------------- ACP IO

def _ACP(args, timeout=60):
    """Single choke point for every `acp` CLI invocation — see module
    docstring's CLI flag disclaimer. Returns (ok, parsed_json_or_None, raw_out, err)."""
    if DRY:
        return True, {"dryRun": True, "cmd": args}, json.dumps({"dryRun": True, "cmd": args}), ""
    try:
        p = subprocess.run(["acp"] + args, cwd=WS, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return False, None, "", str(e)
    out = p.stdout.strip()
    parsed = None
    if out:
        try:
            parsed = json.loads(out)
        except Exception:
            parsed = None
    return p.returncode == 0, parsed, out, p.stderr.strip()


def resolve_vape_agent_id():
    """`acp browse "vape"` — resolves VAPE's own agent id so create-job below
    never has to hardcode one. Falls back to the literal string "vape" (the
    same identifier docs/ACP_PROTOCOL.md's own CLI demo uses) if browse's
    response shape doesn't carry an obvious id field, since VAPE's provider
    identity is a stable, already-registered name either way."""
    ok, parsed, out, err = _ACP(["browse", "vape", "--json"])
    if not ok:
        log(f"acp browse failed (falling back to name 'vape'): {err[:200]}")
        return "vape"
    candidates = parsed if isinstance(parsed, list) else (parsed or {}).get("agents") or (parsed or {}).get("results") or []
    for c in candidates if isinstance(candidates, list) else []:
        if isinstance(c, dict):
            name = str(c.get("name") or "").lower()
            if name == "vape" or "vape" in name:
                return c.get("id") or c.get("agentId") or c.get("walletAddress") or "vape"
    return "vape"


def create_job(provider_id, offering, requirement):
    return _ACP(["client", "create-job", "--provider", str(provider_id), "--offering", offering,
                 "--requirement", json.dumps(requirement), "--chain-id", str(CHAIN_ID), "--json"])


def fund_job(job_id, amount):
    return _ACP(["client", "fund", "--job-id", str(job_id), "--amount", amount,
                 "--chain-id", str(CHAIN_ID), "--json"])


def job_status(job_id):
    return _ACP(["job", "status", "--job-id", str(job_id), "--chain-id", str(CHAIN_ID), "--json"])


def complete_job(job_id):
    return _ACP(["client", "complete", "--job-id", str(job_id), "--chain-id", str(CHAIN_ID), "--json"])


def _extract_job_id(parsed):
    if not isinstance(parsed, dict):
        return None
    for k in ("jobId", "job_id", "id", "onChainJobId"):
        if parsed.get(k):
            return parsed[k]
    return None


def _job_is_submitted(parsed):
    if not isinstance(parsed, dict):
        return False
    phase = str(parsed.get("phase") or parsed.get("status") or parsed.get("state") or "").lower()
    return "submit" in phase or "complet" in phase or bool(parsed.get("deliverable"))


# ------------------------------------------------------------------- catalog

def log_catalog(job_id, offering, address, symbol):
    if DRY:
        return
    try:
        os.makedirs(os.path.dirname(CATALOG_PATH), exist_ok=True)
        with open(CATALOG_PATH, "a") as f:
            f.write(f"\n- {now_iso()} | job `{job_id}` | **{offering}** | Virtuals project "
                     f"{symbol or address} | VAPE self-hire via ACP (virtuals_evaluator)")
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(LESSONS_PATH), exist_ok=True)
        with open(LESSONS_PATH, "a") as f:
            f.write(json.dumps({"ts": now_iso(), "job": job_id, "offering": offering,
                                 "outcome": "virtuals_evaluator_self_hire", "target": address,
                                 "path": "acp"}) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------- main

def run():
    since_last = seconds_since_last_attempt()
    if since_last is not None and since_last < MIN_INTERVAL_SECONDS:
        wait_min = round((MIN_INTERVAL_SECONDS - since_last) / 60)
        note = f"4h interval not yet up ({wait_min}m remaining) — skipped this cycle"
        log(note)
        return {"hired": False, "note": note}

    if remaining_today() < 1:
        note = f"daily cap reached ({DAILY_CAP}/day) — skipped this cycle"
        log(note)
        return {"hired": False, "note": note}

    candidate = fresh_virtuals_candidate()
    if not candidate:
        note = "no fresh Virtuals-tagged candidate found this cycle — skipped"
        log(note)
        return {"hired": False, "note": note}
    address, symbol, name = candidate

    offering = random.choice(list(OFFERINGS.keys()))
    price = OFFERINGS[offering]

    # Marked BEFORE the ACP round-trip so a failed/slow attempt still
    # consumes this cycle's interval gate, matching agents/data_agent.py's
    # own mark_attempt()-before-hire ordering (no retry-storming a flaky CLI).
    mark_attempt()
    _mark_seen(address)

    provider_id = resolve_vape_agent_id()
    requirement = {"address": address, "chain_id": CHAIN_ID}

    ok, parsed, out, err = create_job(provider_id, offering, requirement)
    if not ok:
        log(f"create-job failed for {offering} @ {address}: {err[:200]}")
        log_ledger({"ts": now_iso(), "target": address, "symbol": symbol, "offering": offering,
                    "phase": "create-job-failed", "error": err[:200]})
        return {"hired": False, "note": "create-job failed"}

    job_id = _extract_job_id(parsed)
    if not job_id:
        log(f"create-job returned no job id: {out[:200]}")
        log_ledger({"ts": now_iso(), "target": address, "symbol": symbol, "offering": offering,
                    "phase": "no-job-id", "raw": out[:200]})
        return {"hired": False, "note": "create-job returned no job id"}

    ok, parsed, out, err = fund_job(job_id, price)
    if not ok:
        log(f"fund failed for job {job_id}: {err[:200]}")
        log_ledger({"ts": now_iso(), "job": job_id, "target": address, "symbol": symbol,
                    "offering": offering, "phase": "fund-failed", "error": err[:200]})
        return {"hired": False, "note": "fund failed", "job": job_id}

    # Real payment has now settled into escrow — this counts as this cycle's
    # 1 real ACP transaction regardless of whether the poll below catches a
    # submit+complete in time (mirrors agents/data_agent.py's "paid iff the
    # request settled" semantics: fund is the payment action, complete is a
    # best-effort follow-up, not a precondition for the quota to count).
    record_job()
    log(f"{address} ({symbol or 'unknown'}): funded job {job_id} for {offering}, ${price}")

    submitted = False
    for _ in range(JOB_POLL_ATTEMPTS):
        time.sleep(JOB_POLL_SECONDS)
        ok, parsed, out, err = job_status(job_id)
        if ok and _job_is_submitted(parsed):
            submitted = True
            break

    completed = False
    if submitted:
        ok, parsed, out, err = complete_job(job_id)
        completed = ok
        if ok:
            log_catalog(job_id, offering, address, symbol)
        else:
            log(f"complete failed for job {job_id}: {err[:200]}")

    log_ledger({"ts": now_iso(), "job": job_id, "target": address, "symbol": symbol,
                "offering": offering, "cost_usd": price, "submitted": submitted, "completed": completed})
    return {"hired": True, "job": job_id, "offering": offering, "target": address,
            "submitted": submitted, "completed": completed}


if __name__ == "__main__":
    print(json.dumps(run()))
