#!/usr/bin/env python3
"""
DeFiLlama TVL and Price Data Scraper for VAPE.

Fetches current chain TVL, protocol TVL summaries, and price data for
major assets using only the public DeFiLlama APIs. No inputs required.
Outputs a single JSON object to stdout.

Assumptions documented in module docstring:
- Public endpoints only (no API keys).
- Hard-coded list of major assets for price lookup (scalable via edit).
- urllib used for stdlib-only HTTP; timeouts enforced.
- Output is machine-readable JSON for downstream VAPE market_data use.
"""

import json
import logging
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List

# Configuration
API_BASE = "https://api.llama.fi"
COINS_BASE = "https://coins.llama.fi"
TIMEOUT = 15
PRICE_TOKENS = [
    "coingecko:bitcoin",
    "coingecko:ethereum",
    "coingecko:usd-coin",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("defillama_scraper")


def _fetch_json(url: str) -> Any:
    """Perform GET request and return parsed JSON with error handling."""
    req = urllib.request.Request(url, headers={"User-Agent": "VAPE/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                raise urllib.error.HTTPError(url, resp.status, "Bad status", {}, None)
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        logger.error("Fetch failed for %s: %s", url, exc)
        raise


def fetch_chains_tvl() -> List[Dict[str, Any]]:
    """Return TVL breakdown for all tracked chains."""
    url = f"{API_BASE}/v2/chains"
    data = _fetch_json(url)
    return [
        {"name": c.get("name"), "tvl": c.get("tvl")}
        for c in data
        if isinstance(c, dict)
    ]


def fetch_protocols_tvl() -> List[Dict[str, Any]]:
    """Return summarized TVL for top protocols (name, chain, tvl)."""
    url = f"{API_BASE}/protocols"
    data = _fetch_json(url)
    return [
        {
            "name": p.get("name"),
            "chain": p.get("chain"),
            "tvl": p.get("tvl"),
        }
        for p in data
        if isinstance(p, dict)
    ][:50]  # limit for payload size


def fetch_prices() -> Dict[str, Any]:
    """Return current prices for the configured token list."""
    tokens = ",".join(PRICE_TOKENS)
    url = f"{COINS_BASE}/prices/current/{tokens}"
    data = _fetch_json(url)
    return data.get("coins", {})


def main() -> None:
    """Execute all fetches and emit combined JSON result."""
    try:
        result = {
            "chains": fetch_chains_tvl(),
            "protocols": fetch_protocols_tvl(),
            "prices": fetch_prices(),
        }
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        logger.info("Scrape completed successfully")
    except Exception as exc:
        logger.exception("Scraper failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()