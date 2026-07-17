#!/usr/bin/env python3
"""
hack_feed.py - DeFiLlama /hacks fetcher and normalizer.

Fetches hack data via stdlib urllib, filters to last 90 days, normalizes
(date, protocol, chains, technique, loss_usd), emits JSON + markdown to
stdout, and writes dated snapshot under intel/hacks/.

Assumptions:
- API returns list of dicts with keys: date, protocol, chains, technique, amount (USD).
- 'date' is Unix timestamp (seconds). Chains may be list or string.
- No auth or rate limits beyond simple GET.
- intel/hacks/ exists or is creatable by the process.
- Run from repo root; uses only stdlib.
"""

import json
import logging
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

API_URL: str = "https://api.llama.fi/hacks"
OUTPUT_DIR: str = "intel/hacks"
WINDOW_DAYS: int = 90

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def fetch_hacks() -> List[Dict[str, Any]]:
    """Perform single GET and return parsed JSON list. Raises on failure."""
    try:
        with urllib.request.urlopen(API_URL, timeout=30) as resp:
            if resp.status != 200:
                raise urllib.error.HTTPError(API_URL, resp.status, "Bad status", {}, None)
            data = json.loads(resp.read().decode("utf-8"))
            if not isinstance(data, list):
                raise ValueError("Unexpected response shape")
            return data
    except (urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Fetch failed: %s", exc)
        raise


def normalize(record: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and normalize core fields with validation."""
    try:
        ts = int(record.get("date", 0))
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        chains = record.get("chains") or record.get("chain", [])
        if isinstance(chains, str):
            chains = [chains]
        return {
            "date": dt.isoformat(),
            "protocol": str(record.get("protocol", "unknown")),
            "chains": [str(c) for c in chains],
            "technique": str(record.get("technique", "unknown")),
            "loss_usd": int(record.get("amount", 0)),
        }
    except (TypeError, ValueError) as exc:
        logger.warning("Skipping malformed record: %s", exc)
        return {}


def filter_recent(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only records within last 90 days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    return [r for r in records if r and datetime.fromisoformat(r["date"]) >= cutoff]


def to_markdown(records: List[Dict[str, Any]]) -> str:
    """Render sorted markdown table."""
    if not records:
        return "| date | protocol | chains | technique | loss_usd |\n|------|----------|--------|-----------|----------|\n| (none) | | | | |\n"
    lines = ["| date | protocol | chains | technique | loss_usd |",
             "|------|----------|--------|-----------|----------|"]
    for r in sorted(records, key=lambda x: x["date"], reverse=True):
        lines.append(f"| {r['date']} | {r['protocol']} | {', '.join(r['chains'])} | {r['technique']} | {r['loss_usd']:,} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Entry point: fetch, normalize, filter, emit, snapshot."""
    try:
        raw = fetch_hacks()
        normalized = [normalize(r) for r in raw]
        recent = filter_recent(normalized)

        out_json = json.dumps(recent, indent=2, sort_keys=True)
        out_md = to_markdown(recent)

        print(out_json)
        print("\n---\n")
        print(out_md)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        snap = os.path.join(OUTPUT_DIR, f"hacks-{stamp}.json")
        with open(snap, "w", encoding="utf-8") as f:
            f.write(out_json)
        logger.info("Snapshot written: %s (%d records)", snap, len(recent))

    except Exception as exc:
        logger.error("Fatal: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()