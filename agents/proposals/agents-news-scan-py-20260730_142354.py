"""
VAPE self-improvement proposal — generated 2026-07-30T14:23:54.414691+00:00
Target: agents/news_scan.py
Issue: pyflakes: 'datetime.timezone' imported but unused (line 17)
Security review: review: 'open(' present (advisory); review: 'import os' present (advisory)

This is a PROPOSAL, not applied automatically. A human reviews this PR
and decides whether/how to merge it into the actual target file.
"""

"""
VAPE News Scan — discovery half of the news-intel pipeline. Gathers real
headlines (Google News search, CoinGecko's news feed, one bounded general
web search — see agents/news_common.py's module docstring for the full
source rundown) and writes data/news-feed.json, the breaking-headlines
ticker the site renders above the x402 ledger.

Deliberately does no LLM work and no per-story deep research — that's
agents/news_reporter.py's job, run as a separate workflow step right after
this one so it can read this script's output instead of re-gathering.

Usage: python agents/news_scan.py
"""
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import news_common as nc  # noqa: E402


def _parse_pubdate(s: str) -> str:
    """RFC-822 (Google News) or ISO-ish -> comparable sort key; unparseable
    or missing dates sort last rather than crashing the sort."""
    if not s:
        return ""
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(s, fmt).isoformat()
        except Exception:
            continue
    return s


def run() -> None:
    headlines = nc.gather_headlines()
    for h in headlines:
        h["published_sort"] = _parse_pubdate(h.get("published"))
    # Recency first, then a STABLE re-sort that groups crypto/blockchain
    # topics ahead of macro/stocks -- editorial rule: crypto/blockchain leads,
    # especially breaking news, always occupies slot 1. Stability preserves
    # each group's own recency order from the first sort.
    headlines.sort(key=lambda h: h["published_sort"], reverse=True)
    headlines.sort(key=lambda h: 0 if nc.is_crypto_topic(h.get("topic")) else 1)

    state = nc.load_state()
    seen = state.setdefault("seen", {})
    now = nc.now_iso()
    for h in headlines:
        seen.setdefault(h["url"], now)
    # Trim seen ledger so it doesn't grow unbounded across months of runs.
    if len(seen) > 2000:
        for url in list(seen)[: len(seen) - 2000]:
            del seen[url]
    nc.save_state(state)

    ticker = headlines[:60]
    os.makedirs(os.path.dirname(nc.FEED_PATH), exist_ok=True)
    with open(nc.FEED_PATH, "w") as f:
        json.dump({
            "generated": now,
            "count": len(ticker),
            "headlines": [
                {
                    "title": h["title"],
                    "url": h["url"],
                    "source": h.get("source"),
                    "published": h.get("published"),
                    "topic": nc.TOPIC_LABELS.get(h.get("topic"), h.get("topic") or "General"),
                    "crypto": nc.is_crypto_topic(h.get("topic")),
                }
                for h in ticker
            ],
        }, f, indent=2)
    print(f"[news_scan] gathered {len(headlines)} deduped headlines, wrote {len(ticker)} to "
          f"{os.path.relpath(nc.FEED_PATH, nc.ROOT)}")
    # Removed 'return tic' since 'tic' is not defined


# Removed unused import 'from datetime import timezone'
