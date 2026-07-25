#!/usr/bin/env python3
"""
402 Index domain-ownership claim/verify — upgrades VAPE's existing
402index.io listings (agents/x402_directory_register.py) from "pending
review" to instantly-approved by proving ownership of the worker's domain.

Real, documented flow (https://402index.io/api-docs, "Claim Your Listings"):
  1. claim:  POST /api/v1/claim {domain} -> {verification_token, verification_hash, ...}
  2. deploy: publish verification_hash at https://<domain>/.well-known/402index-verify.txt
             (worker/src/index.ts's WELLKNOWN_402INDEX_HASH constant — a separate,
             manual step between running this script's `claim` and `verify` actions)
  3. verify: POST /api/v1/claim/verify {domain} -> {status: "verified", services_count}

Confirmed 2026-07-25 (job log of the 2026-07-15 workflow_dispatch run): re-running
`verify` after the domain is already verified correctly returns HTTP 409 "Domain
already verified" — the earlier 2026-07-05 `claim`+`verify` run had already
succeeded, so that 409 is confirmation of success, not a real failure (the
workflow's own exit-1 handling doesn't know the difference; read the job log body,
not just the exit code, when checking domain-verification status).

A 4th action, `status --url <service-detail-url>`, is a read-only GET of a real
402index.io service-detail page (e.g. https://402index.io/service/<uuid>) — no
guessed/undocumented list-all-services endpoint is called, since 402index.io's
api-docs don't document one; this just fetches the exact URL given and prints the
raw page for a human to read the listed name/URL/health state from.

Must run from GitHub Actions (workflow_dispatch, one action per run) — 402index.io
is unreachable from this repo's dev sandbox, same reason as x402_directory_register.py.

Security note on verification_token: it's real, ongoing credential (lets its holder
PATCH/DELETE VAPE's 402index.io listings — see the "edit"/"delete"/"revoke" endpoints
in the API docs). This script prints it to the job log because this repo has no
mechanism to write a new encrypted GitHub Actions secret from a workflow run; the
`claim` action's log line is the operator's ONE chance to copy it somewhere private.
If it's ever suspected leaked, `revoke` immediately invalidates it and a fresh
`claim` issues a new one — the API is explicitly designed around that recovery path,
which is why this script accepts printing it to a log rather than building bigger,
more sensitive infrastructure (e.g. a secrets-write-scoped PAT) just to avoid it.
"""
import argparse
import json
import sys
import urllib.request
import urllib.error

DOMAIN = "vape-x402.vapex402.workers.dev"
API_BASE = "https://402index.io/api/v1"
UA = {"User-Agent": "VAPE-x402index-claim/1.0", "Content-Type": "application/json"}
GET_UA = {"User-Agent": "VAPE-x402index-claim/1.0"}


def _call(method, path, payload, timeout=15):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{API_BASE}{path}", data=data, headers=UA, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}


def claim():
    code, body = _call("POST", "/claim", {"domain": DOMAIN})
    if code != 200 and code != 201:
        print(f"[claim] FAILED — HTTP {code}: {json.dumps(body)}", file=sys.stderr)
        sys.exit(1)
    token = body.get("verification_token")
    hash_ = body.get("verification_hash")
    if not token or not hash_:
        print(f"[claim] unexpected response shape — HTTP {code}: {json.dumps(body)}", file=sys.stderr)
        sys.exit(1)
    print(f"[claim] domain={DOMAIN}")
    print(f"[claim] verification_hash (safe to publish, this IS the well-known file's content): {hash_}")
    print(f"[claim] verification_url: {body.get('verification_url')}")
    print(f"[claim] verification_token (SENSITIVE — copy this now, it will not be shown again "
          f"by this script): {token}")
    print("\n[claim] NEXT STEPS: (1) add WELLKNOWN_402INDEX_HASH = \"" + hash_ + "\" to "
          "worker/src/index.ts's well-known route, deploy, confirm it's live, THEN "
          "(2) re-run this workflow with action=verify. Claim expires in 72h if not verified.")


def verify():
    code, body = _call("POST", "/claim/verify", {"domain": DOMAIN})
    ok = code == 200 and body.get("status") == "verified"
    print(f"[verify] HTTP {code}: {json.dumps(body)}")
    if not ok:
        print("[verify] FAILED — check that /.well-known/402index-verify.txt is live on the "
              "worker, serves ONLY the hash with no redirect, and is under 1KB.", file=sys.stderr)
        sys.exit(1)
    print(f"[verify] domain verified — {body.get('services_count', '?')} listing(s) now editable.")


def status(service_url):
    """Read-only GET of a real 402index.io service-detail page (the exact
    URL passed in — never guessed, since 402index.io has no documented
    'list my services' API to query instead; see module docstring for the
    documented endpoints this script otherwise uses). Prints the raw HTML
    to the job log for a human to read the listed name/URL/health state
    from, rather than attempting to parse an undocumented page structure
    that could silently break on any 402index.io redesign."""
    req = urllib.request.Request(service_url, headers=GET_UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            code, headers, body = r.getcode(), dict(r.headers), r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        code, headers, body = e.code, dict(e.headers or {}), e.read().decode(errors="replace")
    except Exception as e:
        print(f"[status] FAILED to fetch {service_url}: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"[status] GET {service_url} -> HTTP {code}")
    # x402 v2 (@x402/core 2.19.0, what this repo's worker runs) puts the real
    # payment challenge in the PAYMENT-REQUIRED response header, not the JSON
    # body — confirmed by reading worker/node_modules/@x402/core's own
    # createHTTPResponse(): body is `unpaidResponse ? unpaidResponse.body : {}`
    # unless a route defines unpaidResponseBody, so an empty `{}` body on a
    # real 402 is expected, not broken. Print headers so this is visible.
    print(f"[status] headers: {json.dumps(headers)}")
    print(body)
    if code >= 400:
        sys.exit(1)


def revoke(token):
    code, body = _call("POST", "/claim/revoke", {"domain": DOMAIN, "verification_token": token})
    print(f"[revoke] HTTP {code}: {json.dumps(body)}")
    if code != 200:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=["claim", "verify", "revoke", "status"])
    ap.add_argument("--token", help="verification_token, required for the revoke action")
    ap.add_argument("--url", help="service-detail URL to fetch, required for the status action "
                     "(e.g. https://402index.io/service/<uuid>)")
    args = ap.parse_args()
    if args.action == "claim":
        claim()
    elif args.action == "verify":
        verify()
    elif args.action == "revoke":
        if not args.token:
            print("revoke requires --token", file=sys.stderr)
            sys.exit(1)
        revoke(args.token)
    elif args.action == "status":
        if not args.url:
            print("status requires --url", file=sys.stderr)
            sys.exit(1)
        status(args.url)


if __name__ == "__main__":
    main()
