"""
VAPE x402 ledger backfill — one-time reconstruction of pre-ledger paid jobs
from real on-chain history. Run manually via workflow_dispatch only, never
scheduled: this is a maintenance operation, not a recurring job.

Context: worker/src/lib/jobLog.ts only started logging paid /scan/* jobs
once VAPE_JOBS_KV_ID was configured (see skillforge/memory/build_log.jsonl
for that story). Every USDC payment settled to VAPE's wallet before that
point is real and on-chain, but was never recorded in the ledger's KV
store — this script reconstructs those entries so "The Ledger" site
section reflects VAPE's actual full history, not just activity since the
KV binding went live.

Data source: Base's public RPC (mainnet.base.org), reading real USDC
Transfer(address,address,uint256) event logs directly via eth_getLogs —
NOT Etherscan. Etherscan V2's free API tier returns "Free API access is
not supported for this chain" for the tokentx/txlist history endpoints on
L2s like Base (confirmed live, 2026-07-06) even though its
contract/getsourcecode endpoint works fine cross-chain on the same free
key — a real, undocumented-until-you-hit-it tier restriction. The RPC
path is keyless, needs no new secret, and is the same public endpoint
already used elsewhere in this repo (agents/investigate.py, etc).

Honesty constraint, deliberate: which OFFERING a historical payment was
for can only be inferred from its USD amount, and offering prices changed
over time (PRICE_HISTORY below, reconstructed from `git log -p` on
worker/src/index.ts and agents/publish_reputation.py) — plus one real
price collision has always existed (token_safety_check and
liquidity_check have both always been $0.02). Where the amount doesn't
uniquely identify one offering, the record says so plainly (e.g.
"token_safety_check or liquidity_check") instead of guessing — a wrong
guess is worse than an honest "unknown", same rule this repo applies
everywhere else.

Writes directly into the same Cloudflare KV namespace worker/src/lib/
jobLog.ts uses, via Cloudflare's REST API (this runs in GitHub Actions,
outside the Workers runtime, so it can't import that file directly) —
replicating its exact RECENT_JOBS/TOTALS/DAILY_HISTORY read-modify-write
shape so the two data sources never drift apart. Dedupes by
transaction hash, so it's safe to re-run (e.g. periodically, to catch any
new real transfer that predates this ledger's specific launch moment —
though going forward every new payment is already logged live).

Usage (CI only — needs these as env vars):
  CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, VAPE_JOBS_KV_ID
  Optional: X402_BACKFILL_LOOKBACK_DAYS (default 30)
  Optional: X402_BACKFILL_RESET=true — drop and reclassify every
    previously-backfilled record from scratch (e.g. after fixing a bug in
    the amount-matching logic below); live-logged records are untouched.
    python -m agents.x402_ledger_backfill
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

PAY_TO_ADDRESS = "0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CHAIN_ID = 8453
BASE_RPC = "https://mainnet.base.org"
# keccak256("Transfer(address,address,uint256)") — the standard ERC-20
# Transfer event topic, identical across every ERC-20 token.
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
# eth_getLogs topic filters are 32-byte, left-zero-padded — this is
# PAY_TO_ADDRESS as the log's indexed `to` (topics[2]).
PAY_TO_TOPIC = "0x" + "0" * 24 + PAY_TO_ADDRESS[2:].lower()
BASE_BLOCK_TIME_SEC = 2
# Conservative starting chunk size for eth_getLogs — public RPC providers
# commonly cap the block range per call; shrinks automatically on error.
LOG_CHUNK_BLOCKS = 2000

# Every USD price this offering has EVER been listed at (not just its
# current price) — reconstructed from real git history, not assumed.
PRICE_HISTORY = {
    "exploit_check": [0.01],
    "rug_pull_alert": [0.03],
    "market_intel": [0.07, 0.15],
    # registered/priced under the old name "safety_preflight" for part of
    # this history, before the dossier_check rename.
    "dossier_check": [0.05, 0.10, 0.35],
    # $50 was the price through 2026-07-19; repriced to $1 after that.
    "bounty_deep_dive": [50.00, 1.00],
}
# token_safety_check and liquidity_check have ALWAYS both been $0.02 —
# genuinely no way to tell them apart from amount alone after the fact.
AMBIGUOUS_PRICES = {0.02: ["token_safety_check", "liquidity_check"]}

CF_API = "https://api.cloudflare.com/client/v4"
UA = {"User-Agent": "VAPE-x402-ledger-backfill/1.0"}


def offering_for_amount(usd):
    matches = [name for name, prices in PRICE_HISTORY.items() if any(abs(usd - p) < 1e-6 for p in prices)]
    if usd in AMBIGUOUS_PRICES:
        return " or ".join(AMBIGUOUS_PRICES[usd])
    if len(matches) == 1:
        return matches[0]
    if matches:
        return " or ".join(matches)
    return f"unknown (${usd:.2f})"


def rpc_call(method, params):
    """Handles HTTP 429 (rate limited) itself, centrally, for every RPC
    call this script makes — confirmed live that a second full scan run
    shortly after a successful first one gets rate-limited by the public
    RPC. Backing off and retrying the SAME request is the right response
    to a 429; it's a different failure mode from a "block range too
    large" error, which needs a smaller range instead (handled by the
    caller, since only eth_getLogs has a range to shrink)."""
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    backoff = 1.0
    while True:
        try:
            req = urllib.request.Request(BASE_RPC, data=payload, headers={**UA, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            if "error" in data:
                raise RuntimeError(f"Base RPC error ({method}): {data['error']}")
            time.sleep(0.15)  # pace requests — be a good citizen on a public, shared RPC
            return data["result"]
        except urllib.error.HTTPError as e:
            if e.code != 429 or backoff > 60:
                raise
            print(f"Rate-limited (HTTP 429) on {method} — backing off {backoff:.0f}s...")
            time.sleep(backoff)
            backoff *= 2


def fetch_usdc_transfer_logs(lookback_days):
    """Real USDC Transfer event logs (to PAY_TO_ADDRESS only) from Base's
    public RPC, paginated in chunks since eth_getLogs caps the block range
    per call on public providers — shrinks the chunk and retries the same
    window on a range-related error (rpc_call already handles rate limits
    on its own, so anything reaching here is assumed range-related)."""
    latest = int(rpc_call("eth_blockNumber", []), 16)
    blocks_per_day = 86400 // BASE_BLOCK_TIME_SEC
    from_block = max(0, latest - lookback_days * blocks_per_day)
    print(f"Scanning Base blocks {from_block:,} to {latest:,} (~{lookback_days}d) for USDC transfers to {PAY_TO_ADDRESS}...")

    logs = []
    start = from_block
    chunk = LOG_CHUNK_BLOCKS
    while start <= latest:
        end = min(start + chunk - 1, latest)
        try:
            result = rpc_call("eth_getLogs", [{
                "fromBlock": hex(start), "toBlock": hex(end),
                "address": USDC_BASE,
                "topics": [TRANSFER_TOPIC, None, PAY_TO_TOPIC],
            }])
            logs.extend(result)
            start = end + 1
        except (RuntimeError, urllib.error.HTTPError) as e:
            if chunk <= 50:
                raise RuntimeError(f"eth_getLogs failed even at minimum chunk size: {e}")
            chunk = max(50, chunk // 2)
    return logs


def block_timestamp(cache, block_number_hex):
    if block_number_hex not in cache:
        block = rpc_call("eth_getBlockByNumber", [block_number_hex, False])
        cache[block_number_hex] = int(block["timestamp"], 16)
    return cache[block_number_hex]


def cf_kv_get(account_id, namespace_id, token, key):
    url = f"{CF_API}/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
    req = urllib.request.Request(url, headers={**UA, "Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            # This specific KV endpoint returns the raw stored value (not the
            # usual {success, result} envelope) — the raw value IS the JSON
            # text jobLog.ts wrote via kv.put(key, JSON.stringify(...)).
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise RuntimeError(f"Cloudflare KV GET {key} failed: HTTP {e.code} — {e.read().decode()[:300]}")


def recompute_aggregates(recent):
    """Derives TOTALS/DAILY_HISTORY authoritatively from a final `recent`
    list, rather than trusting incrementally-mutated running totals — used
    right before writing so a merge that adds/removes records afterward
    can't leave totals drifted from what's actually in `recent`."""
    totals = {"jobs": 0, "errors": 0, "revenue_usd": 0, "first_job_ts": None, "last_job_ts": None, "by_offering": {}}
    daily_by_date = {}
    for j in recent:
        totals["jobs"] += 1
        if j.get("status") == "error":
            totals["errors"] += 1
        else:
            totals["revenue_usd"] = round(totals["revenue_usd"] + j["amount_usd"], 6)
        totals["first_job_ts"] = min(totals["first_job_ts"], j["ts"]) if totals["first_job_ts"] else j["ts"]
        totals["last_job_ts"] = max(totals["last_job_ts"], j["ts"]) if totals["last_job_ts"] else j["ts"]
        off = totals["by_offering"].get(j["offering"], {"count": 0, "revenue_usd": 0})
        off["count"] += 1
        if j.get("status") != "error":
            off["revenue_usd"] = round(off["revenue_usd"] + j["amount_usd"], 6)
        totals["by_offering"][j["offering"]] = off
        day = j["ts"][:10]
        entry = daily_by_date.setdefault(day, {"date": day, "jobs": 0, "revenue_usd": 0})
        entry["jobs"] += 1
        if j.get("status") != "error":
            entry["revenue_usd"] = round(entry["revenue_usd"] + j["amount_usd"], 6)
    return totals, daily_by_date


def cf_kv_put(account_id, namespace_id, token, key, value, ttl=None):
    url = f"{CF_API}/accounts/{account_id}/storage/kv/namespaces/{namespace_id}/values/{key}"
    if ttl:
        url += f"?expiration_ttl={ttl}"
    body = json.dumps(value).encode()
    req = urllib.request.Request(url, data=body, headers={**UA, "Authorization": f"Bearer {token}"}, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Cloudflare KV PUT {key} failed: HTTP {e.code} — {e.read().decode()[:300]}")
    if not resp.get("success"):
        raise RuntimeError(f"Cloudflare KV PUT {key} reported failure: {resp}")


def main():
    cf_token = os.environ["CLOUDFLARE_API_TOKEN"]
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    namespace_id = os.environ["VAPE_JOBS_KV_ID"]
    lookback_days = int(os.environ.get("X402_BACKFILL_LOOKBACK_DAYS", "30"))

    logs = fetch_usdc_transfer_logs(lookback_days)
    print(f"Found {len(logs)} real incoming USDC transfer(s) on-chain.")

    # RESET_FIRST: re-derive RECENT_JOBS/TOTALS from scratch instead of
    # appending. Real use case, not speculative: this script infers
    # `offering` from amount, so a fix to that inference logic (or a fix
    # to PRICE_HISTORY) only actually corrects already-written entries if
    # they're regenerated — dedup-by-hash otherwise silently preserves the
    # old, now-wrong labels forever. Only reprocesses entries this script
    # itself wrote (backfilled: true); anything logged live by jobLog.ts
    # is real observed data, never touched.
    reset_first = os.environ.get("X402_BACKFILL_RESET", "").lower() in ("1", "true", "yes")
    if reset_first:
        recent = cf_kv_get(account_id, namespace_id, cf_token, "RECENT_JOBS") or []
        live_only = [j for j in recent if not j.get("backfilled")]
        dropped = len(recent) - len(live_only)
        print(f"X402_BACKFILL_RESET set — dropping {dropped} previously-backfilled record(s) to reclassify from scratch (keeping {len(live_only)} live-logged record(s)).")
        recent = live_only
        totals, daily_by_date = recompute_aggregates(recent)
    else:
        recent = cf_kv_get(account_id, namespace_id, cf_token, "RECENT_JOBS") or []
    seen_hashes = {j.get("tx_hash") for j in recent if j.get("tx_hash")}
    block_ts_cache = {}

    added = 0
    for log in logs:
        tx_hash = log.get("transactionHash")
        if not tx_hash or tx_hash in seen_hashes:
            continue
        from_addr = "0x" + log["topics"][1][-40:]
        # USDC on Base is always 6 decimals (its real, fixed contract
        # property — not something that varies per transfer).
        amount_usd = round(int(log["data"], 16) / 1_000_000, 6)
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(block_timestamp(block_ts_cache, log["blockNumber"])))
        record = {
            "id": f"{ts_iso}-backfill-{tx_hash[2:10]}",
            "ts": ts_iso,
            # amount_usd is already an exact figure derived from atomic USDC
            # units — do NOT round to cents before matching. x402's "exact"
            # payment scheme means a real offering payment lands at its
            # quoted price to the atomic unit; rounding here previously let
            # near-miss amounts (e.g. $0.0089) falsely match a $0.01 price.
            "offering": offering_for_amount(amount_usd),
            "address": None, "chain_id": CHAIN_ID,
            "symbol": None, "name": None, "verdict": None,
            "status": "settled", "amount_usd": amount_usd, "latency_ms": None,
            "payer": from_addr, "tx_hash": tx_hash, "network": "eip155:8453",
            "error": None, "backfilled": True,
        }
        recent.append(record)
        seen_hashes.add(tx_hash)
        added += 1

    if not added and not reset_first:
        print("Nothing new to backfill — every real on-chain transfer is already logged (or none exist yet).")
        return 0

    # This script's own initial read (above) can be arbitrarily stale by the
    # time we're ready to write — a real paid job can land live via
    # worker/src/lib/jobLog.ts's onAfterSettle hook at any point in
    # between, on a completely separate process/runtime this script has no
    # way to coordinate with directly. A blind overwrite here would erase
    # that job from the ledger even though the payment itself is real and
    # already settled on-chain. Re-read immediately before writing and
    # merge in anything new from a fresher read (deduping by `id`, which is
    # unique across both live and backfilled records), so a race narrows to
    # "still possible in the instant between this re-read and the write"
    # rather than "over this whole script's multi-minute chain scan."
    fresh_recent = cf_kv_get(account_id, namespace_id, cf_token, "RECENT_JOBS") or []
    known_ids = {j["id"] for j in recent if j.get("id")}
    newly_live = [j for j in fresh_recent if j.get("id") and j["id"] not in known_ids]
    if newly_live:
        print(f"Merging {len(newly_live)} record(s) logged live since this run's initial read.")
        recent.extend(newly_live)

    totals, daily_by_date = recompute_aggregates(recent)
    recent.sort(key=lambda j: j["ts"], reverse=True)
    cf_kv_put(account_id, namespace_id, cf_token, "RECENT_JOBS", recent[:200])
    cf_kv_put(account_id, namespace_id, cf_token, "TOTALS", totals)
    daily_history = sorted(daily_by_date.values(), key=lambda d: d["date"])[-400:]
    cf_kv_put(account_id, namespace_id, cf_token, "DAILY_HISTORY", daily_history)

    print(f"Backfilled {added} real historical job(s) from on-chain data.")
    print(json.dumps(totals, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
