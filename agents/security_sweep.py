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
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import get_hack_feed  # noqa: E402
from agents import intel_common as ic  # noqa: E402
from agents import llm  # noqa: E402

RECENT_DAYS = 7
BIG_HACK_USD_M = 50
BIG_HACK_WINDOW_DAYS = 14


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


def run():
    feed = get_hack_feed(limit=15)
    incidents = feed.get("incidents", []) if isinstance(feed, dict) else []
    threat, recent, big_recent = compute_threat_level(incidents)

    search = ic.web_search_snippets("ERC-8183 ACP agent commerce protocol exploit vulnerability 2026", max_results=5)

    table_rows = "\n".join(
        f"| {h['date']} | {h['name']} | ${h['amount_usd_m']}M | {h.get('technique') or '—'} | {', '.join(h.get('chains') or []) or '—'} |"
        for h in incidents
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
    print(f"[security_sweep] {threat} — wrote {os.path.relpath(path, ic.ROOT)}")
    return {"threat": threat, "path": path}


if __name__ == "__main__":
    run()
