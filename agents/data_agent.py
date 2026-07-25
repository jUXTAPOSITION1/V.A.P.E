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

Rate limits, VAPOR-pinned instance (agents/data_agent_vapor.py) — UNCHANGED,
fixed caps, per the module's original design:
  - Exactly 1 offering hired per invocation of run_for_investigation()/
    run_standalone(), no more than once every 30 minutes, capped at
    DAILY_CAP (60) hires/day. See _run() below.

Rate limits, CDP-pinned instance (this file's own run_for_investigation()/
run_standalone()/run_catalog_sweep()) — a GROWING MINIMUM instead of a fixed
cap, deliberately: VAPE wants real, ever-increasing x402 settlement volume
through its own worker, not a plateau. GROWTH_BASE_DAILY (100) combined
transactions on day one, compounding GROWTH_RATE_PER_DAY (1%) higher every
day after — unbounded, forever (see _daily_target_combined()). That combined
target is split across this file's two independent CDP streams (the main
investigation/standalone stream and the catalog-sweep stream), each pacing
itself with a deadline-driven "how much is still owed today, how much of the
day is left" calculation (_due_now()) rather than a fixed interval — a
missed or delayed poll doesn't lose its slot, the next call just finds a
shorter required wait and catches up. This is a REAL, IMPORTANT limiting
factor to keep in mind long-term: however often
.github/workflows/featured-investigation.yml's cron actually polls this
module sets a hard ceiling on throughput (at most one real hire per poll)
regardless of how large the growing target gets — once the target's implied
pace exceeds that poll cadence, actual daily volume flattens at
(polls/day) x (number of CDP streams) until the workflow's own cron is
tightened, since no in-process rate limiter can invent extra polls that
never fired. This is by design, not silently masked: the growing target
always represents the honest daily MINIMUM being aimed for, and this module
never claims to have hit it if the polls simply weren't frequent enough.

Restricted to offerings that only need a token address, a chain slug, or no
input at all. Also restricted to Base (chain 8453) for run_for_investigation()/
run_standalone(), since that's the only chain whose DefiLlama chain-slug
mapping is confirmed correct for THIS hire path's fixed offering set.

run_catalog_sweep() below is a second, independently-gated stream (own 30m/
48-per-day cap, own quota/ledger file) added specifically to (a) exercise
every one of VAPE's own x402 offerings priced $0.02 or less — including
protocol/protocol_fees/unlocks/treasury, sourcing a real DefiLlama slug via
protocols_on_chain() rather than guessing one — and (b) build a real,
growing dataset of tokens/projects VAPE has actually seen (data/
token_database.jsonl), sourced fresh each cycle from Base movers, other EVM
chains, and Virtuals-tagged tokens (the worker's own free /trending-base
route), avoiding recently-seen addresses so the same handful of tokens don't
dominate the dataset.

Never raises to its caller — a data-agent outage, an empty wallet, or a
missing key must never sink the underlying investigation it was recruited
into.
"""
import json
import math
import os
import random
import urllib.parse
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WORKER_BASE = "https://vape-x402.vapex402.workers.dev"
NETWORK = "eip155:8453"  # Base mainnet — same network the worker's PAY_TO_ADDRESS settles on

DAILY_CAP = 60  # VAPOR-pinned instance only now (agents/data_agent_vapor.py) — see module docstring
HIRES_PER_RUN = 1
MIN_INTERVAL_SECONDS = 30 * 60  # VAPOR-pinned instance only now — see module docstring
CATALOG_DAILY_CAP = 48  # no longer enforced by run_catalog_sweep() itself (growth-paced instead,
                        # see _daily_targets()) — kept only as a historical reference value

# ── CDP-pinned growing-minimum target (see module docstring) ────────────────
GROWTH_BASE_DAILY = 100       # combined target across both CDP streams, day one
GROWTH_RATE_PER_DAY = 0.01    # +1% more, compounding, every day after — unbounded
GROWTH_EPOCH_PATH = os.path.join(ROOT, "skillforge", "memory", "data_agent_growth.json")
# Sanity floor only — never fire more than once/minute regardless of what the
# pacing math computes (e.g. a corrupted/missing epoch file), independent of
# how large the growing target ever gets.
ABSOLUTE_MIN_INTERVAL_SECONDS = 60


def _growth_epoch():
    """The date the CDP growing-minimum mechanism first activated —
    persisted once, read forever after (today == epoch means day one,
    GROWTH_BASE_DAILY transactions; every day after compounds
    GROWTH_RATE_PER_DAY higher). Never raises: any read/write failure just
    restarts the curve at "today" rather than blocking the agent."""
    try:
        with open(GROWTH_EPOCH_PATH) as f:
            epoch = json.load(f).get("epoch")
        if epoch:
            return epoch
    except Exception:
        pass
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        os.makedirs(os.path.dirname(GROWTH_EPOCH_PATH), exist_ok=True)
        with open(GROWTH_EPOCH_PATH, "w") as f:
            json.dump({"epoch": today}, f)
    except Exception:
        pass
    return today


def _daily_target_combined():
    """Today's combined minimum x402-transaction count across BOTH CDP
    streams (main + catalog) — GROWTH_BASE_DAILY on day one, compounding
    GROWTH_RATE_PER_DAY higher every day after, forever. VAPOR
    (agents/data_agent_vapor.py) is deliberately not part of this."""
    try:
        epoch = datetime.strptime(_growth_epoch(), "%Y-%m-%d").date()
        day_index = max(0, (datetime.now(timezone.utc).date() - epoch).days)
    except Exception:
        day_index = 0
    return GROWTH_BASE_DAILY * ((1 + GROWTH_RATE_PER_DAY) ** day_index)


def _daily_targets():
    """(main_target, catalog_target) whole-number split of today's combined
    growing target — ceil on the whole and on the main half so the two
    always sum to at least the true (fractional) combined target, never
    less, after independent rounding."""
    combined = math.ceil(_daily_target_combined())
    main = math.ceil(combined / 2)
    return main, combined - main


def _due_now(state, target_today):
    """Deadline-driven pacing toward a growing MINIMUM, recomputed fresh on
    every call from how much of today's target is still outstanding and how
    much of the day is left — not a fixed cadence. A missed or delayed poll
    doesn't lose that slot forever: the next call simply finds a shorter
    required wait and catches up, the same principle as a leaky-bucket
    limiter aimed at a floor instead of a ceiling. Once today's target is
    already met, this stays not-due for the rest of the day (a real
    overshoot from another stream firing independently is fine and expected
    — never corrected downward). Returns (due: bool, remaining_target: int)."""
    remaining = target_today - state.count_today()
    if remaining <= 0:
        return False, 0
    now = datetime.now(timezone.utc)
    seconds_left_today = 86400 - (now.hour * 3600 + now.minute * 60 + now.second)
    needed_interval = max(ABSOLUTE_MIN_INTERVAL_SECONDS, seconds_left_today / remaining)
    since_last = state.seconds_since_last_attempt()
    if since_last is not None and since_last < needed_interval:
        return False, remaining
    return True, remaining

# Mirrors agents/investigate.py::EVM_CHAINS' name/gecko/dex fields exactly —
# duplicated here rather than imported to keep this module's only real
# cross-agent coupling (data_agent_vapor.py importing this file) as it is;
# update both places if a chain is ever added/renamed. defillama_fee_slug is
# DefiLlama's own lowercase path slug (confirmed against agents/defillama.py's
# chain_fees()/dex_volumes() — NOT the same string as the GeckoTerminal/
# DexScreener slugs in the other two fields for every chain, e.g. Avalanche
# is "avax" here but "avalanche" for DexScreener).
CHAIN_META = {
    "Base":      {"id": "8453",  "gecko": "base",       "dex": "base",      "defillama_fee_slug": "base"},
    "Ethereum":  {"id": "1",     "gecko": "eth",        "dex": "ethereum",  "defillama_fee_slug": "ethereum"},
    "Arbitrum":  {"id": "42161", "gecko": "arbitrum",   "dex": "arbitrum",  "defillama_fee_slug": "arbitrum"},
    "Optimism":  {"id": "10",    "gecko": "optimism",   "dex": "optimism",  "defillama_fee_slug": "optimism"},
    "Polygon":   {"id": "137",   "gecko": "polygon_pos", "dex": "polygon",  "defillama_fee_slug": "polygon"},
    "BNB Chain": {"id": "56",    "gecko": "bsc",        "dex": "bsc",       "defillama_fee_slug": "bsc"},
    "Avalanche": {"id": "43114", "gecko": "avax",       "dex": "avalanche", "defillama_fee_slug": "avax"},
}

# Every one of VAPE's real x402 offerings priced $0.02 or less (worker/src/
# index.ts's OFFERING_PRICES + worker/src/dataHandlers.ts's DL_OFFERINGS —
# see agents/x402_directory_register.py for the same source-of-truth split),
# tagged with how run_catalog_sweep() below resolves its input:
#   - "address": needs a real token address+chain — sourced via
#     _fresh_candidate(), which is also what grows data/token_database.jsonl.
#   - "chain": needs just a chain name/slug — no address involved.
#   - "protocol": needs a real DefiLlama protocol slug — sourced via
#     agents.defillama.protocols_on_chain(), never guessed.
#   - "none": no input at all.
CATALOG_OFFERINGS = [
    ("exploit_check", "scan", "address"),
    ("token_safety_check", "scan", "address"),
    ("liquidity_check", "scan", "address"),
    ("token_intel", "data", "address"),
    ("token_chart", "data", "address"),
    ("protocol", "data", "protocol"),
    ("protocol_fees", "data", "protocol"),
    ("unlocks", "data", "protocol"),
    ("treasury", "data", "protocol"),
    ("chain_protocols", "data", "chain"),
    ("chain_overview", "data", "chain"),
    ("chain_fees", "data", "chain"),
    ("dex_volumes", "data", "chain"),
    ("yields", "data", "none"),
    ("stablecoins", "data", "none"),
    ("bridges", "data", "none"),
    ("prediction_market_odds", "data", "none"),
]

# Real, growing dataset of tokens/projects DATA AGENT has actually paid to
# look up — a new VAPE data asset in its own right, not just a dedup ledger.
# Append-only NDJSON, one record per successful address-based catalog hire.
TOKEN_DB_PATH = os.path.join(ROOT, "data", "token_database.jsonl")
# How long a (chain, address) is considered "recently seen" and skipped in
# favor of a fresh one — keeps the dataset varied instead of a few tokens
# dominating it, per the module docstring.
TOKEN_DB_COOLDOWN_HOURS = 12
# Only the tail needs scanning for the recency check — this file is meant to
# grow into the thousands, and a full-file scan every 30m would only get
# slower over time for no benefit (nothing past this many recent lines could
# still be "recently seen" at any realistic hire cadence).
TOKEN_DB_RECENT_SCAN_LINES = 3000

# Real, funded wallet the user provisioned for this agent — a fund-moving
# action never proceeds unless DATA_AGENT_PRIVATE_KEY actually derives this
# exact address (see _build_session()). Both facilitator-pinned instances
# share the same wallet: the facilitator is just the settlement rail, not
# the payer's identity, so there's no reason to need a second funded wallet.
EXPECTED_WALLET = "0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15"

# name -> (address) -> query params, for run_for_investigation()/
# run_standalone() — Base-only, no protocol-slug offerings (see module
# docstring). run_catalog_sweep() below is the separate stream that covers
# protocol/protocol_fees/unlocks/treasury and every other chain.
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


def _recent_token_db_addresses():
    """Set of (chain, lowercased address) seen within TOKEN_DB_COOLDOWN_HOURS,
    read from the tail of TOKEN_DB_PATH only (see its constant's comment for
    why). Missing/unreadable file -> empty set, never raises."""
    seen = set()
    if not os.path.exists(TOKEN_DB_PATH):
        return seen
    cutoff = datetime.now(timezone.utc) - timedelta(hours=TOKEN_DB_COOLDOWN_HOURS)
    try:
        with open(TOKEN_DB_PATH) as f:
            lines = f.readlines()[-TOKEN_DB_RECENT_SCAN_LINES:]
        for line in lines:
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
                if ts >= cutoff:
                    seen.add((str(rec.get("chain")), str(rec.get("address", "")).lower()))
            except Exception:
                continue
    except Exception:
        pass
    return seen


def _record_token_db(address, chain, symbol, name, source, offering):
    """Append one real observation to data/token_database.jsonl — see that
    constant's comment. Best-effort: a write failure here must never break
    the hire that triggered it."""
    try:
        os.makedirs(os.path.dirname(TOKEN_DB_PATH), exist_ok=True)
        with open(TOKEN_DB_PATH, "a") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "address": address, "chain": chain, "symbol": symbol, "name": name,
                "source": source, "offering": offering,
            }) + "\n")
    except Exception as e:
        print(f"[data_agent] token_database.jsonl write failed (non-fatal): {e}")


def _resolve_mover_address(mover_name, dex_slug):
    """A GeckoTerminal mover is pool-named ("TOKEN/USD"), not address-keyed —
    resolve it to a real address via DexScreener search + exact chain match,
    same technique agents/investigate.py::auto_target() already uses. None
    on no match, never raises."""
    try:
        from agents import data_fetchers as DF
    except Exception:
        try:
            import data_fetchers as DF
        except Exception:
            return None
    name = (mover_name or "").split("/")[0].strip()
    if not name:
        return None
    d = DF._get(f"https://api.dexscreener.com/latest/dex/search?q={urllib.parse.quote(name)}")
    for p in (d.get("pairs") or []) if isinstance(d, dict) else []:
        if str(p.get("chainId", "")).lower() == dex_slug:
            addr = (p.get("baseToken") or {}).get("address")
            sym = (p.get("baseToken") or {}).get("symbol")
            if addr:
                return addr, sym
    return None


def _fresh_candidate(only_base=False):
    """Picks a real, fresh (not recently hired) token address for
    run_catalog_sweep()'s address-based offerings (and run_standalone()'s
    Base-only hire) — sourced from Base movers, a random other EVM chain's
    movers, or the worker's own free /trending-base feed (Virtuals-tagged
    tokens included), per the module docstring. Returns
    (address, chain_id, symbol, name, source_tag) or None if every source
    came up empty/already-recently-seen this cycle.
    """
    try:
        from agents import data_fetchers as DF
    except Exception:
        try:
            import data_fetchers as DF
        except Exception:
            return None

    recent = _recent_token_db_addresses()

    def _try_mover(chain_name, chain_id, source_tag):
        meta = CHAIN_META[chain_name]
        get_movers = getattr(DF, "get_evm_movers", None)
        if not get_movers:
            return None
        movers = get_movers(meta["gecko"], limit=40)
        for m in (movers.get("biggest_movers") or []):
            resolved = _resolve_mover_address(m.get("name"), meta["dex"])
            if not resolved:
                continue
            addr, sym = resolved
            if (chain_id, addr.lower()) in recent:
                continue
            return addr, chain_id, sym, m.get("name", "").split("/")[0].strip(), source_tag
        return None

    def _try_virtuals():
        try:
            import requests
            r = requests.get(f"{WORKER_BASE}/trending-base", timeout=15)
            if r.status_code != 200:
                return None
            tokens = r.json().get("tokens") or []
        except Exception:
            return None
        virtuals_first = [t for t in tokens if t.get("isVirtuals")] + tokens
        for t in virtuals_first:
            tok = t.get("token") or {}
            addr = tok.get("address")
            if not addr or ("8453", addr.lower()) in recent:
                continue
            source_tag = "virtuals" if t.get("isVirtuals") else "base_trending"
            return addr, "8453", tok.get("symbol"), tok.get("name"), source_tag
        return None

    sources = ["base"] if only_base else random.sample(["base", "evm", "virtuals"], 3)
    for s in sources:
        if s == "base":
            found = _try_mover("Base", CHAIN_META["Base"]["id"], "base")
        elif s == "virtuals":
            found = _try_virtuals()
        else:
            chain_name = random.choice([c for c in CHAIN_META if c != "Base"])
            found = _try_mover(chain_name, CHAIN_META[chain_name]["id"], "evm")
        if found:
            return found
    return None


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

    def count_today(self):
        """Raw hires-so-far-today count, with no fixed-cap assumption baked
        in (unlike remaining_today(), which is DAILY_CAP-relative and only
        meaningful for the VAPOR-pinned instance now) — what the CDP
        growth-paced gate (_due_now()) actually needs."""
        q = self._load_quota()
        if q.get("date") != self._today():
            return 0
        return q.get("count", 0)

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


def hire(session, offering, params, prefix="data"):
    """Pay for and fetch one x402 offering at /<prefix>/<offering> — prefix
    is "data" for the DL_OFFERINGS market-data tier (the only tier this
    module hired before run_catalog_sweep() below) or "scan" for the
    security-check tier (exploit_check/token_safety_check/liquidity_check),
    matching worker/src/index.ts's own route split.

    Returns (deliverable_or_error_dict, paid) — paid is True iff the request
    reached the paid endpoint and got back HTTP 200 (real settlement
    happened), even if the deliverable itself reports an upstream miss
    (status: "error" — a genuine attempt, same as any paid job that comes
    back with "no data"). paid is False on any network/HTTP failure, since
    no settlement can be assumed. Never raises.
    """
    try:
        r = session.get(f"{WORKER_BASE}/{prefix}/{offering}", params=params, timeout=20)
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
    """Original fixed-cap/fixed-interval core — now used ONLY by the
    VAPOR-pinned instance (agents/data_agent_vapor.py), left completely
    unchanged on purpose (see module docstring: the CDP-pinned instance's
    own run_for_investigation()/run_standalone() below call _run_growth()
    instead, a separate function rather than a new parameter here, so
    VAPOR's behavior can never be accidentally altered by a change aimed at
    CDP's growth pacing). Hires 1 random $0.01 x402 offering against
    `address` (capped at DAILY_CAP total paid hires/day, and no more often
    than once every 30m regardless of how often this is called) and returns
    what it bought so a caller (agents/investigate.py's report, or
    run_standalone() below) can fold it in.

    address=None means "pick your own fresh Base candidate" — this is what
    decouples the cadence from needing a successful auto-investigation to
    hand it one (see run_standalone()); chain is always "8453" in that case.
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

    if address is None:
        found = _fresh_candidate(only_base=True)
        if not found:
            return {"hired": [], "note": "no fresh Base candidate found this cycle — skipped"}
        address = found[0]

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


def _run_growth(address, chain, *, client_tag, state, log_prefix, target_today):
    """CDP-only growth-paced sibling of _run() — see module docstring's
    "Rate limits, CDP-pinned instance" section. Deliberately a separate
    function rather than a parameter on _run() itself: agents/
    data_agent_vapor.py calls _run() directly and must keep its own original
    fixed 30-min/DAILY_CAP behavior completely unchanged, so _run()'s gating
    logic is left untouched here — this duplicates its hire-and-log body
    with _due_now()'s adaptive gate in place of the fixed interval+cap pair.

    address=None means "pick your own fresh Base candidate" (see _run()'s
    own docstring for why) — chain is always "8453" in that case.
    """
    if str(chain) != "8453":
        return {"hired": [], "note": "data agent only wired for Base (8453) investigations"}

    due, remaining = _due_now(state, target_today)
    if not due:
        return {"hired": [], "note": f"not due yet ({remaining}/{target_today} still owed today "
                                      "— pacing to the growing minimum, not a fixed cadence)"}

    if address is None:
        found = _fresh_candidate(only_base=True)
        if not found:
            return {"hired": [], "note": "no fresh Base candidate found this cycle — skipped"}
        address = found[0]

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
        "daily_target": target_today,
    })
    print(f"[{log_prefix}] {address}: hired {[h['offering'] for h in hired]}, "
          f"paid {paid_count}, ${cost_usd:.2f} (day target {target_today}, "
          f"{remaining - paid_count} still owed today)")
    return {"hired": hired, "cost_usd": cost_usd}


def _run_catalog(*, client_tag, state, log_prefix):
    """The catalog-sweep stream — see module docstring. Own growth-paced
    gate (_due_now(), against this stream's own half-share of the growing
    combined target — see _daily_targets()), independent of _run_growth()'s.
    Picks 1 random offering from CATALOG_OFFERINGS, resolves a real input
    for it (a fresh token address, a real DefiLlama protocol slug, a chain
    name, or none), hires it, and — for address-based offerings — records
    the observation into data/token_database.jsonl. Never raises.
    """
    _, catalog_target = _daily_targets()
    due, remaining = _due_now(state, catalog_target)
    if not due:
        return {"hired": [], "note": f"not due yet ({remaining}/{catalog_target} still owed today "
                                      "— pacing to the growing minimum, not a fixed cadence)"}

    name, prefix, kind = random.choice(CATALOG_OFFERINGS)
    params = {}
    db_record = None

    if kind == "address":
        found = _fresh_candidate()
        if not found:
            return {"hired": [], "note": f"no fresh candidate found for {name} this cycle — skipped"}
        addr, chain_id, sym, tok_name, source = found
        if name in ("token_intel", "token_chart"):
            # These two take a DefiLlama lowercase chain *slug* (confirmed
            # against worker/src/dataHandlers.ts -> agents/defillama.py's
            # token_price_chart()), not the numeric chain id below.
            chain_by_id = {m["id"]: cname for cname, m in CHAIN_META.items()}
            chain_name = chain_by_id.get(chain_id, "Base")
            params = {"address": addr, "chain": CHAIN_META[chain_name]["defillama_fee_slug"]}
        else:
            # exploit_check/token_safety_check/liquidity_check are /scan/
            # routes (worker/src/index.ts) that take the numeric chain id —
            # required here since _fresh_candidate() can return a non-Base
            # address; omitting it would make the worker silently analyze
            # the wrong chain's state at that address (defaults to 8453).
            params = {"address": addr, "chain": chain_id}
        db_record = (addr, chain_id, sym, tok_name, source)
    elif kind == "protocol":
        try:
            from agents import defillama as DL
        except Exception:
            try:
                import defillama as DL
            except Exception:
                DL = None
        chain_name = random.choice(list(CHAIN_META.keys()))
        protos = (DL.protocols_on_chain(chain_name, top_n=20) or {}).get("protocols") if DL else None
        real_slugs = [p["slug"] for p in (protos or []) if p.get("slug")]
        if not real_slugs:
            return {"hired": [], "note": f"no real DefiLlama protocol slug found on {chain_name} this cycle — skipped"}
        params = {"slug": random.choice(real_slugs)}
    elif kind == "chain":
        chain_name = random.choice(list(CHAIN_META.keys()))
        meta = CHAIN_META[chain_name]
        params = {"chain": chain_name if name in ("chain_protocols", "chain_overview") else meta["defillama_fee_slug"]}
    # kind == "none": params stays {}

    session = _build_session(client_tag)
    if session is None:
        return {"hired": [], "note": "DATA_AGENT_PRIVATE_KEY not configured or invalid — skipped"}

    state.mark_attempt()
    deliverable, paid = hire(session, name, params, prefix=prefix)
    if paid and db_record:
        _record_token_db(*db_record, offering=name)

    state.record_hires(1 if paid else 0)
    cost_usd = 0.02 if paid and name in ("token_safety_check", "liquidity_check") else (0.01 if paid else 0.0)
    state.log_ledger({
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "target": params.get("address") or params.get("slug") or params.get("chain") or "none",
        "hired": [name], "paid": 1 if paid else 0, "cost_usd": cost_usd,
        "daily_target": catalog_target,
    })
    print(f"[{log_prefix}] catalog sweep: hired {name} ({params}), paid={paid}, ${cost_usd:.2f} "
          f"(day target {catalog_target}, {remaining - (1 if paid else 0)} still owed today)")
    return {"hired": [{"offering": name, "params": params, "deliverable": deliverable, "paid": paid}],
            "cost_usd": cost_usd}


_CDP_STATE = _State("data_agent")
_CDP_CATALOG_STATE = _State("data_agent_catalog")


def run_for_investigation(address, chain="8453"):
    """Recruited by agents/investigate.py::investigate() for every real
    report — CDP-pinned instance (X-VAPE-Client: data-agent). Paced toward
    the growing daily minimum (see module docstring), not a fixed cap."""
    main_target, _ = _daily_targets()
    return _run_growth(address, chain, client_tag="data-agent", state=_CDP_STATE,
                       log_prefix="data_agent", target_today=main_target)


def run_standalone():
    """CDP-pinned instance, decoupled from investigate.py entirely — self-
    sources a fresh Base candidate every call. Called on a fixed schedule
    (see .github/workflows/featured-investigation.yml) regardless of whether
    that cycle's auto-investigation found anything, per the module docstring.
    Paced toward the growing daily minimum, not a fixed cap."""
    main_target, _ = _daily_targets()
    return _run_growth(None, "8453", client_tag="data-agent", state=_CDP_STATE,
                       log_prefix="data_agent", target_today=main_target)


def run_catalog_sweep():
    """CDP-pinned instance only (see module docstring for why this stream
    isn't doubled across both facilitator instances) — sweeps through every
    x402 offering priced $0.02 or less, paced toward its own half-share of
    the growing daily minimum."""
    return _run_catalog(client_tag="data-agent", state=_CDP_CATALOG_STATE, log_prefix="data_agent")
