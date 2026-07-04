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
    return {"address": a, "verified": src.get("verified") if isinstance(src, dict) else None,
            "contract_name": src.get("contract_name") if isinstance(src, dict) else None,
            "proxy": src.get("proxy") if isinstance(src, dict) else None,
            "note": "verification + proxy surface; deep audit = deep_contract_audit offering"}


def _market_intel(req):
    ctx = build_market_context()
    return {"base_tvl": ctx.get("base_tvl", {}).get("tvl_usd"),
            "top_protocols": [p["name"] for p in ctx.get("base_tvl", {}).get("top_protocols", [])[:5]],
            "prices": ctx.get("prices"), "anomaly_flags": ctx.get("anomaly_flags")}


def _safety_preflight(req):
    a = _addr(req)
    if not a:
        return {"error": "no address"}
    ts = token_scan(a, _chain(req))
    src = get_contract_source(a, _chain(req))
    return {"address": a, "token_verdict": ts.get("verdict"), "flags": ts.get("flags"),
            "verified": src.get("verified") if isinstance(src, dict) else None,
            "combined": "PROCEED" if ts.get("verdict") == "PROCEED" and (src.get("verified") if isinstance(src, dict) else False) else "REVIEW"}


HANDLERS = {
    "token_safety_check": _token_safety,
    "liquidity_check": _liquidity,
    "rug_pull_alert": _rug_pull,
    "exploit_check": _exploit_check,
    "market_intel": _market_intel,
    "safety_preflight": _safety_preflight,
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
