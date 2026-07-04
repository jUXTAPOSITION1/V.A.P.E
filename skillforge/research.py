#!/usr/bin/env python3
"""
V.A.P.E. Unified Research Router — one search/scrape API over many MCP providers.

VAPE's research (new bounties, protocol/CVE lookups, incident context) should use
the *best available* provider and degrade gracefully. This router:

  1. Picks the best available search MCP by preference:
       Tavily -> Brave -> (fallback) keyless DuckDuckGo HTML
  2. Picks the best available scrape MCP by preference:
       Firecrawl -> Bright Data -> Apify -> (fallback) keyless MCP `fetch`
  3. Falls back to KEYLESS paths when no provider key is set, so research works
     today and becomes superior the moment a key is added — no code change.

Zero new dependencies. Uses skillforge/mcp_client.py to drive MCP servers and
stdlib urllib for the keyless fallbacks.

CLI:
  python -m skillforge.research search "base defi exploit bounty" [--max 5]
  python -m skillforge.research scrape https://example.com/bounty
  python -m skillforge.research providers        # what's active right now
"""
import os
import re
import sys
import json
import html
import argparse
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from skillforge.mcp_client import call, load_registry, server_status  # noqa: E402

UA = {"User-Agent": "VAPE-PrivateEye/1.0"}

# provider -> (mcp server name, tool, arg-builder(query|url) -> dict)
SEARCH_PROVIDERS = [
    ("tavily", "tavily-search", lambda q, n: {"query": q, "max_results": n}),
    ("brave-search", "brave_web_search", lambda q, n: {"query": q, "count": n}),
]
SCRAPE_PROVIDERS = [
    ("firecrawl", "firecrawl_scrape", lambda u: {"url": u, "formats": ["markdown"]}),
    ("brightdata", "scrape_as_markdown", lambda u: {"url": u}),
    ("apify", "call-actor", lambda u: {"actor": "apify/website-content-crawler",
                                       "input": {"startUrls": [{"url": u}]}}),
]

# ── quota guard ──────────────────────────────────────────────────────────────
# Conservative monthly caps, deliberately well under each provider's real
# free-tier ceiling (Tavily free ~1,000 searches/mo, Firecrawl free ~500
# scrape credits/mo, Bright Data's free trial credits are smaller/less
# predictable) — these keys are shared across every hourly/daily VAPE
# workflow that might call research.py, so the cap has to hold across ALL of
# them combined, not per-workflow. Adjust once real usage patterns are known;
# erring conservative costs nothing (keyless fallback still works), erring
# permissive risks a surprise bill or a dead key mid-month.
MONTHLY_QUOTA = {"tavily": 200, "firecrawl": 100, "brightdata": 20}
# Deliberately NOT under data/cache/ — that directory is gitignored (it's an
# ephemeral TTL response cache), so a quota counter living there would reset
# to zero on every fresh CI checkout and never actually cap anything across
# runs. skillforge/memory/ is real, committed, persistent state, same as
# tools-registry.json — this needs the same durability.
QUOTA_PATH = os.path.join(ROOT, "skillforge", "memory", "research_quota.json")


def _quota_month():
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_quota():
    try:
        with open(QUOTA_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_quota(q):
    os.makedirs(os.path.dirname(QUOTA_PATH), exist_ok=True)
    with open(QUOTA_PATH, "w") as f:
        json.dump(q, f, indent=2)


def _quota_ok(name):
    cap = MONTHLY_QUOTA.get(name)
    if cap is None:
        return True  # uncapped provider (e.g. apify) — no free-tier assumption made for it
    q = _load_quota()
    entry = q.get(name, {})
    return entry.get("month") != _quota_month() or entry.get("count", 0) < cap


def _record_usage(name):
    if name not in MONTHLY_QUOTA:
        return
    q = _load_quota()
    month = _quota_month()
    entry = q.get(name, {})
    if entry.get("month") != month:
        entry = {"month": month, "count": 0}
    entry["count"] = entry.get("count", 0) + 1
    q[name] = entry
    _save_quota(q)


def _available(name):
    reg = load_registry()
    spec = reg.get("servers", {}).get(name)
    return bool(spec) and server_status(name, spec)["available"] and _quota_ok(name)


# ── keyless fallbacks ────────────────────────────────────────────────────────
# Public SearXNG JSON instances tried in order for the keyless fallback.
_SEARX = [
    "https://searx.tiekoetter.com",
    "https://priv.au",
    "https://search.hbubli.cc",
    "https://searxng.site",
]


def _ddg_search(query, n):
    """Keyless search fallback. Best-effort: datacenter IPs are often blocked by
    public engines, which is exactly why the keyed providers (Tavily/Brave/etc.)
    are preferred. Tries SearXNG JSON instances, then DDG HTML, and reports
    `degraded` so callers know to add a provider key for reliable results."""
    # 1) SearXNG JSON (most server-friendly when an instance is up)
    for inst in _SEARX:
        try:
            u = f"{inst}/search?format=json&q=" + urllib.parse.quote(query)
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=12) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            rows = d.get("results", [])[:n]
            if rows:
                return {"provider": "searxng-keyless",
                        "results": [{"title": x.get("title", ""),
                                     "url": x.get("url", ""),
                                     "snippet": x.get("content", "")} for x in rows]}
        except Exception:
            continue
    # 2) DDG HTML scrape
    try:
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8", "replace")
        results = []
        for m in re.finditer(r'result__a"\s+href="([^"]+)"(.*?)</a>', body, re.S):
            href = html.unescape(m.group(1))
            _tx = _TextExtractor()
            _tx.feed(m.group(2))
            title = _tx.get_text()
            if href.startswith("//"):
                href = "https:" + href
            params = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            results.append({"title": html.unescape(title).strip(),
                            "url": params.get("uddg", [href])[0]})
            if len(results) >= n:
                break
        if results:
            return {"provider": "ddg-keyless", "results": results}
    except Exception:
        pass
    return {"provider": "keyless", "degraded": True, "results": [],
            "note": "Public keyless search unavailable from this IP. Set "
                    "TAVILY_API_KEY or BRAVE_API_KEY for reliable research."}


class _TextExtractor(HTMLParser):
    """Strip tags via the stdlib HTML parser instead of a hand-rolled regex —
    a regex like <script.*?</script> can't correctly handle case, attributes
    containing '>', or malformed/nested markup (real pages have all three),
    so it silently leaves stray content in. A real parser gets this right."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if not self._skip_depth:
            self.parts.append(data)

    def get_text(self):
        return " ".join("".join(self.parts).split())


def _fetch_keyless(url):
    """Keyless page fetch via the MCP `fetch` server if present, else urllib."""
    if _available("fetch"):
        res = call("fetch", "fetch", {"url": url})
        if res.get("ok"):
            return {"provider": "mcp-fetch", "content": res.get("data")}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode("utf-8", "replace")
        extractor = _TextExtractor()
        extractor.feed(raw)
        text = extractor.get_text()
        return {"provider": "urllib-keyless", "content": text[:8000]}
    except Exception as e:
        return {"provider": "urllib-keyless", "error": str(e)}


# ── public API ──────────────────────────────────────────────────────────────
def search(query, max_results=5):
    """Best available search provider, keyless fallback. Returns normalized dict."""
    for name, tool, build in SEARCH_PROVIDERS:
        if _available(name):
            res = call(name, tool, build(query, max_results))
            _record_usage(name)  # counts the attempt — the real API call already fired either way
            if res.get("ok"):
                return {"provider": name, "query": query, "raw": res.get("data")}
    return {"query": query, **_ddg_search(query, max_results)}


def scrape(url):
    """Best available scrape provider, keyless fallback."""
    for name, tool, build in SCRAPE_PROVIDERS:
        if _available(name):
            res = call(name, tool, build(url))
            _record_usage(name)
            if res.get("ok"):
                return {"provider": name, "url": url, "raw": res.get("data")}
    return {"url": url, **_fetch_keyless(url)}


def _quota_status(name):
    if name not in MONTHLY_QUOTA:
        return None
    q = _load_quota().get(name, {})
    used = q.get("count", 0) if q.get("month") == _quota_month() else 0
    return {"used": used, "cap": MONTHLY_QUOTA[name]}


def providers():
    """Report which research providers are active vs key-gated vs quota-capped right now."""
    out = {"search": [], "scrape": [], "active_search": None, "active_scrape": None}
    for name, *_ in SEARCH_PROVIDERS:
        av = _available(name)
        out["search"].append({"name": name, "available": av, "quota": _quota_status(name)})
        if av and not out["active_search"]:
            out["active_search"] = name
    out["active_search"] = out["active_search"] or "ddg-keyless"
    for name, *_ in SCRAPE_PROVIDERS:
        av = _available(name)
        out["scrape"].append({"name": name, "available": av, "quota": _quota_status(name)})
        if av and not out["active_scrape"]:
            out["active_scrape"] = name
    out["active_scrape"] = out["active_scrape"] or ("mcp-fetch" if _available("fetch") else "urllib-keyless")
    return out


def main():
    ap = argparse.ArgumentParser(description="VAPE unified research router")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--max", type=int, default=5)
    sc = sub.add_parser("scrape")
    sc.add_argument("url")
    sub.add_parser("providers")
    args = ap.parse_args()
    if args.cmd == "search":
        print(json.dumps(search(args.query, args.max), indent=2)[:4000])
    elif args.cmd == "scrape":
        print(json.dumps(scrape(args.url), indent=2)[:4000])
    elif args.cmd == "providers":
        print(json.dumps(providers(), indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
