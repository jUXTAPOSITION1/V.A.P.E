"""
VAPE Macro & Micro News Sweep — revives the "vape-macro-micro-sweep" cron
(see intel/reports/macro-*.md). Same story as security_sweep.py's docstring.

Real data: agents/data_fetchers.py's Fear & Greed index, global market
breadth (BTC/ETH dominance, total mcap change), and stablecoin flows — all
keyless. MACRO TREND is computed deterministically from these real numbers.
One bounded web search adds regulatory/Fed context the numeric feeds can't
see. Runs daily (macro fundamentals move slower than the other sweeps).

Usage: python agents/macro_sweep.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import get_fear_greed, get_global_market, get_stablecoin_flows  # noqa: E402
from agents import intel_common as ic  # noqa: E402
from agents import llm  # noqa: E402


def compute_trend(fng, glob):
    """RISK-OFF / RISK-ON / NEUTRAL from real Fear&Greed + global mcap
    change — reproducible thresholds, not an LLM vibe.

    Extreme Fear&Greed or a sharp mcap move are strong enough signals to
    call the trend on their own (kept as-is below). But a LOT of days land
    in the ambiguous middle where neither threshold fires and the result was
    always a flat NEUTRAL — even though get_fear_greed() already fetches
    yesterday's reading (`prev_value`) specifically to support a momentum
    check, and that field was being discarded unused. Fast day-over-day
    sentiment movement is a real, harder-to-fake signal (a one-day
    Fear&Greed swing of 15+ points reflects an actual shift in aggregate
    market behavior, not noise), so it now gets a say in the ambiguous
    middle zone instead of always defaulting to NEUTRAL there."""
    fng_val = fng.get("value")
    mcap_chg = glob.get("mcap_change_24h_pct")
    if not (isinstance(fng_val, int) and isinstance(mcap_chg, (int, float))):
        return "UNKNOWN"
    if fng_val <= 25 or mcap_chg <= -5:
        return "RISK-OFF"
    if fng_val >= 70 and mcap_chg >= 2:
        return "RISK-ON"
    prev_val = fng.get("prev_value")
    if isinstance(prev_val, int):
        delta = fng_val - prev_val
        if delta <= -15:
            return "RISK-OFF"
        if delta >= 15 and mcap_chg > 0:
            return "RISK-ON"
    return "NEUTRAL"


def run():
    fng = get_fear_greed()
    glob = get_global_market()
    stables = get_stablecoin_flows()
    trend = compute_trend(fng, glob)

    search = ic.web_search_snippets("Federal Reserve interest rate crypto regulation news this week", max_results=8)
    ai_search = ic.web_search_snippets("AI agent crypto sector Base x402 micropayments news", max_results=8)

    top_stables = stables.get("top_stablecoins") or []
    stable_rows = "\n".join(
        f"| {s.get('symbol')} | {ic.fmt_usd(s.get('circulating_usd'))} |"
        for s in top_stables[:5]
    ) or "| — | unavailable this cycle |"

    system = (
        "You are VAPE, an autonomous macro analyst covering crypto markets. Write using "
        "ONLY the real numbers and search results provided — never invent Fed rate figures, "
        "regulatory dates, or news beyond what's given. If search results are thin, say so. "
        "You have real analytical freedom here — go as deep as the real data supports, connect "
        "the macro/regulatory picture to the AI-agent/crypto sector signal, and bring your own "
        "general market/macro knowledge to bear where useful, clearly marked as background "
        "rather than something this cycle's search itself surfaced."
    )
    user = (
        f"MACRO TREND (already computed, do not change it): {trend}\n"
        f"Fear & Greed: {fng.get('value', 'unavailable')} ({fng.get('classification', 'unavailable')})\n"
        f"Global mcap 24h change: {glob.get('mcap_change_24h_pct', 'unavailable')}%\n"
        f"BTC dominance: {glob.get('btc_dominance_pct', 'unavailable')}%, ETH dominance: {glob.get('eth_dominance_pct', 'unavailable')}%\n\n"
        f"Fed/regulatory web search results:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in search.get('results', [])] or 'none available'}\n\n"
        f"AI-agent/crypto sector web search results:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in ai_search.get('results', [])] or 'none available'}\n\n"
        "Write three sections in markdown, each starting with '### ':\n"
        "1. Key Drivers — Fed/regulatory context from the search results, cited specifically, at "
        "whatever depth they support.\n"
        "2. Micro Opportunities — AI-agent x crypto sector signal from the search results.\n"
        "3. Summary Verdict — tying the real numbers and search context together."
    )
    # ask_oci_grok_safe() tries OCI-hosted Grok 4.3 first, falling back to
    # VAPE's Vertex-tuned model (if VAPE_VERTEX_ACCESS_TOKEN is set), falling
    # back further to the same frontier tier/order as before — a run with
    # neither configured behaves identically to before this change.
    narrative, provider = llm.ask_oci_grok_safe(system, user, tier="frontier", max_tokens=2600,
                                                 provider_order=llm.FRONTIER_ORDER)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    trend_emoji = {"RISK-OFF": "⚠️", "RISK-ON": "🟢", "NEUTRAL": "🟡", "UNKNOWN": "⚪"}[trend]
    body = f"""# Macro & Micro News Sweep Report

**Date:** {stamp}

---

## MACRO TREND: {trend_emoji} {trend}

Computed deterministically from real Fear & Greed ({fng.get('value', 'unavailable')}, prior day
{fng.get('prev_value', 'unavailable')}) and global market cap 24h change
({glob.get('mcap_change_24h_pct', 'unavailable')}%). A sharp day-over-day Fear & Greed swing (15+
points) can also tip an otherwise-ambiguous reading toward RISK-OFF/RISK-ON — see the function
docstring in `agents/macro_sweep.py` for the exact thresholds.

---

## Market Breadth (real, keyless)

| Metric | Value |
|--------|-------|
| Fear & Greed | {fng.get('value', 'unavailable')} ({fng.get('classification', 'unavailable')}) |
| Fear & Greed (prior day) | {fng.get('prev_value', 'unavailable')} ({fng.get('prev_classification', 'unavailable')}) |
| Global Market Cap 24h | {glob.get('mcap_change_24h_pct', 'unavailable')}% |
| BTC Dominance | {glob.get('btc_dominance_pct', 'unavailable')}% |
| ETH Dominance | {glob.get('eth_dominance_pct', 'unavailable')}% |
| Total Market Cap | {ic.fmt_usd(glob.get('total_mcap_usd'))} |

### Top Stablecoins by Circulating Supply

| Symbol | Circulating |
|--------|-------------|
{stable_rows}

---

{narrative}

---

{ic.format_search_section("Web Signals — Fed / Regulatory", search)}

---

{ic.format_search_section("Web Signals — AI Agent Sector", ai_search)}

---

## Sources
- Fear & Greed Index (`api.alternative.me/fng`) — keyless
- CoinGecko global market data — keyless
- DefiLlama stablecoins — keyless
- Live web search ({search.get('provider') or 'unavailable'})
- LLM synthesis: {provider or 'unavailable this cycle'}

---

*Report generated by `agents/macro_sweep.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} after the
original ad hoc sweep silently stopped; see intel/reports/macro-2026-07-01-08.md for the last
pre-revival report.*
"""
    path = ic.write_report("macro", body)
    summary = f"Macro sweep: {trend} — F&G {fng.get('value', 'unavailable')}, mcap {glob.get('mcap_change_24h_pct', 'unavailable')}% 24h."
    ic.log_sweep_memory("agents/macro_sweep.py", trend, summary, path, tags=["macro"])
    print(f"[macro_sweep] {trend} — wrote {os.path.relpath(path, ic.ROOT)}")
    return {"trend": trend, "path": path}


if __name__ == "__main__":
    run()
