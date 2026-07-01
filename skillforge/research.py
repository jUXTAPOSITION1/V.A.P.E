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


def _available(name):
    reg = load_registry()
    spec = reg.get("servers", {}).get(name)
    return bool(spec) and server_status(name, spec)["available"]


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
                return {"provider": f"searxng-keyless",
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
            title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
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
        text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        return {"provider": "urllib-keyless", "content": text[:8000]}
    except Exception as e:
        return {"provider": "urllib-keyless", "error": str(e)}


# ── public API ──────────────────────────────────────────────────────────────
def search(query, max_results=5):
    """Best available search provider, keyless fallback. Returns normalized dict."""
    for name, tool, build in SEARCH_PROVIDERS:
        if _available(name):
            res = call(name, tool, build(query, max_results))
            if res.get("ok"):
                return {"provider": name, "query": query, "raw": res.get("data")}
    return {"query": query, **_ddg_search(query, max_results)}


def scrape(url):
    """Best available scrape provider, keyless fallback."""
    for name, tool, build in SCRAPE_PROVIDERS:
        if _available(name):
            res = call(name, tool, build(url))
            if res.get("ok"):
                return {"provider": name, "url": url, "raw": res.get("data")}
    return {"url": url, **_fetch_keyless(url)}


def providers():
    """Report which research providers are active vs key-gated right now."""
    out = {"search": [], "scrape": [], "active_search": None, "active_scrape": None}
    for name, *_ in SEARCH_PROVIDERS:
        av = _available(name)
        out["search"].append({"name": name, "available": av})
        if av and not out["active_search"]:
            out["active_search"] = name
    out["active_search"] = out["active_search"] or "ddg-keyless"
    for name, *_ in SCRAPE_PROVIDERS:
        av = _available(name)
        out["scrape"].append({"name": name, "available": av})
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
