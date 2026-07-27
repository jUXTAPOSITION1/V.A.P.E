"""
Shared helpers for VAPE's news-intel pipeline (agents/news_scan.py discovers
headlines, agents/news_reporter.py turns the best of them into VAPE's own
investigative reports). Same design rule as agents/intel_common.py: real,
fetched data first, LLM only for narrative synthesis — never invent a
headline, source, or quote.

Four source lanes, all keyless (no vendor account needed to ship a working
v1):
  1. Google News RSS search (news.google.com/rss/search) — no API key, no
     quota, works for any query string. This is the main discovery lane.
  2. CoinGecko's public news endpoint — best-effort only. It isn't part of
     CoinGecko's documented free API surface and may 404/410/402 depending
     on current API tier; every caller here must treat empty/error as a
     normal, silent "nothing this cycle," never a failure.
  3. General web search via skillforge.research.search() (Tavily/Brave/DDG-
     keyless, already quota-tracked by that module) — one bounded call per
     discovery cycle, matching every other sweep's "one bounded search"
     convention.
  4. X/Twitter — deliberately NOT implemented. There is no working keyless
     or already-configured path to it anywhere in this repo (xAI's Live
     Search, the one thing that ever gave an LLM call here live X
     grounding, was deprecated — HTTP 410 in production, 2026-07). Left as
     a documented gap rather than a fake/broken integration; wire it in
     once a real API key or replacement method exists.
"""
import io
import os
import re
import sys
import json
import html
import difflib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from skillforge.research import _validate_fetch_url, _SSRFSafeRedirectHandler  # noqa: E402 -- reuse the SSRF guard research.py already built, rather than re-deriving it

UA = {"User-Agent": "VAPE-NewsDesk/1.0"}

NEWS_DIR = os.path.join(ROOT, "intel", "news")
STATE_PATH = os.path.join(ROOT, "skillforge", "memory", "news_state.json")
FEED_PATH = os.path.join(ROOT, "data", "news-feed.json")
NEWS_IMAGES_DIR = os.path.join(ROOT, "docs", "assets", "news-images")
LOGO_PATH = os.path.join(ROOT, "docs", "assets", "logo-v-256.png")
BRAND_WORDMARK = "THE V.A.P.E REPORT"

# (topic key, Google News search query, display label) — covers exactly the
# beats the user asked for: blockchain/crypto/Base, security/exploits,
# finance/macro/US stocks. Kept short and concrete (Google News' own search
# ranks tighter queries better than a long OR-chain).
TOPICS = [
    ("base", "Base blockchain OR Coinbase Base network", "Base"),
    ("crypto-markets", "crypto market bitcoin ethereum", "Crypto Markets"),
    ("defi-security", "DeFi exploit hack crypto security breach", "Security"),
    ("stablecoins", "stablecoin regulation USDC USDT", "Stablecoins"),
    ("regulation", "SEC crypto regulation bill", "Regulation"),
    ("ai-agents", "AI agent crypto onchain autonomous", "AI Agents"),
    ("macro", "Federal Reserve interest rate inflation markets", "Macro"),
    ("stocks", "US stock market Wall Street earnings", "US Stocks"),
]
TOPIC_LABELS = {key: label for key, _query, label in TOPICS}
TOPIC_LABELS["web-search"] = "Crypto Wire"

# By explicit editorial rule: this is a crypto/blockchain-first news
# operation -- every non-crypto beat (macro, US stocks) exists only for
# context around the crypto story, never ahead of it. See
# news_scan.py::_crypto_first_sort() and news_reporter.py::_pick_candidates()
# for where this is enforced.
NON_CRYPTO_TOPICS = {"macro", "stocks"}


def is_crypto_topic(topic_key):
    return topic_key not in NON_CRYPTO_TOPICS


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slugify(title, max_len=60):
    s = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return s[:max_len] or "story"


def _norm_title(title):
    return re.sub(r"[^a-z0-9 ]", "", (title or "").lower()).strip()


def google_news_search(query, max_results=8, topic=None):
    """Keyless Google News RSS search — no API key, no rate-limit account to
    exhaust. Returns [] (never raises) on any network/parse failure; this
    feed is expected to be flaky from a datacenter IP, same caveat research.py
    documents for its own keyless fallbacks."""
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(query) +
           "&hl=en-US&gl=US&ceid=US:en")
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
        root = ET.fromstring(raw)
    except Exception:
        return []
    out = []
    for item in root.findall("./channel/item")[:max_results]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None and source_el.text else None
        # Google News RSS titles are always "Headline - Source Name", even when
        # the <source> element is also present -- strip that redundant suffix
        # rather than leaving it duplicated in the displayed headline.
        if source and title.endswith(f" - {source}"):
            title = title[: -len(f" - {source}")]
        elif not source and " - " in title:
            title, _, source = title.rpartition(" - ")
        title = html.unescape(title).strip()
        if not title or not link:
            continue
        out.append({
            "title": title,
            "url": link,
            "source": source or "Google News",
            "published": pub,
            "topic": topic,
        })
    return out


def coingecko_news(max_results=10):
    """Best-effort only — see module docstring. Any non-200/parse failure
    silently contributes nothing; never treated as an error by callers."""
    try:
        req = urllib.request.Request("https://api.coingecko.com/api/v3/news", headers=UA)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except Exception:
        return []
    items = data.get("data") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    out = []
    for it in items[:max_results]:
        if not isinstance(it, dict):
            continue
        title = it.get("title") or it.get("name")
        url_ = it.get("url") or it.get("news_site_url") or it.get("article_url")
        if not title or not url_:
            continue
        out.append({
            "title": str(title).strip(),
            "url": url_,
            "source": it.get("news_site") or it.get("author") or "CoinGecko",
            "published": it.get("updated_at") or it.get("created_at") or "",
            "image": it.get("thumb_2x") or it.get("thumb") or it.get("image"),
            "topic": "crypto-markets",
        })
    return out


def web_headline_search(query="breaking crypto blockchain security news today", max_results=8):
    """One bounded skillforge.research.search() call, normalized to the same
    shape as the other lanes. This is the "general web search" lane the
    ticker draws from; report writing uses its own separate bounded search
    (agents/news_reporter.py) for corroboration, not this one."""
    try:
        from agents import intel_common as ic
    except Exception:
        return []
    res = ic.web_search_snippets(query, max_results=max_results)
    if not res.get("available"):
        return []
    out = []
    for r in res.get("results", []):
        if not r.get("title") or not r.get("url"):
            continue
        out.append({
            "title": r["title"],
            "url": r["url"],
            "source": urllib.parse.urlparse(r["url"]).hostname or "web",
            "published": "",
            "snippet": r.get("snippet", ""),
            "topic": "web-search",  # query is crypto-focused -- see is_crypto_topic()
        })
    return out


def dedupe(items):
    """De-dupes by exact URL first, then by fuzzy title similarity (0.85+
    ratio) — the same story is frequently syndicated verbatim by multiple
    outlets with a slightly different headline, and Google News itself
    already returns several near-duplicate entries per real event."""
    seen_urls = set()
    kept = []
    for it in items:
        u = it.get("url")
        if not u or u in seen_urls:
            continue
        norm = _norm_title(it.get("title"))
        if any(difflib.SequenceMatcher(None, norm, _norm_title(k.get("title"))).ratio() > 0.85 for k in kept):
            seen_urls.add(u)
            continue
        seen_urls.add(u)
        kept.append(it)
    return kept


def gather_headlines():
    """Combines all discovery lanes into one deduped list. Called by
    news_scan.py only — news_reporter.py reads its output (data/news-feed.json)
    instead of re-gathering, so a single cycle makes exactly one round of
    external calls."""
    items = []
    for key, query, _label in TOPICS:
        items.extend(google_news_search(query, max_results=6, topic=key))
    items.extend(coingecko_news(max_results=10))
    items.extend(web_headline_search())
    return dedupe(items)


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {"reported_urls": [], "seen": {}}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def is_reported(state, url):
    return url in set(state.get("reported_urls", []))


def mark_reported(state, url, max_keep=500):
    reported = state.setdefault("reported_urls", [])
    if url not in reported:
        reported.append(url)
    if len(reported) > max_keep:
        del reported[: len(reported) - max_keep]


def extract_og_image(url):
    """Best-effort og:image scrape from the source article's own page, reusing
    research.py's SSRF-safe fetch machinery rather than re-deriving URL/
    redirect validation. Returns None (never raises) if the page can't be
    fetched or has no og:image — callers must treat a missing image as
    "no real source image available," not an error."""
    if not _validate_fetch_url(url):
        return None
    try:
        opener = urllib.request.build_opener(_SSRFSafeRedirectHandler)
        req = urllib.request.Request(url, headers=UA)
        with opener.open(req, timeout=12) as r:
            raw = r.read(300000).decode("utf-8", "replace")
    except Exception:
        return None
    m = (re.search(r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', raw, re.I)
         or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', raw, re.I))
    if not m:
        return None
    img = html.unescape(m.group(1)).strip()
    return img if img.startswith("http") else None


def write_news_report(slug, body_md):
    """intel/news/news-<YYYY-MM-DD>-<slug>.md — a sibling convention to
    intel_common.write_report(), kept in its own directory since news
    stories (per-story, many/day) are a different shape from the hourly
    category sweeps in intel/reports/."""
    os.makedirs(NEWS_DIR, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(NEWS_DIR, f"news-{date}-{slug}.md")
    if os.path.exists(path):
        path = os.path.join(NEWS_DIR, f"news-{date}-{slug}-{datetime.now(timezone.utc).strftime('%H%M%S')}.md")
    with open(path, "w") as f:
        f.write(body_md)
    return path


def _fetch_image_bytes(source):
    """Real bytes for `source` — a remote http(s) URL (SSRF-guarded exactly
    like extract_og_image's fetch, reusing the same validated opener) or a
    docs/-relative local asset path (e.g. FALLBACK_IMAGE). Returns None
    (never raises) on any failure."""
    if source.startswith("http"):
        if not _validate_fetch_url(source):
            return None
        try:
            opener = urllib.request.build_opener(_SSRFSafeRedirectHandler)
            req = urllib.request.Request(source, headers=UA)
            with opener.open(req, timeout=20) as r:
                return r.read()
        except Exception:
            return None
    try:
        with open(os.path.join(ROOT, "docs", source), "rb") as f:
            return f.read()
    except Exception:
        return None


def brand_image(source, slug):
    """Every VAPE Wire story needs to read as VAPE Wire's own on sight, the
    same way a real wire service stamps its logo on a photo before
    distribution — this downloads/reads `source` (a real photo URL, an
    AI-generated image URL, or a local fallback asset path), crops it to a
    consistent 16:9 frame, and stamps VAPE's real V-mark + wordmark into a
    bottom scrim. Writes the branded JPEG to docs/assets/news-images/
    <slug>.jpg and returns the site-relative path ("assets/news-images/
    <slug>.jpg") the card <img> should use.

    Returns None (never raises) if Pillow isn't installed, the source can't
    be fetched, or the composite fails for any reason — callers must fall
    back to the unbranded source/logo, never break the pipeline over a
    cosmetic step."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageOps
    except ImportError:
        return None
    raw = _fetch_image_bytes(source)
    if not raw:
        return None
    try:
        base = Image.open(io.BytesIO(raw)).convert("RGBA")
        base = ImageOps.fit(base, (1200, 675), Image.LANCZOS)

        scrim_h = 110
        scrim = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(scrim)
        top = base.size[1] - scrim_h
        for y in range(top, base.size[1]):
            alpha = int(190 * (y - top) / scrim_h)
            draw.line([(0, y), (base.size[0], y)], fill=(0, 0, 0, alpha))
        branded = Image.alpha_composite(base, scrim)

        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_size = 44
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        logo_pos = (24, base.size[1] - logo_size - 24)
        branded.paste(logo, logo_pos, logo)

        # load_default(size=...) is Pillow's built-in scalable font (>=10.1,
        # pinned in agents/requirements.txt) -- no external .ttf to vendor
        # or fail to find on a fresh CI runner.
        font = ImageFont.load_default(size=24)
        text_pos = (logo_pos[0] + logo_size + 14, logo_pos[1] + 9)
        ImageDraw.Draw(branded).text(text_pos, BRAND_WORDMARK, font=font, fill=(255, 255, 255, 235))

        os.makedirs(NEWS_IMAGES_DIR, exist_ok=True)
        out_path = os.path.join(NEWS_IMAGES_DIR, f"{slug}.jpg")
        branded.convert("RGB").save(out_path, "JPEG", quality=85)
        return f"assets/news-images/{slug}.jpg"
    except Exception:
        return None
