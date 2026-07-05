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
  - GitHub PR search (real "VAPE build:"/"VAPE self-build:" PRs)  (live build ledger)

Zero new deps (stdlib only). Runs on the free GitHub runner.
"""
import json
import os
import glob
import re
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "reputation.json")
REPO_SLUG = "jUXTAPOSITION1/V.A.P.E"

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
# Payable via the x402 worker specifically — must match worker/src/index.ts's
# OFFERING_PRICES keys (the synchronous AUTO set) plus bounty_deep_dive, which
# has its own async /scan/bounty_deep_dive route (dispatches a real GitHub
# Actions job rather than returning inline). Distinct from AUTO/"zero-LLM"
# above: bounty_deep_dive uses a frontier-model LLM but is still x402-payable.
X402 = AUTO | {"bounty_deep_dive"}
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


# Strict prefixes only — GitHub's search API does fuzzy/tokenized matching (a
# search for "VAPE build" also matches titles like "SKILLFORGE self-directed
# build: VAPE proposes..." that merely contain both words), so the API call
# below is just a candidate filter; this regex is the real gate that decides
# what actually counts as a VAPE-built tool for the public ledger.
_BUILD_TITLE_RE = re.compile(r"^VAPE (self-build|build):\s*(.+)$", re.IGNORECASE)
_VERIFY_RE = re.compile(r"^- ([OK]|[WARN]|[FAIL]) `([^`]+)`", re.MULTILINE)


def _gh_search_prs(query, token=None):
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode({
        "q": f"repo:{REPO_SLUG} is:pr in:title {query}",
        "sort": "created", "order": "desc", "per_page": 30,
    })
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "vape-reputation/1.0"}
    if token:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()).get("items", [])
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"[publish_reputation] GitHub PR search failed for {query!r}: {e}")
        return []


def tool_builds():
    """Real, live ledger of tools VAPE has actually built via its autonomous
    build pipelines (agents/build_request.py, agents/skillforge_build.py) —
    every entry here is a real PR that really exists on GitHub right now, not
    a hand-maintained changelog. Most cycles produce nothing (grounded
    proposals only, see agents/skillforge_build.py's gather_signals()), so a
    short or empty list here is expected and correct, not a bug."""
    token = os.getenv("GITHUB_TOKEN")
    seen, builds = set(), []
    for query in ('"VAPE build"', '"VAPE self-build"'):
        for item in _gh_search_prs(query, token):
            number = item.get("number")
            if number in seen:
                continue
            m = _BUILD_TITLE_RE.match(item.get("title", ""))
            if not m:
                continue  # fuzzy API match that isn't actually a build-pipeline PR
            seen.add(number)
            pr = item.get("pull_request") or {}
            body = item.get("body") or ""
            verify_counts = {"ok": 0, "warn": 0, "fail": 0}
            for icon, _path in _VERIFY_RE.findall(body):
                verify_counts["ok" if icon == "[OK]" else "warn" if icon == "[WARN]" else "fail"] += 1
            status = "merged" if pr.get("merged_at") else ("open" if item.get("state") == "open" else "closed")
            builds.append({
                "number": number,
                "title": m.group(2).strip(),
                "kind": "self-directed" if m.group(1).lower() == "self-build" else "issue-driven",
                "status": status,
                "url": item.get("html_url"),
                "created_at": item.get("created_at"),
                "closed_at": item.get("closed_at"),
                "verification": verify_counts,
            })
    builds.sort(key=lambda b: b["created_at"] or "", reverse=True)
    return builds


def main():
    total_tools, verified_tools, tier_breakdown = tool_stats()
    work_entries, auto_jobs = lessons_stats()
    first, last = newest_oldest("reports/bounty_report_*.md")
    builds = tool_builds()

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
            "tools_built": len(builds),
            "tools_built_list": builds,
            "work_log_entries": work_entries,
            "auto_fulfilled_jobs": auto_jobs,
            "first_report": first,
            "latest_report": last,
        },
        "capabilities": {
            "offerings_live": len(OFFERINGS),
            "auto_fulfilled_zero_llm": sorted(AUTO),
            "offerings": [
                {"name": n, "price_usd": p, "summary": s, "auto": n in AUTO, "x402": n in X402,
                 "sla": "24h (async, frontier-model)" if n == "bounty_deep_dive" else "instant"}
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
                      "offerings": len(OFFERINGS), "tools_verified": verified_tools,
                      "tools_built": len(builds)}, indent=2))


if __name__ == "__main__":
    main()
