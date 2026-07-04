"""
VAPE token scan-and-log — the agent-side twin of the dashboard Hunt console.

Runs the SAME real scan (GoPlus token_security + DexScreener liquidity) as the
browser console, but from Python, and LOGS the verdict into intel/ so agent-run
hunts are persisted and auditable. Keyless, stdlib-only, compute-free (just HTTP).

Usage:
    python -m agents.token_scan <0x_address> [chain_id]
    # chain_id default 8453 (Base); 1=Eth, 42161=Arbitrum
Writes:
    intel/scans/scan-<chain>-<addr8>-<UTC>.md     (human report)
    intel/scans/scans.jsonl                        (append-only machine log)
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "VAPE-PrivateEye/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)"}
SCAN_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "intel", "scans")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url, timeout=15):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"_error": str(e)}


# Hard-reject GoPlus fields — same tier as honeypot, not just an advisory
# flag. All three: real, documented GoPlus token_security fields, flat
# "0"/"1" strings like their siblings (is_mintable, is_proxy, etc.) already
# used above. Kept in its own list so scan.ts/app.js port identically.
HARD_REJECT_FIELDS = ("is_blacklisted", "selfdestruct", "is_airdrop_scam")


def scan(address, chain_id=8453):
    """Return a structured verdict dict from real GoPlus + DexScreener data.

    Same CertiK-style "risk is the default, not the exception" checks added
    to agents/investigate.py's deep-investigation scoring, ported to this
    quick-scan tier wherever they're keyless (GoPlus + DexScreener only) so
    the free Hunt console, the paid x402 offerings, and deep investigations
    never disagree on the checks they share. Contract-verification-based
    checks (e.g. meme-factory-template detection) stay investigate.py-only:
    that needs an optional Etherscan key server-side, which the pure
    browser path (docs/assets/app.js) can't safely hold client-side —
    porting it here would silently diverge the browser from the other two.
    """
    address = address.strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", address):
        return {"error": "invalid_address", "address": address}

    gp_raw = _get(f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}"
                  f"?contract_addresses={address}")
    ds_raw = _get(f"https://api.dexscreener.com/latest/dex/tokens/{address}")

    gp = {}
    if isinstance(gp_raw, dict) and gp_raw.get("result"):
        vals = list(gp_raw["result"].values())
        gp = vals[0] if vals else {}

    pairs = ds_raw.get("pairs") or [] if isinstance(ds_raw, dict) else []
    liquidity_usd = round(sum((p.get("liquidity") or {}).get("usd", 0) for p in pairs), 2)
    # Oldest pair creation timestamp across all pairs — a token's real track
    # record starts at its FIRST pair, not whichever pair happens to be
    # deepest right now.
    pair_created_ms = min((p.get("pairCreatedAt") for p in pairs if p.get("pairCreatedAt")), default=None)
    has_socials = any((p.get("info") or {}).get("socials") or (p.get("info") or {}).get("websites") for p in pairs)

    def f(x):
        try:
            return float(x)
        except Exception:
            return None

    flags = []
    if gp.get("is_honeypot") == "1":
        flags.append("HONEYPOT")
    if (f(gp.get("buy_tax")) or 0) > 0.10:
        flags.append(f"buy_tax {float(gp['buy_tax'])*100:.0f}%")
    if (f(gp.get("sell_tax")) or 0) > 0.10:
        flags.append(f"sell_tax {float(gp['sell_tax'])*100:.0f}%")
    if gp.get("is_mintable") == "1":
        flags.append("mintable")
    owner = gp.get("owner_address") or ""
    if owner and owner != "0x0000000000000000000000000000000000000000":
        flags.append("owner_not_renounced")
    if gp.get("is_proxy") == "1":
        flags.append("proxy")
    if 0 < liquidity_usd < 10000:
        flags.append("low_liquidity")
    if gp.get("cannot_sell_all") == "1":
        flags.append("cannot_sell_all")
    if gp.get("transfer_pausable") == "1":
        flags.append("transfer_pausable")
    for field in HARD_REJECT_FIELDS:
        if gp.get(field) == "1":
            flags.append(field)
    try:
        lp_holders = int(gp.get("lp_holder_count")) if gp.get("lp_holder_count") not in (None, "") else None
    except Exception:
        lp_holders = None
    if lp_holders is not None and lp_holders <= 1:
        flags.append("lp_concentrated")
    try:
        holders = int(gp.get("holder_count")) if gp.get("holder_count") not in (None, "") else None
    except Exception:
        holders = None
    if holders is not None and holders < 50:
        flags.append("low_holder_count")
    if pair_created_ms:
        try:
            if (time.time() * 1000 - float(pair_created_ms)) / 86400000 < 3:
                flags.append("fresh_launch")
        except Exception:
            pass
    if not has_socials:
        flags.append("no_declared_socials")

    hard_reject = gp.get("is_honeypot") == "1" or any(gp.get(field) == "1" for field in HARD_REJECT_FIELDS)
    if hard_reject:
        verdict = "REJECT"
    elif len(flags) >= 2:
        verdict = "CAUTION"
    else:
        verdict = "PROCEED"

    return {
        "ts": _now(),
        "chain_id": chain_id,
        "address": address,
        "name": gp.get("token_name"),
        "symbol": gp.get("token_symbol"),
        "verdict": verdict,
        "flags": flags,
        "holder_count": gp.get("holder_count"),
        "lp_holder_count": gp.get("lp_holder_count"),
        "liquidity_usd": liquidity_usd,
        "pair_created_ms": pair_created_ms,
        "has_declared_socials": has_socials,
        "is_honeypot": gp.get("is_honeypot"),
        "buy_tax": gp.get("buy_tax"),
        "sell_tax": gp.get("sell_tax"),
        "owner_address": owner or None,
        "top_pair_dex": (pairs[0].get("dexId") if pairs else None),
        "source": "goplus+dexscreener",
        "data_error": gp_raw.get("_error") or ds_raw.get("_error"),
    }


def log_scan(result):
    """Persist a scan result to intel/scans/ (md report + jsonl line)."""
    if result.get("error"):
        return None
    os.makedirs(SCAN_DIR, exist_ok=True)
    addr8 = result["address"][:8]
    stamp = result["ts"].replace(":", "").replace("-", "")
    md_path = os.path.join(SCAN_DIR, f"scan-{result['chain_id']}-{addr8}-{stamp}.md")
    title = f"{result.get('name') or 'Unknown'} ({result.get('symbol') or '?'})"
    with open(md_path, "w") as f:
        f.write(f"# VAPE Token Scan — {title}\n\n")
        f.write(f"- **Verdict:** {result['verdict']}\n")
        f.write(f"- **Address:** `{result['address']}` (chain {result['chain_id']})\n")
        f.write(f"- **Scanned:** {result['ts']}\n")
        f.write(f"- **Holders:** {result.get('holder_count')} (LP holders: {result.get('lp_holder_count')})\n")
        f.write(f"- **Liquidity (USD):** {result.get('liquidity_usd')}\n")
        f.write(f"- **Honeypot:** {result.get('is_honeypot')}\n")
        f.write(f"- **Buy/Sell tax:** {result.get('buy_tax')} / {result.get('sell_tax')}\n")
        f.write(f"- **Owner:** {result.get('owner_address')}\n")
        f.write(f"- **Declared socials/website (self-reported, unverified):** {result.get('has_declared_socials')}\n")
        f.write(f"- **Flags:** {', '.join(result['flags']) if result['flags'] else 'none'}\n\n")
        f.write("_Real data: GoPlus token_security + DexScreener. Not investment advice._\n")
    with open(os.path.join(SCAN_DIR, "scans.jsonl"), "a") as f:
        f.write(json.dumps(result) + "\n")
    return md_path


def main():
    if len(sys.argv) < 2:
        print("usage: python -m agents.token_scan <0x_address> [chain_id]")
        sys.exit(2)
    addr = sys.argv[1]
    chain = int(sys.argv[2]) if len(sys.argv) > 2 else 8453
    res = scan(addr, chain)
    if res.get("error"):
        print(json.dumps(res))
        sys.exit(1)
    path = log_scan(res)
    print(json.dumps(res, indent=2))
    if path:
        print(f"\nlogged -> {path}")


if __name__ == "__main__":
    main()
