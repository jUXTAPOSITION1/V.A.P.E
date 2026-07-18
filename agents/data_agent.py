#!/usr/bin/env python3
"""
DATA AGENT — VAPE's own paying customer.

Recruited mid-investigation (agents/investigate.py::investigate()) to hire
one of VAPE's own $0.01 x402 market-data offerings (worker/src/dataHandlers.ts,
the same ones a human buyer hires from docs/assets/hire.js) against the token
under investigation, using its own real, funded wallet (DATA_AGENT_PRIVATE_KEY)
and the official x402 Python SDK's exact-scheme EVM client. Real USDC leaves
DATA_AGENT's wallet and settles into VAPE's own PAY_TO_ADDRESS on Base
mainnet, via the same worker + facilitator any other x402 buyer uses — this
proves the payment rail end-to-end on every real investigation, not only when
an external buyer happens to hire something, and folds independently-priced
DefiLlama-backed data into every report VAPE already writes.

This module runs as TWO independent instances rather than one agent trying
to alternate between facilitators: this file's own run_for_investigation()
tags requests X-VAPE-Client: data-agent (worker/src/index.ts pins that tag
to CDP), and agents/data_agent_vapor.py's run_for_investigation() tags
data-agent-vapor (pinned to VAPOR). An earlier version tried a single agent
alternating 50/50 via a KV-persisted toggle (worker/src/lib/
dataAgentAlternator.ts, removed) — that added a cross-request shared-state
dependency for no real benefit over just running two thin, independently-
gated, deterministic agents. Each instance has its OWN quota/ledger state
(see _State below) so neither's 30-minute gate or daily cap blocks the
other — both can genuinely hire in the same investigation cycle.

Rate limits (hard caps enforced HERE, not the worker's job), per instance:
  - Exactly 1 offering hired per invocation — this agent runs on a fixed 2x/
    hour cadence (see MIN_INTERVAL_SECONDS), so "1 per run" is what maps that
    cadence onto "$0.01 per run" cleanly.
  - 48 hires/day total across every investigation (2/hour x 24h), tracked in
    a per-instance quota file (same durable-counter shape as
    skillforge/research.py's MONTHLY_QUOTA pattern, just per-day). Once hit,
    this becomes a documented no-op for the rest of the day rather than
    erroring the investigation that recruited it.
  - A 30-minute minimum interval between hire attempts, independent of the
    daily cap above — lets agents/investigate.py run on a much tighter
    cadence (the site's Featured Investigation spotlight) without either
    instance firing any more often than 2x/hour.

Restricted to offerings that only need the address already under
investigation, a chain slug, or no input at all — protocol/protocol_fees/
unlocks/treasury need a specific DefiLlama protocol *slug* that isn't
derivable from an arbitrary token address without guessing one, and guessing
a slug is exactly the kind of fabrication this repo's real-data-only rule
forbids. Also restricted to Base (chain 8453) investigations, since that's
the only chain whose DefiLlama chain-slug mapping is confirmed correct here.

Never raises to its caller — a data-agent outage, an empty wallet, or a
missing key must never sink the underlying investigation it was recruited
into.
"""
import json
import os
import random
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKER_BASE = "https://vape-x402.vapex402.workers.dev"
NETWORK = "eip155:8453"  # Base mainnet — same network the worker's PAY_TO_ADDRESS settles on

DAILY_CAP = 48  # 2/hour x 24h
HIRES_PER_RUN = 1
MIN_INTERVAL_SECONDS = 30 * 60  # 30m floor between hire attempts, see module docstring

# Real, funded wallet the user provisioned for this agent — a fund-moving
# action never proceeds unless DATA_AGENT_PRIVATE_KEY actually derives this
# exact address (see _build_session()). Both facilitator-pinned instances
# share the same wallet: the facilitator is just the settlement rail, not
# the payer's identity, so there's no reason to need a second funded wallet.
EXPECTED_WALLET = "0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15"

# name -> (address) -> query params. See the module docstring for why
# protocol/protocol_fees/unlocks/treasury are deliberately excluded.
OFFERING_PARAMS = {
    "token_intel":     lambda addr: {"address": addr, "chain": "base"},
    "token_chart":     lambda addr: {"address": addr, "chain": "base"},
    "chain_protocols": lambda addr: {"chain": "Base"},
    "chain_overview":  lambda addr: {"chain": "Base"},
    "chain_fees":      lambda addr: {"chain": "base"},
    "dex_volumes":     lambda addr: {"chain": "base"},
    "yields":          lambda addr: {},
    "stablecoins":     lambda addr: {},
    "bridges":         lambda addr: {},
}


class _State:
    """Per-instance quota/ledger state, keyed by a filename prefix so the
    CDP-pinned and VAPOR-pinned instances never share (or contend over) the
    same gate — each hires on its own independent 30m/48-per-day schedule."""

    def __init__(self, prefix):
        self.quota_path = os.path.join(ROOT, "skillforge", "memory", f"{prefix}_quota.json")
        self.ledger_path = os.path.join(ROOT, "skillforge", "memory", f"{prefix}_ledger.jsonl")

    def _today(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _load_quota(self):
        try:
            with open(self.quota_path) as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_quota(self, q):
        os.makedirs(os.path.dirname(self.quota_path), exist_ok=True)
        with open(self.quota_path, "w") as f:
            json.dump(q, f, indent=2)

    def remaining_today(self):
        q = self._load_quota()
        if q.get("date") != self._today():
            return DAILY_CAP
        return max(0, DAILY_CAP - q.get("count", 0))

    def seconds_since_last_attempt(self):
        """None if there's no record yet (never gates a fresh install)."""
        last_ts = self._load_quota().get("last_ts")
        if not last_ts:
            return None
        try:
            last = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        except Exception:
            return None
        return (datetime.now(timezone.utc) - last).total_seconds()

    def mark_attempt(self):
        q = self._load_quota()
        if q.get("date") != self._today():
            q = {"date": self._today(), "count": 0}
        q["last_ts"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        self._save_quota(q)

    def record_hires(self, n):
        if n <= 0:
            return
        q = self._load_quota()
        if q.get("date") != self._today():
            q = {"date": self._today(), "count": 0, "last_ts": q.get("last_ts")}
        q["count"] = q.get("count", 0) + n
        self._save_quota(q)

    def log_ledger(self, entry):
        os.makedirs(os.path.dirname(self.ledger_path), exist_ok=True)
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


def _build_session(client_tag):
    """Build a requests.Session that transparently pays x402 402 challenges
    with DATA_AGENT's own funded wallet. Returns None if the key is unset,
    invalid, doesn't derive EXPECTED_WALLET, or the x402 SDK is unavailable —
    a real fund-moving action never proceeds on an unverified identity."""
    key = os.getenv("DATA_AGENT_PRIVATE_KEY")
    if not key:
        return None
    try:
        from eth_account import Account
        account = Account.from_key(key)
    except Exception as e:
        print(f"[data_agent] bad DATA_AGENT_PRIVATE_KEY: {e}")
        return None
    if account.address.lower() != EXPECTED_WALLET.lower():
        print(f"[data_agent] wallet mismatch: key derives {account.address}, "
              f"expected {EXPECTED_WALLET} — refusing to spend from an unverified identity")
        return None
    try:
        from x402 import x402ClientSync
        from x402.http.clients.requests import x402_requests
        from x402.mechanisms.evm.exact import ExactEvmScheme
    except Exception as e:
        print(f"[data_agent] x402 SDK unavailable: {e}")
        return None
    client = x402ClientSync()
    client.register(NETWORK, ExactEvmScheme(signer=account))
    session = x402_requests(client)
    # Lets the worker's facilitator-selection logic (worker/src/index.ts)
    # pin this instance's traffic to its assigned facilitator (data-agent ->
    # CDP, data-agent-vapor -> VAPOR) instead of the random 50/50 split.
    # Session-level header, safe across the payment retry (unlike the fetch()
    # Request-object gotcha docs/assets/hire.js hit): x402HTTPAdapter.send()
    # builds retries via request.copy() + headers.update(), both additive.
    session.headers["X-VAPE-Client"] = client_tag
    return session


def hire(session, offering, params):
    """Pay for and fetch one $0.01 x402 market-data offering.

    Returns (deliverable_or_error_dict, paid) — paid is True iff the request
    reached the paid endpoint and got back HTTP 200 (real settlement
    happened), even if the deliverable itself reports an upstream miss
    (status: "error" — a genuine attempt, same as any paid job that comes
    back with "no data"). paid is False on any network/HTTP failure, since
    no settlement can be assumed. Never raises.
    """
    try:
        r = session.get(f"{WORKER_BASE}/data/{offering}", params=params, timeout=20)
    except Exception as e:
        print(f"[data_agent] {offering} request failed: {e}")
        return {"error": str(e)}, False
    if r.status_code != 200:
        print(f"[data_agent] {offering} failed: HTTP {r.status_code} {r.text[:200]}")
        return {"error": f"HTTP {r.status_code}"}, False
    try:
        body = r.json()
    except Exception as e:
        return {"error": f"bad response: {e}"}, False
    return body.get("deliverable", body), True


def _run(address, chain, *, client_tag, state, log_prefix):
    """Shared core for both facilitator-pinned instances — see module
    docstring. Hires 1 random $0.01 x402 offering against the token under
    investigation (capped at 48 total paid hires/day, and no more often than
    once every 30m regardless of how often investigate.py itself runs) and
    returns what it bought so the report can fold it in.
    """
    if str(chain) != "8453":
        return {"hired": [], "note": "data agent only wired for Base (8453) investigations"}

    since_last = state.seconds_since_last_attempt()
    if since_last is not None and since_last < MIN_INTERVAL_SECONDS:
        wait_min = round((MIN_INTERVAL_SECONDS - since_last) / 60)
        return {"hired": [], "note": f"30m interval not yet up ({wait_min}m remaining) — skipped this cycle"}

    remaining = state.remaining_today()
    if remaining < HIRES_PER_RUN:
        return {"hired": [], "note": f"daily cap reached ({DAILY_CAP}/day) — skipped this cycle"}

    session = _build_session(client_tag)
    if session is None:
        return {"hired": [], "note": "DATA_AGENT_PRIVATE_KEY not configured or invalid — skipped"}

    state.mark_attempt()

    picks = random.sample(list(OFFERING_PARAMS.keys()), HIRES_PER_RUN)

    hired = []
    paid_count = 0
    for name in picks:
        params = OFFERING_PARAMS[name](address)
        deliverable, paid = hire(session, name, params)
        hired.append({"offering": name, "params": params, "deliverable": deliverable, "paid": paid})
        if paid:
            paid_count += 1

    state.record_hires(paid_count)
    cost_usd = round(paid_count * 0.01, 2)
    state.log_ledger({
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": address,
        "hired": [h["offering"] for h in hired],
        "paid": paid_count,
        "cost_usd": cost_usd,
    })
    print(f"[{log_prefix}] {address}: hired {[h['offering'] for h in hired]}, "
          f"paid {paid_count}, ${cost_usd:.2f}")
    return {"hired": hired, "cost_usd": cost_usd}


_CDP_STATE = _State("data_agent")


def run_for_investigation(address, chain="8453"):
    """Recruited by agents/investigate.py::investigate() for every real
    report — CDP-pinned instance (X-VAPE-Client: data-agent)."""
    return _run(address, chain, client_tag="data-agent", state=_CDP_STATE, log_prefix="data_agent")
