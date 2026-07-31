"""One-off diagnostic (2026-07-27): a 402index.io registration backfill
reported 11 of the 15 DL_OFFERINGS routes failing with "endpoint returned
HTTP 503 instead of 402" while probed unauthenticated (see
agents/x402_directory_register.py's run log). This confirms, from a real
GitHub Actions runner (not the dev sandbox, whose egress proxy blocks the
worker's own domain), what an unauthenticated GET to each /data/<name> route
actually returns right now, and prints the raw body so the real cause (worker
bug vs. a transient DefiLlama/Cloudflare blip at registration time) is
visible directly rather than inferred from code reading.
"""
import urllib.error
import urllib.request

WORKER_BASE = "https://vape-x402.vapex402.workers.dev"

# The 11 that failed + 2 that succeeded (token_intel, prediction_market_odds)
# as a control -- if the control also 503s now, this is worker-wide, not
# specific to these 11.
ROUTES = [
    "protocol?slug=aerodrome",
    "protocol_fees?slug=aave",
    "unlocks?slug=aptos",
    "treasury?slug=uniswap",
    "chain_protocols",
    "chain_overview",
    "chain_fees",
    "dex_volumes",
    "yields",
    "stablecoins",
    "bridges",
    "token_intel?address=0x0000000000000000000000000000000000000000",
    "prediction_market_odds",
]

UA = {"User-Agent": "VAPE-diag/1.0", "Accept": "application/json"}


def probe(path):
    url = f"{WORKER_BASE}/data/{path}"
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.getcode(), r.read().decode(errors="replace")[:500]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500]
    except Exception as e:
        return 0, str(e)


def main():
    for path in ROUTES:
        code, body = probe(path)
        print(f"\n=== /data/{path} -> HTTP {code} ===")
        print(body)


if __name__ == "__main__":
    main()
