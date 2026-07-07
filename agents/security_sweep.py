"""
VAPE Security Sweep — revives the "vape-security-sweep" cron that ran as an
ad hoc Claude Code session (never committed code) for 3 weeks before
silently stopping 2026-07-01 with no trace anywhere in git history — see
intel/reports/security-*.md for the historical reports this restores.

Real data: agents/data_fetchers.get_hack_feed() (DeFiLlama's keyless hacks
feed, already proven elsewhere in this repo) is the backbone — dated
incidents, real $ lost, real chain/technique. THREAT LEVEL is computed
DETERMINISTICALLY from that feed (never LLM-guessed — see intel_common.py's
module docstring). One bounded live web search adds framework-level
context (ERC-8183/ACP-specific news) the hacks feed can't see; the LLM's
only job is synthesizing what these real inputs mean for VAPE's own
operational surface, grounded in the real data passed to it.

Usage: python agents/security_sweep.py
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import get_hack_feed  # noqa: E402
from agents import intel_common as ic  # noqa: E402
from agents import llm  # noqa: E402

RECENT_DAYS = 7
BIG_HACK_USD_M = 50
BIG_HACK_WINDOW_DAYS = 14

# Feeds docs/assets/attackfeed.js's homepage ticker + "Threat Ledger" section —
# more items than the report table shows (which stays short for readability),
# filtered to a real, dated lookback window rather than an arbitrary count so
# "past 2 months or so" is an honest, reproducible cutoff, not just "however
# many the API happened to return."
ATTACK_FEED_PATH = os.path.join(ic.ROOT, "data", "attack-feed.json")
ATTACK_FEED_LOOKBACK_DAYS = 60
ATTACK_FEED_FETCH_LIMIT = 40

# VAPE doesn't just report these incidents — for ones it can actually verify
# a target for, it runs its own real forensics pipeline against them (see
# attempt_incident_forensics() below). Scoped to Base only (investigate.py's
# real pipeline) and a real, resolved on-chain address only — never a
# fabricated one — so "investigating the attacks" means something checkable.
ATTACK_RESPONSE_STATE_PATH = os.path.join(ic.ROOT, "skillforge", "memory", "attack_response_state.json")
ATTACK_RESPONSE_LOOKBACK_DAYS = 14
_ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")


def _days_ago(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return 9999


def compute_threat_level(incidents):
    """Deterministic: HIGH if a big hack landed recently or 3+ hacks this
    week; MEDIUM if any hack this week; else LOW. Real thresholds, not a
    vibe — a reader can recompute this from the table below."""
    recent = [h for h in incidents if _days_ago(h["date"]) <= RECENT_DAYS]
    big_recent = [h for h in incidents
                  if _days_ago(h["date"]) <= BIG_HACK_WINDOW_DAYS and h.get("amount_usd_m", 0) >= BIG_HACK_USD_M]
    if big_recent or len(recent) >= 3:
        return "HIGH", recent, big_recent
    if recent:
        return "MEDIUM", recent, big_recent
    return "LOW", recent, big_recent


def write_attack_feed(incidents, threat, source_report_path):
    """Real, dated-window slice of the same incident feed the report table
    draws from — powers the homepage ticker and the full Threat Ledger
    section. `source_report` is the exact report this run just wrote, so
    the site can link the feed straight back to its knowledge source."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ATTACK_FEED_LOOKBACK_DAYS)
    recent = []
    for h in incidents:
        try:
            d = datetime.strptime(h["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if d >= cutoff:
            recent.append(h)
    payload = {
        "generated_at": ic.now_iso(),
        "source_report": os.path.relpath(source_report_path, ic.ROOT).replace(os.sep, "/"),
        "threat_level": threat,
        "lookback_days": ATTACK_FEED_LOOKBACK_DAYS,
        "incidents": recent,
    }
    os.makedirs(os.path.dirname(ATTACK_FEED_PATH), exist_ok=True)
    with open(ATTACK_FEED_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    return len(recent)


def _load_attack_response_state():
    try:
        with open(ATTACK_RESPONSE_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_attack_response_state(state):
    os.makedirs(os.path.dirname(ATTACK_RESPONSE_STATE_PATH), exist_ok=True)
    with open(ATTACK_RESPONSE_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def attempt_incident_forensics(incidents):
    """VAPE doesn't just narrate these incidents, it investigates the ones
    it can verify a real target for: for recent Base-chain hacks not
    already checked, search for the real on-chain address and, if one is
    found, run investigate.py's actual forensics pipeline against it —
    producing a genuine investigation report, not a summary of someone
    else's. Never fabricates an address: if search doesn't surface one,
    the incident is honestly recorded as unresolved and skipped. A state
    file makes this idempotent — each real incident is only ever searched
    once, not re-queried every 6 hours forever.
    """
    try:
        from agents import investigate as inv
    except Exception as e:
        print(f"[security_sweep] could not import investigate.py: {e}")
        return []

    state = _load_attack_response_state()
    cutoff = datetime.now(timezone.utc) - timedelta(days=ATTACK_RESPONSE_LOOKBACK_DAYS)
    outcomes = []
    for h in incidents:
        chains = [str(c).lower() for c in (h.get("chains") or [])]
        if "base" not in chains:
            continue
        try:
            d = datetime.strptime(h["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if d < cutoff:
            continue
        incident_id = f"{h['date']}:{h['name']}"
        if incident_id in state:
            continue  # already resolved-or-tried this exact real incident

        search = ic.web_search_snippets(f"{h['name']} exploit contract address Base Basescan", max_results=5)
        address = None
        for r in search.get("results", []):
            m = _ADDR_RE.search(f"{r.get('title', '')} {r.get('snippet', '')}")
            if m:
                address = m.group(0)
                break

        if not address:
            state[incident_id] = {"checked_at": ic.now_iso(), "resolved": False}
            outcomes.append({"incident": incident_id, "resolved": False})
            continue

        hint = f"post-incident forensics: {h['name']} exploit ({h['date']}, ${h.get('amount_usd_m')}M, {h.get('technique')})"
        try:
            result = inv.investigate(address, chain="8453", hint=hint, force=False)
        except Exception as e:
            print(f"[security_sweep] investigate({address}) failed: {e}")
            state[incident_id] = {"checked_at": ic.now_iso(), "resolved": False, "error": str(e)}
            outcomes.append({"incident": incident_id, "resolved": False})
            continue

        state[incident_id] = {
            "checked_at": ic.now_iso(), "resolved": True, "address": address,
            "verdict": result.get("verdict") or result.get("skipped"),
            "report": result.get("report"),
        }
        outcomes.append({"incident": incident_id, "resolved": True, "address": address})

    _save_attack_response_state(state)
    return outcomes


def run():
    feed = get_hack_feed(limit=ATTACK_FEED_FETCH_LIMIT)
    incidents = feed.get("incidents", []) if isinstance(feed, dict) else []
    threat, recent, big_recent = compute_threat_level(incidents)

    search = ic.web_search_snippets("ERC-8183 ACP agent commerce protocol exploit vulnerability 2026", max_results=5)

    # Report table stays short for readability even though `incidents` now
    # holds up to ATTACK_FEED_FETCH_LIMIT entries (the ticker/Threat Ledger
    # want more history than a markdown table should show inline).
    table_rows = "\n".join(
        f"| {h['date']} | {h['name']} | ${h['amount_usd_m']}M | {h.get('technique') or '—'} | {', '.join(h.get('chains') or []) or '—'} |"
        for h in incidents[:15]
    ) or "| — | no incidents in feed this cycle | — | — | — |"

    system = (
        "You are VAPE, an autonomous on-chain security analyst. Write the analysis sections "
        "of a security sweep report using ONLY the real data provided — never invent dollar "
        "amounts, dates, or incidents beyond what's given. If the data is thin, say so plainly "
        "rather than padding with generic security advice. Focus specifically on how these real "
        "incidents relate to VAPE's own operational surface: Base chain, ERC-8183/ACP job "
        "escrow contracts, and AI-agent-operated wallets."
    )
    user = (
        f"THREAT LEVEL (already computed from real data, do not change it): {threat}\n"
        f"Incidents in the last {RECENT_DAYS} days: {len(recent)}\n"
        f"Incidents >= ${BIG_HACK_USD_M}M in the last {BIG_HACK_WINDOW_DAYS} days: {len(big_recent)}\n\n"
        f"Full incident feed (real, from DeFiLlama):\n{table_rows}\n\n"
        f"Web search results on ERC-8183/ACP-specific security news:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in search.get('results', [])] or 'none available'}\n\n"
        "Write three sections in markdown, each starting with '### ':\n"
        "1. Summary — 3-5 sentences on the current threat landscape from the real incidents above.\n"
        "2. VAPE Impact Assessment — how these specific incidents/techniques relate to ERC-8183 "
        "escrow, ACP agent wallets, and Base-deployed contracts. Say plainly if there's no direct relevance.\n"
        "3. Recommendations — 3-5 concrete, specific action items, grounded in the real incidents above."
    )
    narrative, provider = llm.ask_safe(system, user, tier="deep", max_tokens=1400)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    threat_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[threat]
    body = f"""# VAPE Security Sweep Report

**Generated:** {stamp}
**Trigger:** `agents/security_sweep.py` (scheduled, GitHub Actions)

---

## THREAT LEVEL: {threat_emoji} {threat}

Computed deterministically: {len(recent)} incident(s) in the last {RECENT_DAYS} days across the
tracked feed, {len(big_recent)} of which exceeded ${BIG_HACK_USD_M}M within the last {BIG_HACK_WINDOW_DAYS} days.

---

## Recent DeFi/Crypto Incidents (real, DeFiLlama hacks feed)

| Date | Protocol | Amount Lost | Technique | Chain(s) |
|------|----------|-------------|-----------|----------|
{table_rows}

---

{narrative}

---

{ic.format_search_section("Web Signals — ERC-8183 / ACP", search)}

---

## Sources
- DeFiLlama hacks feed (`api.llama.fi/hacks`) — keyless, real-time
- Live web search ({search.get('provider') or 'unavailable'})
- LLM synthesis: {provider or 'unavailable this cycle'}

---

*Report generated by `agents/security_sweep.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} after the
original ad hoc sweep silently stopped; see intel/reports/security-2026-07-01-20.md for the last
pre-revival report.*
"""
    path = ic.write_report("security", body)
    summary = f"Security sweep: {threat} — {len(recent)} incident(s) in last {RECENT_DAYS}d, {len(big_recent)} >= ${BIG_HACK_USD_M}M."
    ic.log_sweep_memory("agents/security_sweep.py", threat, summary, path, tags=["security"])

    feed_count = write_attack_feed(incidents, threat, path)
    forensics = attempt_incident_forensics(incidents)
    resolved = [o for o in forensics if o["resolved"]]
    if forensics:
        print(f"[security_sweep] incident forensics: {len(resolved)}/{len(forensics)} new Base incident(s) "
              f"resolved to a real address and investigated")

    print(f"[security_sweep] {threat} — wrote {os.path.relpath(path, ic.ROOT)}, "
          f"{feed_count} incident(s) in attack feed")
    return {"threat": threat, "path": path, "feed_count": feed_count, "forensics": forensics}


if __name__ == "__main__":
    run()
