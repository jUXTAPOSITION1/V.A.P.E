"""
VAPE x402 ledger backfill — one-time reconstruction of pre-ledger paid jobs
from real on-chain history. Run manually via workflow_dispatch only, never
scheduled: this is a maintenance operation, not a recurring job.

Context: worker/src/lib/jobLog.ts only started logging paid /scan/* jobs
once VAPE_JOBS_KV_ID was configured (see skillforge/memory/build_log.jsonl
for that story). Every USDC payment settled to VAPE's wallet before that
point is real and on-chain, but was never recorded in the ledger's KV
store — this script reconstructs those entries from Etherscan's
token-transfer history for PAY_TO_ADDRESS, so "The Ledger" site section
reflects VAPE's actual full history, not just activity since the KV
binding went live.

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
replicating its exact RECENT_JOBS/TOTALS/STATS_DAILY:<date> read-modify-
write shape so the two data sources never drift apart. Dedupes by
transaction hash, so it's safe to re-run (e.g. periodically, to catch any
new real transfer that predates this ledger's specific launch moment —
though going forward every new payment is already logged live).

Usage (CI only — needs these as env vars):
  ETHERSCAN_API_KEY, CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, VAPE_JOBS_KV_ID
    python -m agents.x402_ledger_backfill
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PAY_TO_ADDRESS = "0xa1420293a7df49bc8380f543a1fe7b8d6f582879"
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
CHAIN_ID = 8453

# Every USD price this offering has EVER been listed at (not just its
# current price) — reconstructed from real git history, not assumed.
PRICE_HISTORY = {
    "exploit_check": [0.01],
    "rug_pull_alert": [0.03],
    "market_intel": [0.07, 0.15],
    # registered/priced under the old name "safety_preflight" for part of
    # this history, before the dossier_check rename.
    "dossier_check": [0.05, 0.10, 0.35],
    "bounty_deep_dive": [50.00],
}
# token_safety_check and liquidity_check have ALWAYS both been $0.02 —
# genuinely no way to tell them apart from amount alone after the fact.
AMBIGUOUS_PRICES = {0.02: ["token_safety_check", "liquidity_check"]}

ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"
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


def fetch_usdc_transfers(api_key):
    q = urllib.parse.urlencode({
        "chainid": CHAIN_ID, "module": "account", "action": "tokentx",
        "address": PAY_TO_ADDRESS, "contractaddress": USDC_BASE,
        "sort": "asc", "apikey": api_key,
    })
    req = urllib.request.Request(f"{ETHERSCAN_V2}?{q}", headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    if data.get("status") != "1" and data.get("message") != "No transactions found":
        raise RuntimeError(f"Etherscan error: {data.get('message')} — {data.get('result')}")
    return data.get("result") or []


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
    etherscan_key = os.environ["ETHERSCAN_API_KEY"]
    cf_token = os.environ["CLOUDFLARE_API_TOKEN"]
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    namespace_id = os.environ["VAPE_JOBS_KV_ID"]

    print(f"Fetching real USDC transfer history to {PAY_TO_ADDRESS} on Base from Etherscan...")
    transfers = fetch_usdc_transfers(etherscan_key)
    incoming = [t for t in transfers if t.get("to", "").lower() == PAY_TO_ADDRESS.lower()]
    print(f"Found {len(incoming)} real incoming USDC transfer(s) on-chain.")

    recent = cf_kv_get(account_id, namespace_id, cf_token, "RECENT_JOBS") or []
    totals = cf_kv_get(account_id, namespace_id, cf_token, "TOTALS") or {
        "jobs": 0, "errors": 0, "revenue_usd": 0, "first_job_ts": None, "last_job_ts": None, "by_offering": {},
    }
    seen_hashes = {j.get("tx_hash") for j in recent if j.get("tx_hash")}
    daily_cache = {}

    added = 0
    for t in incoming:
        tx_hash = t.get("hash")
        if not tx_hash or tx_hash in seen_hashes:
            continue
        decimals = int(t.get("tokenDecimal", "6"))
        amount_usd = round(int(t["value"]) / (10 ** decimals), 6)
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(t["timeStamp"])))
        record = {
            "id": f"{ts_iso}-backfill-{tx_hash[:8]}",
            "ts": ts_iso,
            "offering": offering_for_amount(round(amount_usd, 2)),
            "address": None, "chain_id": CHAIN_ID,
            "symbol": None, "name": None, "verdict": None,
            "status": "settled", "amount_usd": amount_usd, "latency_ms": None,
            "payer": t.get("from"), "tx_hash": tx_hash, "network": "eip155:8453",
            "error": None, "backfilled": True,
        }
        recent.append(record)
        seen_hashes.add(tx_hash)
        added += 1

        totals["jobs"] += 1
        totals["revenue_usd"] = round(totals["revenue_usd"] + amount_usd, 6)
        totals["first_job_ts"] = min(totals["first_job_ts"], ts_iso) if totals["first_job_ts"] else ts_iso
        totals["last_job_ts"] = max(totals["last_job_ts"], ts_iso) if totals["last_job_ts"] else ts_iso
        off = totals["by_offering"].get(record["offering"], {"count": 0, "revenue_usd": 0})
        off["count"] += 1
        off["revenue_usd"] = round(off["revenue_usd"] + amount_usd, 6)
        totals["by_offering"][record["offering"]] = off

        day = ts_iso[:10]
        if day not in daily_cache:
            daily_cache[day] = cf_kv_get(account_id, namespace_id, cf_token, f"STATS_DAILY:{day}") or {"jobs": 0, "revenue_usd": 0}
        daily_cache[day]["jobs"] += 1
        daily_cache[day]["revenue_usd"] = round(daily_cache[day]["revenue_usd"] + amount_usd, 6)

    if not added:
        print("Nothing new to backfill — every real on-chain transfer is already logged (or none exist yet).")
        return 0

    recent.sort(key=lambda j: j["ts"], reverse=True)
    cf_kv_put(account_id, namespace_id, cf_token, "RECENT_JOBS", recent[:200])
    cf_kv_put(account_id, namespace_id, cf_token, "TOTALS", totals)
    for day, bucket in daily_cache.items():
        cf_kv_put(account_id, namespace_id, cf_token, f"STATS_DAILY:{day}", bucket, ttl=60 * 60 * 24 * 100)

    print(f"Backfilled {added} real historical job(s) from on-chain data.")
    print(json.dumps(totals, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
