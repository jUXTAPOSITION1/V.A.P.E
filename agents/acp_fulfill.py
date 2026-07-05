"""
VAPE ACP fulfillment bridge — turn a funded ACP job into a real deliverable.

This is the connective tissue between the ACP job monitor and VAPE's verified tools.
Given an offering name + requirement (the job's input), it runs the RIGHT real-data
tool and returns a structured deliverable string ready for `acp provider submit`.

Real data only. Keyless where possible. stdlib + existing agent modules — zero new deps.

The ACP monitor's reasoning handler calls fulfill() once a job is funded; it does NOT
sign or submit here (that stays in the ACP CLI path). This module only produces the
deliverable payload, so it's safe to run/test without touching the wallet.
"""
import json
import os
import sys

try:
    from agents.token_scan import scan as token_scan
    from agents.data_fetchers import build_market_context, get_contract_source
except Exception:  # when invoked from inside agents/
    from token_scan import scan as token_scan
    from data_fetchers import build_market_context, get_contract_source


def _addr(req):
    """Pull a contract address out of a requirement dict/string."""
    if isinstance(req, dict):
        for k in ("address", "contract", "token", "target"):
            if req.get(k):
                return str(req[k]).strip()
    if isinstance(req, str):
        import re
        m = re.search(r"0x[a-fA-F0-9]{40}", req)
        if m:
            return m.group(0)
    return None


def _chain(req, default=8453):
    if isinstance(req, dict):
        for k in ("chain_id", "chainId", "chain"):
            if req.get(k):
                try:
                    return int(req[k])
                except Exception:
                    pass
    return default


# offering name -> handler(requirement) -> deliverable dict
def _token_safety(req):
    a = _addr(req)
    if not a:
        return {"error": "no address in requirement"}
    return token_scan(a, _chain(req))


def _liquidity(req):
    a = _addr(req)
    r = token_scan(a, _chain(req)) if a else {"error": "no address"}
    if "error" in r:
        return r
    return {"address": a, "liquidity_usd": r.get("liquidity_usd"),
            "top_pair_dex": r.get("top_pair_dex"), "verdict": r.get("verdict")}


def _rug_pull(req):
    a = _addr(req)
    r = token_scan(a, _chain(req)) if a else {"error": "no address"}
    if "error" in r:
        return r
    rug = [f for f in r.get("flags", []) if f in
           ("HONEYPOT", "mintable", "owner_not_renounced", "cannot_sell_all", "transfer_pausable",
            "is_blacklisted", "selfdestruct", "is_airdrop_scam", "lp_concentrated")]
    return {"address": a, "rug_risk": "HIGH" if (r.get("is_honeypot") == "1" or len(rug) >= 2) else "LOW",
            "owner_powers": rug, "verdict": r.get("verdict")}


def _exploit_check(req):
    a = _addr(req)
    if not a:
        return {"error": "no address"}
    src = get_contract_source(a, _chain(req))
    # src's "no_key"/error state (e.g. ETHERSCAN_API_KEY not configured) must
    # be surfaced, not swallowed — silently falling through to all-None
    # fields looks like "we checked, it's not verified" when the truth is
    # "we never checked", which a paying customer has no way to tell apart.
    if isinstance(src, dict) and src.get("error"):
        return {"address": a, "error": src["error"], "note": src.get("note", "contract verification unavailable")}
    return {"address": a, "verified": src.get("verified") if isinstance(src, dict) else None,
            "contract_name": src.get("contract_name") if isinstance(src, dict) else None,
            "proxy": src.get("proxy") if isinstance(src, dict) else None,
            "note": "verification + proxy surface; deep audit = deep_contract_audit offering"}


def _market_intel(req):
    # Was base_tvl/top_protocols/prices/anomaly_flags only — thin for a paid
    # snapshot when build_market_context() already fetches fear_greed and
    # global_market for the free site's own "Wire" section. Surfacing the
    # same real, already-fetched fields here instead of a second API call.
    # anomaly_flags is dropped rather than kept ACP-only: it needs the full
    # multi-vertical fetch (hacks/movers/chain-activity), which is real
    # parity work worker/src/lib/marketIntel.ts can't cheaply match for a
    # single lean paid call — better to keep both fulfillment paths
    # identical in scope than let the ACP buyer see a field the x402 buyer
    # never gets for the same offering.
    ctx = build_market_context()
    fng = ctx.get("fear_greed") or {}
    glob_m = ctx.get("global_market") or {}
    return {"base_tvl": ctx.get("base_tvl", {}).get("tvl_usd"),
            "base_tvl_24h_change_pct": ctx.get("base_tvl", {}).get("tvl_24h_change_pct"),
            "top_protocols": [p["name"] for p in ctx.get("base_tvl", {}).get("top_protocols", [])[:5]],
            "prices": ctx.get("prices"),
            "fear_greed": fng.get("value"),
            "fear_greed_classification": fng.get("classification"),
            "global_market_cap_usd": glob_m.get("total_mcap_usd"),
            "global_market_cap_change_24h_pct": glob_m.get("mcap_change_24h_pct")}


def _safety_preflight(req):
    a = _addr(req)
    if not a:
        return {"error": "no address"}
    ts = token_scan(a, _chain(req))
    if "error" in ts:
        return ts
    src = get_contract_source(a, _chain(req))
    result = {"address": a, "token_verdict": ts.get("verdict"), "flags": ts.get("flags"),
              "verified": src.get("verified") if isinstance(src, dict) else None,
              "combined": "PROCEED" if ts.get("verdict") == "PROCEED" and (src.get("verified") if isinstance(src, dict) else False) else "REVIEW"}
    # Same reasoning as _exploit_check: don't let a missing/failed
    # verification silently collapse into "verified: None" with no context.
    if isinstance(src, dict) and src.get("error"):
        result["verification_note"] = src.get("note", src["error"])
    return result


def _community_broadcast(req):
    """Return VAPE's latest real community intel broadcast (agents/broadcast.py,
    scheduled every 6h) — the offering was priced/listed since day one but had
    no auto-handler because nothing generated fresh broadcasts to serve."""
    import glob
    files = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "intel", "broadcasts", "broadcast-*.md")), reverse=True)
    if not files:
        return {"error": "no broadcast generated yet"}
    with open(files[0]) as f:
        content = f.read()
    return {"file": os.path.basename(files[0]), "content": content}


HANDLERS = {
    "token_safety_check": _token_safety,
    "liquidity_check": _liquidity,
    "rug_pull_alert": _rug_pull,
    "exploit_check": _exploit_check,
    "market_intel": _market_intel,
    "safety_preflight": _safety_preflight,
    "community_intel_broadcast": _community_broadcast,
    # deep_contract_audit / forensics_deep / wallet_recon route to the SKILLFORGE
    # tool tier (slither/aderyn/mythril, wallet_trace) via the monitor's handler;
    # they need the runner/keys, so are intentionally not auto-run here.
}


def fulfill(offering_name, requirement=None):
    """Return a deliverable dict for a funded job. Real data only."""
    h = HANDLERS.get(offering_name)
    if not h:
        return {"offering": offering_name,
                "status": "manual",
                "note": "no auto-handler; route to SKILLFORGE tool tier via monitor handler"}
    try:
        result = h(requirement or {})
        return {"offering": offering_name, "status": "ok", "deliverable": result,
                "source": "vape-real-data", "disclaimer": "Real on-chain data. Not investment advice."}
    except Exception as e:
        return {"offering": offering_name, "status": "error", "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("usage: python -m agents.acp_fulfill <offering_name> [json_requirement]")
        print("offerings:", ", ".join(HANDLERS))
        sys.exit(2)
    offering = sys.argv[1]
    req = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    print(json.dumps(fulfill(offering, req), indent=2))


if __name__ == "__main__":
    main()
