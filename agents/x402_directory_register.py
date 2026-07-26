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

Registers each of VAPE's synchronous x402 "scan" offerings
(docs/ACP_PROTOCOL.md / data/reputation.json / worker/src/index.ts::
OFFERING_PRICES + the standalone tx_decode/community_intel_broadcast/
bulk_safety_bundle routes), the two $1 async audit offerings
(bounty_deep_dive and its deep_contract_audit alias — same file's
BOUNTY_DEEP_DIVE_PRICE/DEEP_CONTRACT_AUDIT_PRICE), and the "data"
micro-services (worker/src/dataHandlers.ts::DL_OFFERINGS) with:
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

Deliberately NOT scheduled: trigger manually (workflow_dispatch) when the
offering list, prices, or worker URL change — see
.github/workflows/x402-directory.yml.

State-file skip (2026-07-25, revised): the 2026-07-05 run registered 22
offerings with 402index.io; 5 more (tx_decode, community_intel_broadcast,
bulk_safety_bundle, deep_contract_audit, website_review) were added to the
worker on 2026-07-20 but never registered anywhere, since this script was
never re-run in between. STATE_PATH records which offering names have
already been successfully registered with 402index.io; register_402index()
skips those on every future run unless --force-all is passed — this is now
confirmed (per the real POST /api/v1/register docs: "Re-registering an
existing URL+protocol updates the record") to be a pacing/no-op-avoidance
default, not a duplication-risk workaround, so --force-all is a real,
safe way to push a metadata-only change (e.g. a price or description edit)
to already-listed offerings. VAPOR's own /discovery/register is a real
upsert (per its own docs), so register_vapor() is intentionally NOT
filtered by this state — it always sends the full current list.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "x402_directory_state.json")

WORKER_BASE = "https://vape-x402.vapex402.workers.dev"
PROVIDER = "VAPE"
# Literally VAPE's favicon (the same file served at docs/index.html's
# <link rel="icon">), not a separate logo asset — reused here so every
# external listing matches the icon a human sees in their own browser tab.
ICON_URL = "https://juxtaposition1.github.io/V.A.P.E/assets/favicon-32.png"
PAY_TO = "0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15"
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
    "token_safety_check": ("0.02", "Full token safety + liquidity scan with a weighted 0-100 risk score."),
    "liquidity_check": ("0.02", "Liquidity depth + top pair DEX for a Base token."),
    "rug_pull_alert": ("0.03", "Owner-power / rug-risk flags (mint, blacklist, pausable transfers, LP concentration)."),
    "market_intel": ("0.07", "Base TVL trend, per-protocol share/category breakdown, concentration "
                         "risk, DEX volume, top gainers/losers, prices, sentiment, and a narrative summary."),
    "dossier_check": ("0.10", "VAPE's deepest instant verdict: weighted 0-100 risk score, "
                         "meme-factory-template detection, recent-hack correlation, public "
                         "web-reputation search, a live check of declared socials, and a "
                         "frontier-LLM quick source read."),
    "tx_decode": ("0.05", "Plain-language transaction decode + risk flags for any Base/EVM tx "
                         "hash — real on-chain tx/receipt/logs plus signature lookup."),
    "community_intel_broadcast": ("0.10", "VAPE's latest 6-hourly consolidated security + market "
                         "intel broadcast — real committed output, not generated per-request."),
    "bulk_safety_bundle": ("0.50", "token_safety_check batched over 5-25 tokens in one job, "
                         "flat-priced."),
    "website_review": ("0.15", "Phishing/scam-page red-flag read of a website URL — real scrape "
                         "+ frontier-LLM read for fake contract addresses, wallet-drainer patterns, "
                         "brand mismatch, and copy-paste scam-site boilerplate. Not a smart-contract "
                         "audit (see bounty_deep_dive for that)."),
}

# Market-data micro-services — mirrors worker/src/dataHandlers.ts's
# DL_OFFERINGS exactly. These are served at /data/<name> (not /scan/<name>),
# so they're kept in their own dict and routed accordingly below. Mostly
# 0.01 USDC (the keyless DefiLlama tools, plus prediction_market_odds which
# is also keyless via Polymarket/Kalshi); wallet_pnl_deepdive is priced
# separately since it's a richer, Alchemy + CoinGecko-backed deliverable
# (Base mainnet only — rebuilt off Codex after its wallet-analytics fields
# turned out to be paid-plan-gated).
DATA_OFFERINGS = {
    "wallet_pnl_deepdive": ("0.25", "Real Base-mainnet wallet balances + an "
                       "unrealized-P&L estimate per holding (current value vs. first-"
                       "acquisition price)."),
    "prediction_market_odds": ("0.01", "Live crypto/Base-relevant prediction-market odds from "
                       "Polymarket and Kalshi, ranked by volume."),
    "token_intel": ("0.01", "Price + confidence, oracle-derived token age, optional "
                       "fees/unlocks/treasury, and the token's real logo."),
    "token_chart": ("0.01", "Daily price series (default 30d) + token logo."),
    "protocol": ("0.01", "Full protocol record: per-chain TVL, category, audits, logo."),
    "protocol_fees": ("0.01", "Protocol real earned fees + revenue (24h/7d/30d/1y/all-time)."),
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

# bounty_deep_dive — real, x402-gated at /scan/bounty_deep_dive (see
# worker/src/index.ts's BOUNTY_DEEP_DIVE_PRICE / BOUNTY_DEEP_DIVE_DISCOVERY),
# but was never actually included in any external directory registration
# below despite this script's own module docstring listing it as a live
# offering — a real, silent discovery gap: other agents scanning 402index/
# VAPOR for VAPE's services could never find it, unlike every other real
# x402 route this repo serves. Kept in its own dict (not folded into
# OFFERINGS) since its fulfillment shape is async (GitHub Actions dispatch),
# not a same-request deterministic script — still genuinely x402-payable
# at the same /scan/ route prefix, so it belongs in every registration pass.
BOUNTY_OFFERINGS = {
    "bounty_deep_dive": ("1.00", "Submission-ready bug-bounty PoC: real recon + Slither/Halmos/"
                       "Mythril/Aderyn (when available) + a frontier-LLM source review, for a "
                       "Base/EVM contract address or an external bounty program's own GitHub repo."),
    # Address-only alias of the exact same pipeline above (see
    # worker/src/index.ts's DEEP_CONTRACT_AUDIT_PRICE/dispatchAddressAuditJob)
    # — its own x402 listing/name since that's how ACP already knows it.
    "deep_contract_audit": ("1.00", "slither+aderyn+mythril severity-rated audit + 0-100 score "
                       "for a Base/EVM contract address — the same real-tool pipeline as "
                       "bounty_deep_dive, address-only."),
}

# (name, (price, desc), route_prefix) across all tiers — one place that knows
# which offering lives at which route.
def _all_offerings():
    for name, meta in OFFERINGS.items():
        yield name, meta, "scan"
    for name, meta in BOUNTY_OFFERINGS.items():
        yield name, meta, "scan"
    for name, meta in DATA_OFFERINGS.items():
        yield name, meta, "data"


# Substrings of the response headers worth logging on a 429. Matched
# case-insensitively against the header name, so this covers the common
# spellings (RateLimit-Reset, X-RateLimit-Remaining, Retry-After, ...)
# without needing to know which convention 402index.io happens to use.
_RATELIMIT_HEADER_HINTS = ("ratelimit", "rate-limit", "retry-after", "reset")


def _ratelimit_headers(headers):
    """Subset of `headers` that describes the rate-limit state, for logging."""
    if not headers:
        return {}
    return {k: v for k, v in dict(headers).items()
            if any(hint in k.lower() for hint in _RATELIMIT_HEADER_HINTS)}


def _post(url, payload, timeout=15, max_retries=1, backoff_base=10):
    """POST with retry-on-429. GitHub-hosted runners share IP pools across
    countless unrelated CI jobs, so a small public API's per-IP rate limit
    can trip from traffic that has nothing to do with this repo. Honors a
    real Retry-After header when the server sends one; otherwise backs off
    exponentially, capped so one bad/huge Retry-After value can't stall the
    job for hours.

    max_retries defaults to 1, not 3: the api-docs' page text claims "10
    registrations per hour per IP" for POST /api/v1/register, but the
    server's own 429 body is the real ground truth and says otherwise —
    confirmed live (2026-07-25): {"error": "Too many registrations. Limit:
    50 per hour per IP."}. Either way it's a hard hourly quota, not a short
    transient throttle (that's a separate, much looser 100 req/min free-tier
    limit on the read endpoints). Once that quota is hit, no backoff shorter
    than the remaining window (up to ~60 minutes) can ever succeed, so
    burning 3 retries x up to 120s each per offering (confirmed in practice:
    this is exactly what made a 27-offering force-all run grind through only
    2 successes in 25+ minutes) just wastes CI time for a guaranteed-failed
    call. One quick retry still covers a genuinely transient blip;
    register_402index() below stops
    attempting further offerings entirely once it sees a real 429, since at
    that point every remaining call in this run is going to fail too."""
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
            if code == 429:
                # The only authoritative answer to *when* the quota rolls over.
                # 402index.io's api-docs page and its own 429 body already
                # disagree about the limit itself (10 vs 50 per hour per IP),
                # and neither states when the window resets — so without these
                # headers, "re-run later" is guesswork. Logging them turns the
                # backfill into something schedulable.
                rl = _ratelimit_headers(e.headers)
                print(f"[402index] 429 rate-limit headers: "
                      f"{json.dumps(rl) if rl else '(server sent none)'}")
                if attempt < max_retries:
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


def _load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {"registered_402index": []}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def _category_for(name):
    """402index.io's `category` field is a plain prefix-matched string (its
    own docs example: "bitcoin", "ai/text") — there's no fixed taxonomy to
    conform to, just pick something a filter/search would reasonably match."""
    if name in BOUNTY_OFFERINGS:
        return "crypto/security/audit"
    if name in DATA_OFFERINGS:
        return "crypto/market-data"
    return "crypto/security"


def register_402index(only=None, force_all=False):
    """Registers each offering with 402index.io — but SKIPS any offering
    already recorded in STATE_PATH as previously registered, unless
    force_all is set. `only`, if given, further restricts this run to that
    explicit set of offering names (e.g. just the newly-added ones)
    regardless of state.

    Confirmed via the real api-docs POST /api/v1/register section (2026-07-25,
    read past the truncation that hid it on the first fetch): "Re-registering
    an existing URL+protocol updates the record" — so re-sending an
    already-listed offering is a real, documented upsert, not a duplication
    risk. The state-file skip is kept anyway as a pacing/no-op-avoidance
    default (no reason to re-POST 27 unchanged listings every run), but
    --force-all is now a safe, real "refresh metadata" mechanism, not just a
    theoretical escape hatch.

    Real gap this closes: the payload previously sent only {url, name,
    protocol, provider} — none of the documented price_usd/description/
    category/payment_asset/payment_network fields — which is exactly why
    every VAPE listing shows a blank "—" price on 402index.io's own directory
    page instead of its real x402 price."""
    state = _load_state()
    already = set(state.get("registered_402index", []))
    results = []
    newly_registered = []
    for name, (price, desc), prefix in _all_offerings():
        if only is not None and name not in only:
            continue
        if not force_all and name in already:
            print(f"[402index] {name}: skipped — already registered on a previous run "
                  f"(pass --force-all to re-send anyway)")
            continue
        if results:
            time.sleep(2)  # pace requests — be a good citizen on someone else's free API
        payload = {
            "url": f"{WORKER_BASE}/{prefix}/{name}",
            "name": f"VAPE {name}",
            "protocol": "x402",
            "provider": PROVIDER,
            "description": desc,
            "price_usd": float(price),
            "payment_asset": "USDC",
            "payment_network": "Base",
            "category": _category_for(name),
        }
        code, body = _post("https://402index.io/api/v1/register", payload)
        ok = 200 <= code < 300
        results.append({"offering": name, "status": code, "ok": ok, "response": body})
        print(f"[402index] {name}: HTTP {code} {'OK' if ok else 'FAILED'} — {json.dumps(body)[:200]}")
        if ok:
            newly_registered.append(name)
        elif code == 429:
            # Real hourly quota, confirmed exhausted for this run's IP — every
            # remaining offering would also 429 (the retry inside _post()
            # already tried once and failed), so stop here instead of
            # grinding through the rest one-by-one for no benefit. Re-run
            # later (the quota resets ~60min after its first counted request)
            # to pick up where this left off.
            attempted = {r["offering"] for r in results}
            remaining = [n for n, _meta, _prefix in _all_offerings()
                         if (only is None or n in only) and n not in attempted]
            print(f"[402index] 429 — hourly per-IP registration quota exhausted after "
                  f"{len(newly_registered)} success(es) this run. Stopping early rather "
                  f"than retrying the remaining {len(remaining)} offering(s) into a "
                  f"guaranteed failure: {remaining}. Re-dispatch (same --force-all/--only "
                  f"flags) once the quota window resets to pick up the rest.")
            break

    if newly_registered:
        state["registered_402index"] = sorted(already | set(newly_registered))
        _save_state(state)
        print(f"[402index] recorded {len(newly_registered)} newly-registered offering(s) in "
              f"{os.path.relpath(STATE_PATH, _REPO_ROOT)}: {newly_registered}")
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
        f"(ERC-8004 #59900). {len(OFFERINGS)} instant x402 offerings ($0.01-$0.50: exploit/"
        f"token-safety/liquidity/rug-pull/dossier/tx-decode/community-intel/bulk-safety/"
        f"website-review checks) + {len(DATA_OFFERINGS)} market-data micro-services ($0.01-$0.25 "
        f"each: token price-oracle intel, wallet P&L, TVL/fees/unlocks/treasury, yields, stablecoin "
        f"depeg, bridge volumes, prediction-market odds) + a $1 deep-dive bounty audit / address-only "
        f"deep_contract_audit alias (recon + Slither/Halmos/Mythril/Aderyn + frontier-model review — "
        f"a submission-ready PoC and full technical detail). Docs: "
        f"https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md"
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="Comma-separated offering names to register with 402index.io "
                     "this run (e.g. newly-added offerings only). Omit to register every offering "
                     "not already recorded as registered in the state file.")
    ap.add_argument("--force-all", action="store_true", help="Re-send every offering to 402index.io "
                     "even if already recorded as registered — use only if you know the directory "
                     "dedupes by URL, or intend an explicit re-listing.")
    args = ap.parse_args()
    only = set(n.strip() for n in args.only.split(",") if n.strip()) if args.only else None

    print(f"=== VAPE x402 directory registration — worker: {WORKER_BASE} ===\n")
    idx_results = register_402index(only=only, force_all=args.force_all)

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
