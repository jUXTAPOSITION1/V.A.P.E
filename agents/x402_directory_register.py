#!/usr/bin/env python3
"""
VAPE x402 discovery-directory registration — one-time (workflow_dispatch)
announcement of VAPE's live x402 offerings to third-party discovery
directories, so other AI agents can find and hire VAPE without already
knowing its URL.

Must run from GitHub Actions, not a local/sandboxed dev session — these are
arbitrary external hosts outside this repo's normal keyless-API footprint
(GoPlus/DexScreener/DefiLlama/CoinGecko), unreachable from this repo's dev
sandbox; CI's unrestricted egress is required for this to actually work.

Registers each of VAPE's 6 auto-fulfilled x402 offerings (docs/ACP_PROTOCOL.md
/ data/reputation.json / worker/src/index.ts::OFFERING_PRICES) with:
  - 402 Index (https://402index.io) — documented, self-service REST API,
    POST /api/v1/register with {url, name, protocol, provider}. Confirmed
    schema at https://402index.io/api-docs.

The following have no documented public submission API as of this writing —
only a manual web-form flow each. This script prints a ready-to-paste listing
manifest to the job log for each instead of guessing at an undocumented
endpoint; do not add a fabricated POST call here without first confirming a
real one exists (see the 2026-07 directory survey below for what's actually
real vs. unverifiable in this fast-moving ecosystem):
  - x402 List (https://x402-list.com) — "submit yours" web form.
  - x402scan (https://www.x402scan.com/resources/register) — a real
    Merit-Systems-built ecosystem explorer; its /resources/register page
    fetches the submitted URL and auto-adds it if it returns a valid x402
    schema, but there's no documented POST API to call directly — same
    manual-submission treatment as x402 List.
  - x402.study — another real, independent x402 directory with a "submit
    yours" flow.
  - awesome-x402 (https://github.com/xpaysh/awesome-x402) — a real, actively
    curated GitHub list; listing requires a PR to a third-party repo, not an
    API call. Prints a ready-to-paste README entry instead.

Also registers every offering with VAPOR (jUXTAPOSITION1/VAPOR) — our own
x402 facilitator's Bazaar-compatible discovery endpoint (`POST
/discovery/register`, see VAPOR's docs/API.md), an explicit alternative to
CDP's undocumented, observably-broken auto-listing (x402-foundation/x402#2112,
still open — see the note below). Unlike the third-party directories above,
this is our own service, so it's safe to re-run on a schedule (a real upsert,
not a one-shot "hope it dedupes" POST).

Deliberately NOT integrated (real, but need a real decision or access this
script doesn't have — see worker/README.md's "x402 Bazaar discovery" section
for the full writeup):
  - Coinbase's Bazaar / agentic.market — real and already wired in-code
    (worker/src/index.ts's registerExtension(bazaarResourceServerExtension)/
    withBazaar()). Indexing is automatic on the CDP facilitator's side (no
    registration call exists to make) the first time a real payment settles
    on an endpoint — but x402-foundation/x402#2112 (confirmed still OPEN as
    of 2026-07-14: a service with 8 real settlements still isn't indexed) is
    a live, unresolved bug in CDP's own facilitator, not something fixable
    from this repo.
  - the402.ai — real marketplace with a real self-service API, but listing
    costs a real $0.01 x402 payment (POST /v1/register), meaning a CI job
    would need a funded, signing-capable wallet — a materially bigger, more
    sensitive lift than a plain POST. Needs an explicit decision before
    building, not a silent addition.
  - 402index.io domain verification (POST /api/v1/claim -> publish the
    returned verification_hash at /.well-known/402index-verify.txt on the
    worker -> POST /api/v1/claim/verify) would upgrade our existing
    "pending review" listings to instantly-approved. Real and documented,
    but the claim's verification_token is an ongoing edit credential that
    needs to be stored as a real secret — this script/session has no way to
    write a new encrypted GitHub Actions secret, so this needs a human step.
  - _x402 DNS TXT record discovery — a real IETF draft
    (draft-jeftovic-x402-dns-discovery-00), but still an early-stage draft
    (not a ratified standard) and requires adding a DNS record in the
    Cloudflare dashboard, which this script/session has no access to.
  - "agent-index.x402.merkleworks.io", mentioned in passing during this
    research — no evidence found that this actually exists; not referenced
    or implemented anywhere.

Deliberately NOT scheduled: repeated calls to an unfamiliar directory's
/register endpoint with unknown dedup behavior risk creating duplicate
listings. Trigger manually (workflow_dispatch) when the offering list,
prices, or worker URL change — see .github/workflows/x402-directory.yml.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

WORKER_BASE = "https://vape-x402.vapex402.workers.dev"
PROVIDER = "VAPE"
# Literally VAPE's favicon (the same file served at docs/index.html's
# <link rel="icon">), not a separate logo asset — reused here so every
# external listing matches the icon a human sees in their own browser tab.
ICON_URL = "https://juxtaposition1.github.io/V.A.P.E/assets/favicon-32.png"
PAY_TO = "0xa1420293a7df49bc8380f543a1fe7b8d6f582879"
# Real, already-verified USDC-on-Base contract (same address used by
# agents/x402_ledger_backfill.py — never re-typed from memory here).
USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
UA = {"User-Agent": "VAPE-x402-directory-register/1.0", "Content-Type": "application/json"}

# VAPOR (jUXTAPOSITION1/VAPOR) — VAPE's own x402 facilitator, settling half
# of VAPE's real x402 traffic in a 50/50 hybrid split with CDP (see
# worker/src/lib/facilitatorClient.ts), and also a Bazaar-compatible
# discovery service in its own right (see its docs/API.md's "Discovery
# (x402 Bazaar)" section).
VAPOR_BASE = "https://x402.duckdns.org"
# Optional: only needed if VAPOR's production deployment has API_KEYS
# configured (see VAPOR's src/config/api-keys.ts) — if VAPOR is running
# with no keys configured at all ("open mode"), registration works with no
# header. Set as a repo secret once VAPOR's operator issues one; until
# then, calls are attempted unauthenticated and a 401 is reported plainly
# rather than silently skipped, since that's a real, actionable signal
# (not merely "feature unavailable").
VAPOR_API_KEY = os.environ.get("VAPOR_API_KEY")

# Mirrors worker/src/index.ts::OFFERING_PRICES exactly — this script is a
# discovery announcement, not a second source of pricing truth; if prices
# change there, update here too.
OFFERINGS = {
    "exploit_check": ("0.01", "Contract verification + proxy-swap surface check."),
    "token_safety_check": ("0.02", "Full GoPlus + DexScreener token safety scan with CertiK-style scoring."),
    "liquidity_check": ("0.02", "Liquidity depth + top pair DEX for a Base token."),
    "rug_pull_alert": ("0.03", "Owner-power / rug-risk flags (mint, blacklist, pausable transfers, LP concentration)."),
    "market_intel": ("0.07", "Base TVL, top protocols, prices, and rule-based anomaly flags."),
    "dossier_check": ("0.10", "VAPE's deepest instant verdict: weighted CertiK-style score, "
                         "meme-factory-template detection, recent-hack correlation, public "
                         "web-reputation search, a live check of declared socials, and a "
                         "frontier-LLM quick source read."),
}

# Market-data micro-services — mirrors worker/src/dataHandlers.ts's
# DL_OFFERINGS exactly. These are served at /data/<name> (not /scan/<name>),
# so they're kept in their own dict and routed accordingly below. All 0.01 USDC.
DATA_OFFERINGS = {
    "token_intel": ("0.01", "Price + confidence, oracle-derived token age, optional "
                       "fees/unlocks/treasury, and the token's real logo."),
    "token_chart": ("0.01", "Daily price series (default 30d) + token logo."),
    "protocol": ("0.01", "Full protocol record: per-chain TVL, category, audits, logo."),
    "protocol_fees": ("0.01", "Protocol real earned fees + revenue (24h/7d/30d)."),
    "unlocks": ("0.01", "Token unlock/emission schedule — next upcoming dump-risk event."),
    "treasury": ("0.01", "Protocol treasury composition + own-token fragility share."),
    "chain_protocols": ("0.01", "Top protocols on a chain by TVL, each with its logo."),
    "chain_overview": ("0.01", "A chain's headline TVL + rank among all chains."),
    "chain_fees": ("0.01", "Fee-earning protocols on a chain, ranked, with logos."),
    "dex_volumes": ("0.01", "DEX trading volume on a chain by venue, with logos."),
    "yields": ("0.01", "Yield pools by chain/project/symbol, TVL-ranked — trap detection."),
    "stablecoins": ("0.01", "Stablecoins by supply with live peg + computed depeg."),
    "bridges": ("0.01", "Bridges ranked by daily volume — bridge-exploit threat data."),
}

# (name, (price, desc), route_prefix) across both tiers — one place that knows
# which offering lives at which route.
def _all_offerings():
    for name, meta in OFFERINGS.items():
        yield name, meta, "scan"
    for name, meta in DATA_OFFERINGS.items():
        yield name, meta, "data"


def _post(url, payload, timeout=15, max_retries=3, backoff_base=10):
    """POST with retry-on-429. GitHub-hosted runners share IP pools across
    countless unrelated CI jobs, so a small public API's per-IP rate limit
    (confirmed hit in practice: 402index.io caps at 50/hour/IP) can trip from
    traffic that has nothing to do with this repo. Honors a real Retry-After
    header when the server sends one; otherwise backs off exponentially,
    capped so one bad/huge Retry-After value can't stall the job for hours."""
    data = json.dumps(payload).encode()
    code, body = 0, {"error": "not attempted"}
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(url, data=data, headers=UA, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.getcode(), json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"raw": raw}
            code = e.code
            if code == 429 and attempt < max_retries:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                try:
                    wait = float(retry_after) if retry_after else backoff_base * (2 ** attempt)
                except Exception:
                    wait = backoff_base * (2 ** attempt)
                wait = min(wait, 120)
                print(f"[402index] 429 rate-limited, retrying in {wait:.0f}s "
                      f"(attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
                continue
            return code, body
        except Exception as e:
            return 0, {"error": str(e)}
    return code, body


def register_402index():
    results = []
    for i, (name, _meta, prefix) in enumerate(_all_offerings()):
        if i > 0:
            time.sleep(2)  # pace requests — be a good citizen on someone else's free API
        payload = {
            "url": f"{WORKER_BASE}/{prefix}/{name}",
            "name": f"VAPE {name}",
            "protocol": "x402",
            "provider": PROVIDER,
        }
        code, body = _post("https://402index.io/api/v1/register", payload)
        ok = 200 <= code < 300
        results.append({"offering": name, "status": code, "ok": ok, "response": body})
        print(f"[402index] {name}: HTTP {code} {'OK' if ok else 'FAILED'} — {json.dumps(body)[:200]}")
    return results


def _to_raw_usdc(price_usd):
    """"0.01" -> "10000" (USDC has 6 decimals) — base-10 integer string, the
    same unit x402's maxAmountRequired/PaymentRequirements always use."""
    return str(round(float(price_usd) * 1_000_000))


def register_vapor():
    """Registers every offering with VAPOR's own Bazaar-compatible discovery
    endpoint (see module docstring). Real upsert on our own service — safe
    to re-run every time this script runs, unlike the third-party
    directories above."""
    headers = dict(UA)
    if VAPOR_API_KEY:
        headers["x-api-key"] = VAPOR_API_KEY

    results = []
    for i, (name, (price, desc), prefix) in enumerate(_all_offerings()):
        if i > 0:
            time.sleep(1)
        resource_url = f"{WORKER_BASE}/{prefix}/{name}"
        payload = {
            "resource": resource_url,
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "eip155:8453",
                "maxAmountRequired": _to_raw_usdc(price),
                "resource": resource_url,
                "payTo": PAY_TO,
                "asset": USDC_BASE,
            }],
            "description": desc,
            "serviceName": PROVIDER,
            "tags": ["security", "base"] if prefix == "scan" else ["market-data", "base"],
            "iconUrl": ICON_URL,
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(f"{VAPOR_BASE}/discovery/register", data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                code, body = r.getcode(), json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raw = e.read().decode(errors="replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"raw": raw}
            code = e.code
        except Exception as e:
            code, body = 0, {"error": str(e)}
        ok = 200 <= code < 300
        results.append({"offering": name, "status": code, "ok": ok})
        print(f"[vapor] {name}: HTTP {code} {'OK' if ok else 'FAILED'} — {json.dumps(body)[:200]}")
    return results


def build_x402_list_manifest():
    return {
        "provider": PROVIDER,
        "icon": ICON_URL,
        "base_url": WORKER_BASE,
        "network": "eip155:8453",
        "pay_to": PAY_TO,
        "docs": "https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md",
        "offerings": [
            {"name": name, "route": f"/{prefix}/{name}", "price_usd": price, "description": desc}
            for name, (price, desc), prefix in _all_offerings()
        ],
    }


def build_awesome_x402_entry():
    """A ready-to-paste line for a PR against xpaysh/awesome-x402's services
    list — that repo takes contributions via PR, not an API, and this repo
    has no write access to it, so a human has to actually open that PR."""
    return (
        f"- **[VAPE]({WORKER_BASE})** — autonomous on-chain security detective on Base "
        f"(ERC-8004 #54988). 6 instant x402 security offerings ($0.01-$0.10: exploit/token-safety/"
        f"liquidity/rug-pull/dossier/market-intel checks) + 13 market-data micro-services "
        f"($0.01 each: token price-oracle intel, TVL/fees/unlocks/treasury, yields, stablecoin "
        f"depeg, bridge volumes) + a $50 24h-SLA deep-dive audit (recon + Slither + frontier-model "
        f"review). Docs: https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md"
    )


def main():
    print(f"=== VAPE x402 directory registration — worker: {WORKER_BASE} ===\n")
    idx_results = register_402index()

    manifest = build_x402_list_manifest()
    for directory_name, url in (
        ("x402-list.com", "https://x402-list.com/"),
        ("x402scan.com", "https://www.x402scan.com/resources/register"),
        ("x402.study", "https://x402.study/"),
    ):
        print(f"\n[{directory_name}] No documented public submission API — submit manually at "
              f"{url} using this listing info:\n")
        print(json.dumps(manifest, indent=2))

    print("\n[awesome-x402] PR-only (github.com/xpaysh/awesome-x402) — this repo has no write "
          "access there, so open the PR by hand with this entry:\n")
    print(build_awesome_x402_entry())

    print(f"\n=== Registering with VAPOR's discovery endpoint — {VAPOR_BASE} ===\n")
    vapor_results = register_vapor()
    vapor_failed = [r for r in vapor_results if not r["ok"]]
    if vapor_failed and all(r["status"] == 401 for r in vapor_failed):
        print("\n[vapor] all registrations rejected with HTTP 401 — VAPOR's production deployment "
              "has API_KEYS configured and this run has no VAPOR_API_KEY secret set. Ask VAPOR's "
              "operator for a key (scoped to VAPE's own payTo is fine) and set it as this repo's "
              "VAPOR_API_KEY secret; this is not treated as a build failure since it's a known, "
              "actionable configuration gap rather than a code bug.", file=sys.stderr)
    elif vapor_failed:
        print(f"\n[vapor] {len(vapor_failed)}/{len(vapor_results)} registrations failed for a reason "
              "other than a missing API key — see the per-offering lines above.", file=sys.stderr)

    failed = [r for r in idx_results if not r["ok"]]
    if failed and len(failed) == len(idx_results):
        # every single call failed (e.g. host unreachable/blocked, or the
        # per-IP rate limit was already exhausted by unrelated traffic on
        # this shared GitHub-runner IP before the retries in _post() even
        # had a chance) — surface as a real failure, but with an actionable
        # message instead of a bare exit code.
        still_429 = all(r["status"] == 429 for r in failed)
        if still_429:
            print(f"\n[402index] all {len(failed)} registrations still rate-limited (HTTP 429) "
                  "after in-run retries — this GitHub-runner IP's hourly cap was likely already "
                  "used up by unrelated traffic. Re-run this workflow later (the hourly window "
                  "resets on its own); no code fix will make a shared-IP limit clear faster.",
                  file=sys.stderr)
        else:
            print(f"\n[402index] all {len(failed)} registrations failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
