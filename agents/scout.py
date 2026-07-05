"""
SCOUT — VAPE's bounty-radar triage agent.

Per docs/ARCHITECTURE_ROADMAP.md's own design rule ("rule-based first, LLM
only when reasoning is required"), SCOUT ranks opportunities by a plain
numeric fit score — no LLM call, no token spend, safe to run hourly.

Real data source: DeFiLlama's public hacks feed (https://api.llama.fi/hacks,
keyless, already proven elsewhere in this repo via
agents/data_fetchers.get_hack_feed). This is the one opportunity type VAPE
can poll live end-to-end without a fragile HTML scrape or an undocumented
private API. The other platforms already present in
intel/bounty-radar/opportunities.json (HackenProof, HackerOne, Cantina,
Code4rena, Sherlock, Immunefi, AgentArena) were bundled in as static
seed/example data at repo import (commit e69546c) and have no public,
keyless, stable API to poll — wiring those up for real is future work, not
faked here.

Behavior: append-only. Existing opportunities (including the June 2026 seed
set) are never rewritten — only genuinely new incidents get appended, with
isNew=True and firstSeen=now. seen.json tracks lastSeen for every incident
touched this run so future runs can tell "still around" from "new."
"""
import json
import math
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import _get  # noqa: E402  (keyless, file-cached GET)

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTEL_DIR = os.path.join(_REPO_ROOT, "intel", "bounty-radar")
OPPORTUNITIES_PATH = os.path.join(INTEL_DIR, "opportunities.json")
SEEN_PATH = os.path.join(INTEL_DIR, "seen.json")

MAX_OPPORTUNITIES = 2000     # safety cap so the archive can't grow unbounded
FIT_THRESHOLD_DIGEST = 50    # matches the existing digest convention
FETCH_LIMIT = 150            # how many recent DeFiLlama incidents to consider per run

BASE_CHAIN_HINTS = {"base", "coinbase"}
EVM_CHAIN_HINTS = {
    "ethereum", "arbitrum", "optimism", "polygon", "bsc", "avalanche",
    "fantom", "blast", "linea", "scroll", "zksync era", "zksync", "berachain", "mantle",
}
FORENSICS_TAG_HINTS = ("bridge", "reentrancy", "oracle", "access control", "logic", "key compromise")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def _fit_score(prize_usd, chains, technique, date_unix):
    """Pure numeric heuristic — no LLM. Weighs size (log scale, so a $10M
    incident doesn't drown out everything else), Base/EVM relevance (VAPE's
    home turf), recency, and whether the technique matches VAPE's forensics
    specialty (bridges, oracles, access control, key compromise)."""
    amount_score = min(70, 10 * math.log10(max(prize_usd, 1000)))

    chains_lower = {str(c).lower() for c in (chains or [])}
    if chains_lower & BASE_CHAIN_HINTS:
        chain_bonus = 20
    elif chains_lower & EVM_CHAIN_HINTS:
        chain_bonus = 10
    else:
        chain_bonus = 0

    age_days = (time.time() - date_unix) / 86400 if date_unix else 999
    if age_days <= 30:
        recency_bonus = 10
    elif age_days <= 90:
        recency_bonus = 5
    else:
        recency_bonus = 0

    technique_lower = str(technique or "").lower()
    technique_bonus = 5 if any(h in technique_lower for h in FORENSICS_TAG_HINTS) else 0

    return round(min(100, amount_score + chain_bonus + recency_bonus + technique_bonus))


def fetch_defillama_hacks(limit=FETCH_LIMIT):
    """Real incidents from DeFiLlama, shaped into opportunities.json's schema."""
    raw = _get("https://api.llama.fi/hacks", ttl=1800, cache_key="llama_hacks")
    if not isinstance(raw, list):
        return []
    out = []
    for h in sorted(raw, key=lambda x: x.get("date", 0), reverse=True)[:limit]:
        date_unix = h.get("date") or 0
        name = h.get("name") or "Unknown"
        amount = h.get("amount") or 0
        chains = h.get("chain") or []
        technique = h.get("technique") or ""
        opp_id = f"defillama-hack:{name}-{date_unix}"
        tags = ["incident-lead", "forensics"] + [str(c).lower() for c in chains]
        desc = (
            f"{technique} on {','.join(chains)}. Lead for incident response + forensics."
            if technique else
            f"Incident lead for forensics on {','.join(chains)}."
        )
        out.append({
            "platform": "defillama-hack",
            "id": opp_id,
            "name": f"{name} (exploit ${amount:,.0f})" if amount else name,
            "prizeUsd": round(amount),
            "currency": "USD",
            "status": "incident",
            "url": "https://defillama.com/hacks",
            "deadline": None,
            "tags": tags,
            "desc": desc,
            "fitScore": _fit_score(amount, chains, technique, date_unix),
        })
    return out


def _write_digest(entries, new_count, total_count):
    now = datetime.now(timezone.utc)
    path = os.path.join(INTEL_DIR, f"digest-{now.strftime('%Y-%m-%d-%H')}.md")
    ranked = sorted(entries, key=lambda x: x.get("fitScore", 0), reverse=True)
    shown = [e for e in ranked if e.get("fitScore", 0) >= FIT_THRESHOLD_DIGEST]

    lines = [
        f"# VAPE Bug Bounty Radar — {now.strftime('%Y-%m-%dT%H:%M:%S.%f')}Z",
        "",
        f"Scanned {total_count} opportunities. New: {new_count}. Showing fit>={FIT_THRESHOLD_DIGEST}.",
        "",
        "| Fit | Prize | Platform | Program | Status | New |",
        "|----|-------|----------|---------|--------|-----|",
    ]
    for e in shown:
        prize = f"${e['prizeUsd']:,.0f}" if e.get("prizeUsd") else "—"
        program = f"[{e.get('name', 'Unknown')}]({e.get('url', '#')})"
        new_mark = "[OK]" if e.get("isNew") else ""
        lines.append(f"| {e.get('fitScore', 0)} | {prize} | {e.get('platform', '')} | {program} | {e.get('status', '')} | {new_mark} |")

    lines += ["", "## Top targets (act now)", ""]
    for e in shown[:8]:
        prize = f"${e['prizeUsd']:,.0f}" if e.get("prizeUsd") else "—"
        lines.append(f"- **{e.get('name', 'Unknown')}** ({e.get('platform', '')}, fit {e.get('fitScore', 0)}, {prize}) — {e.get('url', '')}")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return path


def run():
    opportunities = _load_json(OPPORTUNITIES_PATH, [])
    if not isinstance(opportunities, list):
        opportunities = []
    seen = _load_json(SEEN_PATH, {})
    if not isinstance(seen, dict):
        seen = {}

    existing_ids = {o.get("id") for o in opportunities}
    now_iso = _now_iso()

    fetched = fetch_defillama_hacks()
    new_entries = []

    for opp in fetched:
        opp_id = opp["id"]
        is_new = opp_id not in existing_ids
        opp["isNew"] = is_new
        opp["firstSeen"] = now_iso if is_new else seen.get(opp_id, {}).get("firstSeen", now_iso)

        seen[opp_id] = {
            "name": opp["name"],
            "prizeUsd": opp["prizeUsd"],
            "lastSeen": now_iso,
        }

        if is_new:
            new_entries.append(opp)

    if new_entries:
        opportunities = opportunities + new_entries
        if len(opportunities) > MAX_OPPORTUNITIES:
            opportunities = sorted(
                opportunities, key=lambda o: o.get("firstSeen", ""), reverse=True
            )[:MAX_OPPORTUNITIES]
        _save_json(OPPORTUNITIES_PATH, opportunities)

    _save_json(SEEN_PATH, seen)
    digest_path = _write_digest(opportunities, len(new_entries), len(opportunities))

    print(f"[SCOUT] scanned {len(fetched)} DeFiLlama incidents, {len(new_entries)} new, "
          f"{len(opportunities)} total in archive. Digest: {os.path.relpath(digest_path, _REPO_ROOT)}")
    return {"scanned": len(fetched), "new": len(new_entries), "total": len(opportunities)}


if __name__ == "__main__":
    run()
