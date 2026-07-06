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

Deliberately NOT integrated (real, but need a real decision or access this
script doesn't have — see worker/README.md's "x402 Bazaar discovery" section
for the full writeup):
  - Coinbase's Bazaar / agentic.market — real and already wired in-code
    (worker/src/index.ts's registerExtension(bazaarResourceServerExtension)/
    withBazaar()). Indexing is automatic on the CDP facilitator's side (no
    registration call exists to make) the first time a real payment settles
    on an endpoint — but x402-foundation/x402#2112 (confirmed still OPEN as
    of 2026-07-05: a service with 8 real settlements still isn't indexed) is
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
UA = {"User-Agent": "VAPE-x402-directory-register/1.0", "Content-Type": "application/json"}

# Mirrors worker/src/index.ts::OFFERING_PRICES exactly — this script is a
# discovery announcement, not a second source of pricing truth; if prices
# change there, update here too.
OFFERINGS = {
    "exploit_check": ("0.01", "Contract verification + proxy-swap surface check."),
    "token_safety_check": ("0.02", "Full GoPlus + DexScreener token safety scan with CertiK-style scoring."),
    "liquidity_check": ("0.02", "Liquidity depth + top pair DEX for a Base token."),
    "rug_pull_alert": ("0.03", "Owner-power / rug-risk flags (mint, blacklist, pausable transfers, LP concentration)."),
    "market_intel": ("0.07", "Base TVL, top protocols, prices, and rule-based anomaly flags."),
    "safety_preflight": ("0.10", "VAPE's deepest instant verdict: weighted CertiK-style score, "
                         "meme-factory-template detection, recent-hack correlation, public "
                         "web-reputation search, a live check of declared socials, and a "
                         "frontier-LLM quick source read."),
}


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
    for i, name in enumerate(OFFERINGS):
        if i > 0:
            time.sleep(2)  # pace requests — be a good citizen on someone else's free API
        payload = {
            "url": f"{WORKER_BASE}/scan/{name}",
            "name": f"VAPE {name}",
            "protocol": "x402",
            "provider": PROVIDER,
        }
        code, body = _post("https://402index.io/api/v1/register", payload)
        ok = 200 <= code < 300
        results.append({"offering": name, "status": code, "ok": ok, "response": body})
        print(f"[402index] {name}: HTTP {code} {'OK' if ok else 'FAILED'} — {json.dumps(body)[:200]}")
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
            {"name": name, "route": f"/scan/{name}", "price_usd": price, "description": desc}
            for name, (price, desc) in OFFERINGS.items()
        ],
    }


def build_awesome_x402_entry():
    """A ready-to-paste line for a PR against xpaysh/awesome-x402's services
    list — that repo takes contributions via PR, not an API, and this repo
    has no write access to it, so a human has to actually open that PR."""
    return (
        f"- **[VAPE]({WORKER_BASE})** — autonomous on-chain security detective on Base "
        f"(ERC-8004 #54988). 6 instant x402 offerings ($0.01-$0.15: exploit/token-safety/"
        f"liquidity/rug-pull/preflight/market-intel checks) + a $50 24h-SLA deep-dive audit "
        f"(recon + Slither + frontier-model review). Docs: "
        f"https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md"
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
