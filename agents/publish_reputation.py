#!/usr/bin/env python3
"""
VAPE reputation publisher — emit a verifiable services + track-record JSON the
dashboard fetches client-side. REAL DATA ONLY: every number is counted from the
repo or pulled from on-chain identity. No invented job counts, no fake 5-star ratings.

Writes: data/reputation.json  (committed; dashboard fetches it raw from GitHub)

Sources (all verifiable):
  - reports/, intel/broadcasts/, intel/catalog/, intel/scans/   (real artifact counts)
  - skillforge/memory/tools-registry.json                       (real tool tiers)
  - skillforge/memory/lessons.jsonl                             (real job/work log)
  - agents/acp_fulfill.py HANDLERS + price map                  (live offerings)
  - on-chain identity constants (wallet, ERC-8004, agent id)    (publicly checkable)

Zero new deps (stdlib only). Runs on the free GitHub runner.
"""
import json
import os
import glob
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "reputation.json")

# Publicly verifiable on-chain identity (anyone can check these).
IDENTITY = {
    "agent": "VAPE",
    "name": "Virtual Ape Private Eye",
    "wallet": "0xa1420293a7df49bc8380f543a1fe7b8d6f582879",
    "erc8004_id": 54988,
    "agent_id": "019eaf60-592a-7f5c-99a2-3e85199303fe",
    "vape_token": "0x2b601d7fc4705361F0c0249a005a714b7A3EdaFE",
    "chain": "Base",
    "x": "https://x.com/based_vape",
    "verify_identity": "https://app.virtuals.io/acp/agent/019eaf60-592a-7f5c-99a2-3e85199303fe",
}

# Live offerings the agent SELLS (price + which are auto-fulfilled with zero LLM).
AUTO = {"token_safety_check", "liquidity_check", "rug_pull_alert",
        "exploit_check", "safety_preflight", "market_intel"}
OFFERINGS = [
    ("exploit_check", 0.01, "Exploit & scam-database check for any Base wallet/contract"),
    ("partner_referral", 0.01, "Earn USDC commission referring clients to VAPE"),
    ("token_safety_check", 0.02, "Honeypot detector + 0-100 safety score (GoPlus+DexScreener)"),
    ("liquidity_check", 0.02, "DEX liquidity depth, LP burn, slippage + SAFE/THIN/DANGEROUS"),
    ("wallet_recon", 0.03, "Address profiling: holdings, patterns, risk flags"),
    ("rug_pull_alert", 0.03, "Rug risk LOW/MEDIUM/HIGH/EXTREME with specific red flags"),
    ("tx_decode", 0.05, "Plain-language tx decode + risk flags for any Base tx hash"),
    ("safety_preflight", 0.05, "All-in-one pre-trade GO/CAUTION/NO_GO verdict"),
    ("whale_watch", 0.10, "Whale buys/sells + BULLISH/BEARISH/NEUTRAL net-flow"),
    ("community_intel_broadcast", 0.10, "6-hourly consolidated security+market intel broadcast"),
    ("market_intel", 0.15, "Real-time price/TVL/liquidity + actionable signal"),
    ("bulk_safety_bundle", 0.50, "Scan 5-25 tokens in one job, 40% off"),
    ("deep_contract_audit", 1.00, "slither+aderyn+mythril severity-rated audit + 0-100 score"),
    ("forensics_deep", 2.00, "Full wallet trace + chain-of-custody graph"),
    ("bounty_deep_dive", 50.00, "24h-SLA premium audit: full recon + Slither + frontier-model "
     "line-by-line source review, real report"),
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def count_glob(pattern):
    return len(glob.glob(os.path.join(ROOT, pattern)))


def newest_oldest(pattern, rx=r"(\d{8})"):
    files = glob.glob(os.path.join(ROOT, pattern))
    dates = []
    for f in files:
        m = re.search(rx, os.path.basename(f))
        if m:
            dates.append(m.group(1))
    if not dates:
        return None, None
    dates.sort()
    return dates[0], dates[-1]


def tool_stats():
    p = os.path.join(ROOT, "skillforge/memory/tools-registry.json")
    try:
        d = json.load(open(p))
        tiers = d.get("tiers", {})
        total = sum(len(v) for v in tiers.values() if hasattr(v, "__len__"))
        verified = 0
        for tier in tiers.values():
            items = tier.values() if isinstance(tier, dict) else (tier if isinstance(tier, list) else [])
            for t in items:
                if isinstance(t, dict) and t.get("status") in ("verified", "ok", "installed"):
                    verified += 1
        return total, verified, {k: (len(v) if hasattr(v, "__len__") else 0) for k, v in tiers.items()}
    except Exception:
        return 0, 0, {}


def lessons_stats():
    p = os.path.join(ROOT, "skillforge/memory/lessons.jsonl")
    work_entries = 0
    auto_jobs = 0
    try:
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            work_entries += 1
            try:
                j = json.loads(line)
                if j.get("path") == "zero-llm" or j.get("outcome") == "auto_submitted":
                    auto_jobs += 1
            except Exception:
                pass
    except Exception:
        pass
    return work_entries, auto_jobs


def main():
    total_tools, verified_tools, tier_breakdown = tool_stats()
    work_entries, auto_jobs = lessons_stats()
    first, last = newest_oldest("reports/bounty_report_*.md")

    # Real investigation count — one file per real deep investigation, same
    # pattern as reports_published/token_scans_logged above. Previously
    # counted "- "/"* " bullet lines in investigation-catalog.md, but
    # agents/investigate.py::update_catalog() appends "| ... |" markdown
    # TABLE rows, not bullets — every real auto-investigation since the
    # catalog switched to table format was silently uncounted, freezing this
    # number at the 42 bullet-style entries from the original June seed data
    # forever regardless of how many new investigations actually ran.
    catalog = count_glob("intel/investigations/*.md")

    rep = {
        "generated": now(),
        "identity": IDENTITY,
        "verifiable_activity": {
            "reports_published": count_glob("reports/*.md"),
            "intel_reports": count_glob("intel/reports/*.md"),
            "intel_broadcasts": count_glob("intel/broadcasts/*.md"),
            "catalog_investigations": catalog,
            "token_scans_logged": count_glob("intel/scans/scan-*.md"),
            "skills_codified": count_glob("skillforge/skills/*.md"),
            "tools_total": total_tools,
            "tools_verified": verified_tools,
            "tool_tiers": tier_breakdown,
            "work_log_entries": work_entries,
            "auto_fulfilled_jobs": auto_jobs,
            "first_report": first,
            "latest_report": last,
        },
        "capabilities": {
            "offerings_live": len(OFFERINGS),
            "auto_fulfilled_zero_llm": sorted(AUTO),
            "offerings": [
                {"name": n, "price_usd": p, "summary": s, "auto": n in AUTO}
                for n, p, s in OFFERINGS
            ],
        },
        "operating_model": {
            "data": "real-data-only — every finding sourced from GoPlus/DexScreener/"
                    "DefiLlama/CoinGecko/Base RPC/Etherscan, never fabricated",
            "compute": "near-zero — listener+drain idle at no cost; 6 offerings settle "
                       "with no model wake; GitHub Actions run the pipeline free",
            "rails": "ACP on Base — escrowed USDC jobs, ERC-8004 registered identity",
            "uptime": "24/7 — detached daemons (PPID 1) + hourly GitHub workflows",
        },
        "disclaimer": "Activity counts are generated from this public repo and on-chain "
                      "identity — independently verifiable. Not investment advice.",
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(rep, f, indent=2)
    print(json.dumps({"wrote": OUT, "reports": rep["verifiable_activity"]["reports_published"],
                      "offerings": len(OFFERINGS), "tools_verified": verified_tools}, indent=2))


if __name__ == "__main__":
    main()
