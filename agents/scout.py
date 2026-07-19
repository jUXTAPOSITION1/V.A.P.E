"""
SCOUT — VAPE's bounty-radar triage agent.

Per docs/ARCHITECTURE_ROADMAP.md's own design rule ("rule-based first, LLM
only when reasoning is required"), SCOUT ranks opportunities by a plain
numeric fit score — no LLM call, no token spend, safe to run hourly.

The one exception, where reasoning genuinely is required: every cycle with
anything to assess gets a real strategic analysis on top of the numeric
table (_strategic_briefing() below, via agents/llm.py's FRONTIER_ORDER) —
why the top opportunities matter and what VAPE should actually do about
them, not just a re-sorted list. Runs every cycle, not only when something's
new — coverage over conserving the frontier tier's one-time credit, by
explicit direction.

Insight also gets ACTED on, not just narrated: _act_on_incidents() below
delegates to agents/security_sweep.py's already-verified, real-chain
address-resolution pipeline (same dedup state file security_sweep.py's own
scheduled runs use) so a real incident — on any chain investigate.py can
actually work with, not just Base — gets a real agents/investigate.py
investigation triggered from SCOUT's hourly cadence too, not only
security_sweep's 4x/day. Never fabricates an address — same "verify or skip"
guarantee as attempt_incident_forensics() itself.

Real data source: DeFiLlama's public hacks feed (https://api.llama.fi/hacks,
keyless, already proven elsewhere in this repo via
agents/data_fetchers.get_hack_feed). This is the one opportunity type VAPE
can poll live end-to-end without a fragile HTML scrape or an undocumented
private API. The other platforms already present in
intel/bounty-radar/opportunities.json (HackenProof, HackerOne, Cantina,
Code4rena, Sherlock, Immunefi, AgentArena) were bundled in as static
seed/example data at repo import (commit e69546c) and have no public,
keyless, stable API to poll — wiring those up for real is future work, not
(Code4rena specifically announced its wind-down in May 2026, with Immunefi
absorbing its bounty programs and researchers — its seed entries here are
historical only; no new Code4rena leads should be expected going forward.)
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


def _strategic_briefing(new_entries, shown):
    """Real strategic analysis of THIS cycle's top opportunities — the
    frontier model's reasoning on WHY they matter and WHAT VAPE should
    actually do about them, not just a re-statement of the numeric-fit
    table below. Runs every cycle that has anything to assess (not gated
    on new_entries — per explicit direction, coverage matters more than
    conserving the frontier tier's one-time credit here). Returns "" on
    any failure/unavailability/nothing-to-assess — a digest without a
    briefing is still a complete, honest digest.
    """
    top = shown[:15]
    if not top:
        return ""
    try:
        from agents.llm import ask_oci_grok_safe, FRONTIER_ORDER
    except Exception:
        return ""

    lines = [
        f"- {e.get('name', 'Unknown')} | platform={e.get('platform', '')} | "
        f"fit={e.get('fitScore', 0)} | prize=${e.get('prizeUsd', 0):,.0f} | "
        f"status={e.get('status', '')} | tags={','.join(e.get('tags', []))} | "
        f"desc={e.get('desc', '')}"
        for e in top
    ]
    new_lines = [f"- {e.get('name', 'Unknown')} (fit {e.get('fitScore', 0)})" for e in new_entries[:15]]

    # Previously this briefing reasoned only over the fit-table itself, with
    # no outside research at all — one bounded web search on the top-ranked
    # entry's own name gives it real freedom to bring in fresh context (a
    # PoC, a disclosure thread, competing platforms already circling it) the
    # static feed can't show.
    try:
        from agents import intel_common as ic
        research = ic.web_search_snippets(f"{top[0].get('name', '')} exploit disclosure bug bounty", max_results=6)
    except Exception:
        research = {"available": False, "provider": None, "results": []}
    research_lines = (
        "\n".join(f"- {r['title']}: {r['snippet']}" for r in research.get("results", []))
        or "(no web research available this cycle)"
    )

    system = (
        "You are VAPE's strategic analyst for its bug-bounty/incident radar. VAPE is an "
        "autonomous on-chain detective specializing in Base/EVM forensics, smart-contract "
        "security, and bounty hunting. Give an opinionated, actionable strategic briefing on "
        "the real data below — not a summary of a table the reader already sees. No hedging, "
        "no invented details beyond what's given. You have real analytical freedom here: write "
        "at whatever depth the real data and research actually support — this is not a "
        "word-capped summary — and bring your own general knowledge of the bounty/security "
        "landscape to bear where useful, clearly marked as background rather than something "
        "this cycle's data itself showed."
    )
    user = (
        "=== TOP-RANKED OPPORTUNITIES THIS CYCLE (real, DeFiLlama hacks feed + seed bounty data) ===\n"
        + "\n".join(lines)
        + "\n\n=== NEW THIS CYCLE ===\n" + ("\n".join(new_lines) if new_lines else "(none — same top set as last cycle)")
        + f"\n\n=== WEB RESEARCH on top-ranked entry ({research.get('provider') or 'unavailable'}) ===\n"
        + research_lines
        + "\n\n=== YOUR TASK ===\n"
        "Pick as many opportunities as are genuinely worth VAPE's attention right now (not a "
        "fixed count). For each: WHY it matters (technique novelty, chain relevance, prize vs. "
        "effort), WHAT VAPE-specific capability or tool this would exercise or expose a gap in "
        "(recon, static analysis, forensics tracing), and ONE concrete next action. Fold in "
        "anything the web research above adds. If nothing changed since last cycle, say that "
        "plainly and don't repeat the same analysis verbatim — note what, if anything, is still "
        "worth chasing. If genuinely nothing here is worth VAPE's attention, say so plainly "
        "instead of padding."
    )
    try:
        text, _provider = ask_oci_grok_safe(system, user, tier="frontier", provider_order=FRONTIER_ORDER,
                                             max_tokens=1800, temperature=0.4)
    except Exception as e:
        print(f"[SCOUT] strategic briefing unavailable: {e}")
        return ""
    if not text or text.startswith("[llm unavailable"):
        return ""
    return text.strip()


def _act_on_incidents():
    """Real action step, not just narration: for recent (or large enough
    to still be worth chasing regardless of age) hack incidents on any
    chain investigate.py can work with, delegate to agents.security_sweep's
    already-built, address-verification pipeline (attempt_incident_forensics) — same
    skillforge/memory/attack_response_state.json dedup file
    security_sweep.py's own scheduled runs use, so this never re-does work
    those runs already did (or vice versa). Triggers a REAL
    agents.investigate.investigate() call whenever a real, verified address
    is found. Never fabricates an address: an incident search finding
    nothing verifiable is honestly recorded as unresolved, same as
    attempt_incident_forensics()'s own guarantee. Returns the list of
    outcomes; [] on any failure/no candidates — never raises."""
    try:
        from agents.data_fetchers import get_hack_feed
        from agents.security_sweep import attempt_incident_forensics
    except Exception as e:
        print(f"[SCOUT] action step unavailable: {e}")
        return []
    try:
        feed = get_hack_feed(limit=FETCH_LIMIT)
        incidents = feed.get("incidents", []) if isinstance(feed, dict) else []
        return attempt_incident_forensics(incidents)
    except Exception as e:
        print(f"[SCOUT] action step failed: {e}")
        return []


def _write_digest(entries, new_count, total_count, new_entries, forensics_outcomes=None):
    now = datetime.now(timezone.utc)
    path = os.path.join(INTEL_DIR, f"digest-{now.strftime('%Y-%m-%d-%H')}.md")
    ranked = sorted(entries, key=lambda x: x.get("fitScore", 0), reverse=True)
    shown = [e for e in ranked if e.get("fitScore", 0) >= FIT_THRESHOLD_DIGEST]

    lines = [
        f"# VAPE Bug Bounty Radar — {now.strftime('%Y-%m-%dT%H:%M:%S.%f')}Z",
        "",
        f"Scanned {total_count} opportunities. New: {new_count}. Showing fit>={FIT_THRESHOLD_DIGEST}.",
        "",
    ]

    briefing = _strategic_briefing(new_entries, shown)
    if briefing:
        lines += ["## Strategic Briefing", "", briefing, ""]

    if forensics_outcomes:
        lines += ["## Actions Taken This Cycle", ""]
        resolved = [o for o in forensics_outcomes if o.get("resolved")]
        if resolved:
            for o in resolved:
                lines.append(f"- ✅ **{o['incident']}** — verified address `{o['address']}`, "
                             "real investigation launched (see intel/investigations/).")
        unresolved = [o for o in forensics_outcomes if not o.get("resolved")]
        if unresolved:
            lines.append(f"- Searched but could not verify a real address for "
                         f"{len(unresolved)} other recent incident(s) this cycle "
                         "(no fabricated targets — recorded as unresolved).")
        lines.append("")

    lines += [
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
    forensics_outcomes = _act_on_incidents()
    digest_path = _write_digest(opportunities, len(new_entries), len(opportunities), new_entries,
                                forensics_outcomes)

    resolved_n = sum(1 for o in forensics_outcomes if o.get("resolved"))
    print(f"[SCOUT] scanned {len(fetched)} DeFiLlama incidents, {len(new_entries)} new, "
          f"{len(opportunities)} total in archive, {resolved_n} real investigation(s) launched this "
          f"cycle. Digest: {os.path.relpath(digest_path, _REPO_ROOT)}")
    return {"scanned": len(fetched), "new": len(new_entries), "total": len(opportunities),
            "investigations_launched": resolved_n}


if __name__ == "__main__":
    run()
