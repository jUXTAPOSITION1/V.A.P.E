"""
VAPE Bug Bounty Intelligence — revives the "Bug Bounty Intelligence Report"
cron (see intel/reports/bug-bounty-intel-2026-06-10.md), which only ever
ran once. Its core, still-open watch item was: "Virtuals Protocol is
actively working with Immunefi to launch a bug bounty program (not yet
live)" — this makes that a real recurring check instead of a one-time note.

Real data: a targeted live web search checks for an actual Immunefi listing;
a second, broader search adds real context on the wider Base bug-bounty
landscape; agents/scout.py's own real, keyless DeFiLlama-hacks-derived
archive (intel/bounty-radar/opportunities.json, already running hourly via
scout.yml) supplies a real cross-reference of recent Base-tagged incidents/
opportunities, so this doesn't re-fetch data scout.py already maintains.
The VERDICT stays a deterministic hostname check (never LLM-guessed); a
frontier-tier (Grok 4.1 Fast first — see agents/intel_common.py's
grok_analysis()) Analyst Briefing section synthesizes what both searches +
the opportunities table actually imply.

Runs weekly — bounty-program launches are rare events, no value in daily polling.

Usage: python agents/bug_bounty_intel.py
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import intel_common as ic  # noqa: E402

OPPORTUNITIES_PATH = os.path.join(ic.ROOT, "intel", "bounty-radar", "opportunities.json")
LOOKBACK_DAYS = 14


def load_recent_base_opportunities():
    try:
        with open(OPPORTUNITIES_PATH) as f:
            opps = json.load(f)
    except Exception:
        return []
    if not isinstance(opps, list):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    out = []
    for o in opps:
        tags = o.get("tags") or []
        if "base" not in [str(t).lower() for t in tags]:
            continue
        try:
            seen = datetime.fromisoformat(str(o.get("firstSeen", "")).replace("Z", "+00:00"))
        except Exception:
            continue
        if seen >= cutoff:
            out.append(o)
    out.sort(key=lambda o: o.get("fitScore", 0), reverse=True)
    return out[:10]


def _is_immunefi_url(url):
    """Real hostname check, not a substring match — CodeQL correctly flagged
    the substring form as unreliable (e.g. 'evil.com/?u=immunefi.com' or
    'immunefi.com.evil.com' would both false-positive on 'in url')."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    return host == "immunefi.com" or host.endswith(".immunefi.com")


def run():
    search = ic.web_search_snippets("Virtuals Protocol Immunefi bug bounty program launch", max_results=8)
    # Second, broader query — the narrow Immunefi/Virtuals check above answers
    # one specific yes/no, but gives Grok nothing else to reason about; this
    # gives it real material on the wider Base bug-bounty landscape so the
    # analyst section below can do more than restate the verdict.
    landscape_search = ic.web_search_snippets("Base blockchain bug bounty program launch 2026", max_results=8)
    immunefi_live = any(
        _is_immunefi_url(r.get("url") or "") and "virtual" in (r.get("title", "") + r.get("snippet", "")).lower()
        for r in search.get("results", [])
    )

    recent = load_recent_base_opportunities()
    recent_rows = "\n".join(
        f"| {o.get('name')} | {o.get('platform')} | ${o.get('prizeUsd', 0):,.0f} | {o.get('firstSeen', '')[:10]} |"
        for o in recent
    ) or f"| — | no new Base-tagged opportunities in the last {LOOKBACK_DAYS}d | — | — |"

    verdict = "IMMUNEFI LIVE" if immunefi_live else "NOT YET LAUNCHED"

    briefing = ic.grok_analysis(
        "bug-bounty-intelligence analyst",
        (
            f"VERDICT (deterministic, do not change): {verdict}\n\n"
            f"Targeted search — Virtuals Protocol x Immunefi ({search.get('provider') or 'unavailable'}):\n"
            + ("\n".join(f"- {r['title']} ({r['url']}): {r['snippet']}" for r in search.get("results", [])) or "none")
            + f"\n\nBroader search — Base bug bounty landscape ({landscape_search.get('provider') or 'unavailable'}):\n"
            + ("\n".join(f"- {r['title']} ({r['url']}): {r['snippet']}" for r in landscape_search.get("results", [])) or "none")
            + f"\n\nRecent Base-tagged opportunities from scout.py's archive (last {LOOKBACK_DAYS}d):\n{recent_rows}"
        ),
        instructions=(
            "Write the 'Analyst Briefing' section of this bug-bounty-intelligence report. Interpret "
            "what the search results actually suggest about the state of Base/Virtuals bug-bounty "
            "coverage — not just whether Immunefi is live, but what the broader landscape search "
            "implies about competing platforms, timing, or gaps VAPE itself could speak to. If the "
            "opportunities table shows a pattern worth flagging, say so."
        ),
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""# Bug Bounty Intelligence Report — Base & Virtuals Protocol

**Date:** {stamp}

---

## VERDICT: {verdict}

Real check: searched for a live Virtuals Protocol Immunefi listing this cycle.
{'Found a matching immunefi.com result — see Web Signals below.' if immunefi_live else "No matching immunefi.com listing found in this cycle's search results."}

---

## Recent Base-Tagged Opportunities (real, from `agents/scout.py`'s archive)

Cross-referenced from `intel/bounty-radar/opportunities.json` — the same real,
keyless DeFiLlama-hacks-derived archive `scout.yml` maintains hourly, filtered to
Base-tagged entries seen in the last {LOOKBACK_DAYS} days.

| Name | Platform | Prize/Loss | First Seen |
|------|----------|------------|------------|
{recent_rows}

---

## Analyst Briefing (Grok 4.1 Fast)

{briefing}

---

{ic.format_search_section("Web Signals — Immunefi / Bounty Programs", search)}

---

{ic.format_search_section("Web Signals — Base Bug Bounty Landscape", landscape_search)}

---

## Recommended Actions

1. Re-run this check weekly — Immunefi program launches are rare, infrequent events.
2. If VERDICT flips to IMMUNEFI LIVE, cross-check scope against `intel/reports/attack-surface-map-2026-06-10.md`'s
   flagged findings for anything still unpatched per `agents/mainnet_patch_check.py`'s latest run.
3. Direct disclosure to security@virtuals.io remains available regardless of Immunefi status.

---

## Sources
- Live web search — targeted ({search.get('provider') or 'unavailable'}) + broader landscape ({landscape_search.get('provider') or 'unavailable'})
- `intel/bounty-radar/opportunities.json` (real, maintained by `agents/scout.py` hourly)
- Analyst Briefing: OCI-hosted Grok 4.3 (or the next available provider — Vertex-tuned Gemini, then `agents.llm.FRONTIER_ORDER`)

---

*Report generated by `agents/bug_bounty_intel.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} as a
real recurring check of the original one-time 2026-06-10 finding.*
"""
    path = ic.write_report("bug-bounty-intel", body)
    summary = f"Bug bounty intel: {verdict}. {len(recent)} recent Base-tagged opportunity(s) cross-referenced."
    ic.log_sweep_memory("agents/bug_bounty_intel.py", verdict, summary, path, tags=["bounty", "virtuals"])
    print(f"[bug_bounty_intel] {verdict} — wrote {os.path.relpath(path, ic.ROOT)}")
    return {"verdict": verdict, "path": path}


if __name__ == "__main__":
    run()
