"""
VAPE Sentiment Sweep — revives the "X/Twitter Sentiment Sweep" cron (see
intel/reports/sentiment-*.md). Same story as security_sweep.py's docstring.

The historical reports self-flagged their own biggest weakness: "xurl is
NOT authenticated... relies on web_search site:x.com surface data, which
returns mostly cached snapshots... Treat sentiment as directional, not
precise." This revival fixes that honestly rather than repeating it:
- The headline SENTIMENT SCORE is the real, objective Fear & Greed index
  (agents/data_fetchers.get_fear_greed(), keyless, live) — not an LLM's
  impression of a handful of cached search snippets.
- The narrative section is explicitly labeled as an LLM's qualitative read
  of live web search results (skillforge/research.py's Tavily/Brave-backed
  search, not a raw site:x.com scrape), with source attribution so a reader
  can tell real signal from interpretation.

Usage: python agents/sentiment_sweep.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import get_fear_greed  # noqa: E402
from agents import intel_common as ic  # noqa: E402
from agents import llm  # noqa: E402


def score_label(fng_value):
    """Maps the real Fear & Greed value (0-100) to a /10 score + label —
    a fixed, reproducible mapping, not an LLM opinion."""
    if fng_value is None:
        return None, "unavailable"
    tenth = round(fng_value / 10, 1)
    if fng_value >= 75:
        label = "Extreme Greed"
    elif fng_value >= 55:
        label = "Greed / Bullish-leaning"
    elif fng_value >= 45:
        label = "Neutral"
    elif fng_value >= 25:
        label = "Fear / Bearish-leaning"
    else:
        label = "Extreme Fear"
    return tenth, label


def run():
    fng = get_fear_greed()
    fng_value = fng.get("value") if isinstance(fng, dict) else None
    score, label = score_label(fng_value)

    virtuals_search = ic.web_search_snippets("Virtuals Protocol AI agent Base ecosystem news this week", max_results=5)
    base_search = ic.web_search_snippets("Base blockchain Coinbase crypto sentiment narrative this week", max_results=5)

    system = (
        "You are VAPE, an autonomous crypto-market analyst. Write a qualitative narrative "
        "read of Virtuals Protocol / Base sentiment using ONLY the real search results "
        "provided below — do not claim access to live X/Twitter data you don't have, and "
        "do not invent engagement numbers, follower counts, or specific posts not present "
        "in the snippets. If the search results are thin, say so plainly."
    )
    user = (
        f"Real Fear & Greed index: {fng_value if fng_value is not None else 'unavailable'} "
        f"({fng.get('classification', 'unavailable')}), previous: {fng.get('prev_value', 'unavailable')} "
        f"({fng.get('prev_classification', 'unavailable')})\n\n"
        f"Virtuals Protocol / AI agent web search results:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in virtuals_search.get('results', [])] or 'none available'}\n\n"
        f"Base / crypto sentiment web search results:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in base_search.get('results', [])] or 'none available'}\n\n"
        "Write two sections in markdown, each starting with '### ':\n"
        "1. Top Narratives — the 3-5 most notable themes from the search results above, "
        "citing which result each comes from.\n"
        "2. Narrative Shifts — how this compares to what you'd expect from the real Fear & Greed "
        "reading, and any tension between the numeric mood and the qualitative narrative."
    )
    narrative, provider = llm.ask_safe(system, user, tier="deep", max_tokens=1200)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""# Sentiment Sweep Report — {stamp}

**Source fidelity:** SENTIMENT SCORE below is the real, live Fear & Greed index (objective,
keyless, `alternative.me/fng`) — not an LLM impression. The narrative sections are an LLM's
qualitative read of live web search results (Tavily/Brave-backed, with keyless fallback),
clearly separated from the objective score so directional narrative color is never mistaken
for a precise, quantified reading.

---

## SENTIMENT SCORE: {score if score is not None else 'N/A'}/10 ({label})

Real Fear & Greed index: **{fng_value if fng_value is not None else 'unavailable'}** ({fng.get('classification', 'unavailable')}).
Previous reading: {fng.get('prev_value', 'unavailable')} ({fng.get('prev_classification', 'unavailable')}).

---

{narrative}

---

{ic.format_search_section("Web Signals — Virtuals / AI Agents", virtuals_search)}

---

{ic.format_search_section("Web Signals — Base / Crypto Narrative", base_search)}

---

## Sources
- Fear & Greed Index (`api.alternative.me/fng`) — keyless, real-time
- Live web search ({virtuals_search.get('provider') or 'unavailable'})
- LLM synthesis: {provider or 'unavailable this cycle'}

---

*Report generated by `agents/sentiment_sweep.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} with an
honest fix for the original sweep's self-flagged low source fidelity; see
intel/reports/sentiment-2026-07-01-20.md for the last pre-revival report.*
"""
    path = ic.write_report("sentiment", body)
    summary = f"Sentiment sweep: {score}/10 ({label}) — real Fear&Greed {fng_value}."
    ic.log_sweep_memory("agents/sentiment_sweep.py", label, summary, path, tags=["sentiment"])
    print(f"[sentiment_sweep] {label} ({score}/10) — wrote {os.path.relpath(path, ic.ROOT)}")
    return {"score": score, "path": path}


if __name__ == "__main__":
    run()
