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

x402 List (https://x402-list.com) has no documented public submission API as
of this writing — only a manual web-form "submit yours" flow. This script
prints a ready-to-paste listing manifest to the job log instead of guessing
at an undocumented endpoint; do not add a fabricated POST call here without
first confirming a real one exists.

Deliberately NOT scheduled: repeated calls to an unfamiliar directory's
/register endpoint with unknown dedup behavior risk creating duplicate
listings. Trigger manually (workflow_dispatch) when the offering list,
prices, or worker URL change — see .github/workflows/x402-directory.yml.
"""
import json
import sys
import urllib.request
import urllib.error

WORKER_BASE = "https://vape.juxtaposition1.deno.net"
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
    "safety_preflight": ("0.05", "Combined token safety + contract verification preflight verdict."),
    "market_intel": ("0.15", "Base TVL, top protocols, prices, and rule-based anomaly flags."),
}


def _post(url, payload, timeout=15):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try:
            body = json.loads(body)
        except Exception:
            body = {"raw": body}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def register_402index():
    results = []
    for name in OFFERINGS:
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


def main():
    print(f"=== VAPE x402 directory registration — worker: {WORKER_BASE} ===\n")
    idx_results = register_402index()

    manifest = build_x402_list_manifest()
    print("\n[x402-list.com] No documented public submission API — submit manually at "
          "https://x402-list.com/ using this listing info:\n")
    print(json.dumps(manifest, indent=2))

    failed = [r for r in idx_results if not r["ok"]]
    if failed and len(failed) == len(idx_results):
        # every single call failed (e.g. host unreachable/blocked) — surface as a real failure
        print(f"\n[402index] all {len(failed)} registrations failed", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
