#!/usr/bin/env python3
"""
CDP Bazaar indexing self-check — a real, read-side monitor for whether
VAPE's offerings actually appear in Coinbase Developer Platform's x402
Bazaar discovery catalog.

Why this exists: CDP's own facilitator never emits the documented
EXTENSION-RESPONSES header that's supposed to tell a resource server
whether its declared bazaar extension was accepted, is still processing,
or was rejected (confirmed via network-level packet capture in
x402-foundation/x402#2112, still open as of 2026-07-14). VAPE's worker
already declares the extension correctly on every offering (see
worker/src/index.ts's declareDiscoveryExtension() calls) and settles real
payments through CDP — but with the one documented diagnostic signal
silently missing, there was no way to actually know whether indexing
happened. worker/src/index.ts's GET /admin/bazaar-status closes that gap
by querying CDP's own discovery catalog directly (filtered by VAPE's
payTo) and diffing it against the real offering list. This script just
calls that endpoint on a schedule and turns a real state CHANGE into a
Memory finding — not every run, since "CDP Bazaar still isn't indexing
us" every single day would be noise, not new information.

An unconfirmed theory (that indexing requires payTo to be a CDP-provisioned
wallet, not VAPE's existing external EOA) was investigated and found to
have no support in the actual x402 protocol spec
(coinbase/x402's docs/extensions/bazaar.mdx) — so this script does not
attempt or recommend any wallet-custody change.
"""
import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "cdp_bazaar_check_state.json")
FINDINGS_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "findings.jsonl")
STATUS_URL = "https://vape-x402.vapex402.workers.dev/admin/bazaar-status"
VALIDATE_URL = "https://vape-x402.vapex402.workers.dev/admin/bazaar-validate"
UA = {"User-Agent": "VAPE-cdp-bazaar-check/1.0", "Accept": "application/json"}


def _fetch_validate():
    """Calls the worker's new /admin/bazaar-validate probe (CDP's own
    POST /v2/x402/validate diagnostic, passed through verbatim) — logged
    raw to CI output only, not persisted as a finding yet, since the exact
    response schema is still unverified as of when this was added. Once a
    real response has been observed, promote the useful fields into a
    proper finding the same way _fetch_status()'s caller does."""
    req = urllib.request.Request(VALIDATE_URL, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"error": f"HTTP {e.code}: {raw[:300]}"}
    except Exception as e:
        return {"error": str(e)}


def _fetch_status():
    """Calls the worker's own /admin/bazaar-status — never talks to CDP
    directly (the worker already holds the CDP JWT auth needed for that;
    duplicating it here would just be a second place to keep in sync).
    Returns the parsed body, or an error dict with the same {error} shape
    the worker itself would return on a real failure. Never raises."""
    req = urllib.request.Request(STATUS_URL, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {"error": f"HTTP {e.code}: {raw[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _append_finding(entry):
    try:
        os.makedirs(os.path.dirname(FINDINGS_PATH), exist_ok=True)
        with open(FINDINGS_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[cdp_bazaar_check] could not append finding: {e}")


def main():
    validate_result = _fetch_validate()
    print(f"[cdp_bazaar_check] /admin/bazaar-validate raw response: {json.dumps(validate_result)}")

    status = _fetch_status()

    if status.get("error") or not status.get("cdp_reachable", True):
        # CDP itself (or our own worker) being unreachable is a different,
        # transient failure mode from "CDP is up but doesn't index us" —
        # never confuse the two by treating this as a real 0-indexed state.
        print(f"[cdp_bazaar_check] could not check status this run: {status.get('error')}")
        return

    indexed_count = status.get("indexed_count", 0)
    total = status.get("total_offerings", 0)
    missing = status.get("missing", [])
    print(f"[cdp_bazaar_check] {indexed_count}/{total} offerings indexed in CDP's Bazaar catalog.")
    if missing:
        print(f"[cdp_bazaar_check] missing: {json.dumps(missing[:5])}{' ...' if len(missing) > 5 else ''}")

    prev = _load_state()
    now_iso = datetime.now(timezone.utc).isoformat()

    if prev is None:
        # First run — establish the baseline. Worth one real finding since
        # it's the first concrete evidence of this repo's own indexing
        # state, not a guess.
        _append_finding({
            "category": "finding",
            "title": f"CDP Bazaar indexing baseline: {indexed_count}/{total} offerings indexed",
            "content": (
                f"agents/cdp_bazaar_check.py's first run against worker/src/index.ts's "
                f"/admin/bazaar-status: {indexed_count} of {total} real VAPE offerings appear in "
                f"CDP's own x402 Bazaar discovery catalog (queried directly, filtered by VAPE's "
                f"payTo — not inferred from the missing EXTENSION-RESPONSES header, which CDP's "
                f"facilitator never emits; see x402-foundation/x402#2112, still open). "
                + (f"Missing: {json.dumps(missing)}." if missing else "All offerings are indexed.")
            ),
            "source": "agents/cdp_bazaar_check.py",
            "tags": ["x402", "bazaar", "cdp", "discovery"],
            "confidence": 0.95,
            "severity": "LOW" if indexed_count == total else "INFO",
            "timestamp": now_iso,
        })
        _save_state({"indexed_count": indexed_count, "total": total, "checked_at": now_iso})
        return

    if indexed_count != prev.get("indexed_count"):
        improved = indexed_count > prev.get("indexed_count", 0)
        _append_finding({
            "category": "finding",
            "title": (
                f"CDP Bazaar indexing changed: {prev.get('indexed_count')} -> {indexed_count} "
                f"of {total} offerings"
            ),
            "content": (
                f"agents/cdp_bazaar_check.py detected a real change in how many VAPE offerings "
                f"CDP's x402 Bazaar catalog reports as indexed, versus the last recorded check "
                f"({prev.get('checked_at')}). "
                + ("Improvement — CDP may have started indexing correctly." if improved
                   else "Regression — a previously-indexed offering disappeared from CDP's catalog.")
                + (f" Missing: {json.dumps(missing)}." if missing else " All offerings are now indexed.")
            ),
            "source": "agents/cdp_bazaar_check.py",
            "tags": ["x402", "bazaar", "cdp", "discovery"],
            "confidence": 0.95,
            "severity": "LOW",
            "timestamp": now_iso,
        })
        _save_state({"indexed_count": indexed_count, "total": total, "checked_at": now_iso})
    else:
        print("[cdp_bazaar_check] no change since last check — not logging a duplicate finding.")


if __name__ == "__main__":
    main()
