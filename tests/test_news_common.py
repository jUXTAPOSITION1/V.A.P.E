"""Tests for agents/news_common.py's deterministic helpers — dedupe, slug,
state tracking, and the Google News RSS parser. Hermetic: any network call
is mocked, no real HTTP.
"""
import json
import urllib.error
from unittest import mock

from agents import news_common as nc


def test_slugify_normalizes_and_truncates():
    assert nc.slugify("Fed Hikes Rates!! Again?") == "fed-hikes-rates-again"
    assert len(nc.slugify("x" * 200, max_len=10)) == 10


def test_slugify_empty_falls_back():
    assert nc.slugify("") == "story"
    assert nc.slugify("!!!") == "story"


def test_dedupe_removes_exact_url_duplicates():
    items = [
        {"title": "Base TVL hits new high", "url": "https://a.example/1"},
        {"title": "Base TVL hits new high", "url": "https://a.example/1"},
    ]
    assert len(nc.dedupe(items)) == 1


def test_dedupe_removes_near_duplicate_titles_different_urls():
    items = [
        {"title": "Fed Cuts Rates by 25 Basis Points", "url": "https://a.example/1"},
        {"title": "Fed cuts rates by 25 basis points", "url": "https://b.example/2"},
    ]
    assert len(nc.dedupe(items)) == 1


def test_dedupe_keeps_genuinely_different_stories():
    items = [
        {"title": "Base TVL hits new high", "url": "https://a.example/1"},
        {"title": "SEC sues major exchange", "url": "https://b.example/2"},
    ]
    assert len(nc.dedupe(items)) == 2


def test_reported_state_roundtrip(tmp_path, monkeypatch):
    state_path = tmp_path / "news_state.json"
    monkeypatch.setattr(nc, "STATE_PATH", str(state_path))

    state = nc.load_state()
    assert state == {"reported_urls": [], "seen": {}}
    assert not nc.is_reported(state, "https://a.example/1")

    nc.mark_reported(state, "https://a.example/1")
    nc.save_state(state)

    reloaded = nc.load_state()
    assert nc.is_reported(reloaded, "https://a.example/1")
    assert not nc.is_reported(reloaded, "https://b.example/2")


def test_mark_reported_is_idempotent():
    state = {"reported_urls": ["https://a.example/1"], "seen": {}}
    nc.mark_reported(state, "https://a.example/1")
    assert state["reported_urls"] == ["https://a.example/1"]


def test_mark_reported_trims_to_max_keep():
    state = {"reported_urls": [f"https://a.example/{i}" for i in range(10)], "seen": {}}
    nc.mark_reported(state, "https://a.example/new", max_keep=5)
    assert len(state["reported_urls"]) == 5
    assert state["reported_urls"][-1] == "https://a.example/new"


_SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>Base network hits record TVL - CoinDesk</title>
  <link>https://news.google.com/rss/articles/abc123</link>
  <pubDate>Mon, 27 Jul 2026 12:00:00 GMT</pubDate>
  <source url="https://coindesk.com">CoinDesk</source>
</item>
<item>
  <title>Untitled entry with no explicit source</title>
  <link>https://news.google.com/rss/articles/def456</link>
  <pubDate>Mon, 27 Jul 2026 11:00:00 GMT</pubDate>
</item>
</channel></rss>"""


def _fake_urlopen(body):
    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return body
    return Resp()


def test_google_news_search_parses_real_shape():
    with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen(_SAMPLE_RSS)):
        out = nc.google_news_search("base blockchain", topic="Base")
    assert len(out) == 2
    assert out[0]["title"] == "Base network hits record TVL"
    assert out[0]["source"] == "CoinDesk"
    assert out[0]["url"] == "https://news.google.com/rss/articles/abc123"
    assert out[0]["topic"] == "Base"
    # No <source> element -> falls back to splitting "Title - Source" if present,
    # else keeps the full title and a generic source label.
    assert out[1]["source"] == "Google News"


def test_google_news_search_network_failure_returns_empty_not_raise():
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        assert nc.google_news_search("anything") == []


def test_google_news_search_malformed_xml_returns_empty():
    with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen(b"not xml")):
        assert nc.google_news_search("anything") == []


def test_strip_html_removes_tags_and_unescapes_entities():
    assert nc._strip_html("<p>Bitcoin &amp; Ethereum <b>rally</b></p>") == "Bitcoin & Ethereum rally"


def test_strip_html_handles_none_and_empty():
    assert nc._strip_html(None) == ""
    assert nc._strip_html("") == ""


_SAMPLE_NATIVE_RSS = b"""<?xml version="1.0"?>
<rss xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<item>
  <title>Bitcoin Rallies Past $100K on ETF Inflows</title>
  <link>https://www.coindesk.com/markets/2026/07/28/bitcoin-rallies</link>
  <pubDate>Tue, 28 Jul 2026 09:00:00 GMT</pubDate>
  <description>&lt;p&gt;Bitcoin surged past $100,000 as spot ETF inflows accelerated.&lt;/p&gt;</description>
  <content:encoded><![CDATA[<p>Bitcoin surged past $100,000 as spot ETF inflows accelerated this week, with BlackRock's IBIT leading net creations.</p>]]></content:encoded>
</item>
<item>
  <title>No Link Item</title>
  <pubDate>Tue, 28 Jul 2026 08:00:00 GMT</pubDate>
</item>
</channel></rss>"""


def test_native_rss_feed_parses_real_shape_and_prefers_content_encoded():
    with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen(_SAMPLE_NATIVE_RSS)):
        out = nc.native_rss_feed("https://www.coindesk.com/arc/outboundfeeds/rss/", "CoinDesk", "crypto-markets")
    assert len(out) == 1  # the linkless second item is skipped
    item = out[0]
    assert item["title"] == "Bitcoin Rallies Past $100K on ETF Inflows"
    assert item["url"] == "https://www.coindesk.com/markets/2026/07/28/bitcoin-rallies"
    assert item["source"] == "CoinDesk"
    assert item["topic"] == "crypto-markets"
    # content:encoded (the fuller field) wins over the shorter description
    assert "BlackRock's IBIT" in item["snippet"]
    assert "<p>" not in item["snippet"]


def test_native_rss_feed_network_failure_returns_empty_not_raise():
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        assert nc.native_rss_feed("https://example.com/feed", "Example", "crypto-markets") == []


def test_native_rss_feed_malformed_xml_returns_empty():
    with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen(b"not xml")):
        assert nc.native_rss_feed("https://example.com/feed", "Example", "crypto-markets") == []


def test_coingecko_news_best_effort_empty_on_failure():
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            "url", 404, "not found", {}, None)):
        assert nc.coingecko_news() == []


def test_coingecko_news_parses_real_shape():
    body = json.dumps({"data": [
        {"title": "BTC rallies", "url": "https://x.example/1", "news_site": "X News",
         "updated_at": "2026-07-27T00:00:00Z", "thumb_2x": "https://x.example/img.jpg"},
        {"title": None, "url": None},  # malformed entry, must be skipped not crash
    ]}).encode()
    with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen(body)):
        out = nc.coingecko_news()
    assert len(out) == 1
    assert out[0]["title"] == "BTC rallies"
    assert out[0]["image"] == "https://x.example/img.jpg"


def test_extract_og_image_rejects_non_public_url():
    assert nc.extract_og_image("http://169.254.169.254/latest/meta-data/") is None


def test_extract_og_image_parses_meta_tag():
    html_body = b'<html><head><meta property="og:image" content="https://cdn.example/pic.jpg"></head></html>'
    with mock.patch("agents.news_common._validate_fetch_url", return_value=True), \
         mock.patch("urllib.request.build_opener") as build_opener:
        opener = build_opener.return_value
        opener.open.return_value.__enter__.return_value.read.return_value = html_body
        img = nc.extract_og_image("https://example.com/story")
    assert img == "https://cdn.example/pic.jpg"


def _make_test_jpeg(path, size=(400, 300), color=(30, 60, 90)):
    from PIL import Image
    Image.new("RGB", size, color).save(path, "JPEG")


def test_brand_image_stamps_local_source_and_writes_expected_path(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "NEWS_IMAGES_DIR", str(tmp_path / "news-images"))
    src_dir = tmp_path / "docs"
    src_dir.mkdir()
    _make_test_jpeg(src_dir / "source.jpg")
    # brand_image() reads local (non-http) sources relative to docs/ under
    # ROOT -- point ROOT-derived docs/ lookup at our tmp dir instead.
    monkeypatch.setattr(nc, "_fetch_image_bytes", lambda source: (src_dir / "source.jpg").read_bytes())

    out = nc.brand_image("source.jpg", "my-slug")
    assert out == "assets/news-images/my-slug.jpg"

    written = tmp_path / "news-images" / "my-slug.jpg"
    assert written.exists()

    from PIL import Image
    img = Image.open(written)
    assert img.size == (1200, 675)


def test_brand_image_returns_none_when_source_unfetchable(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "NEWS_IMAGES_DIR", str(tmp_path / "news-images"))
    monkeypatch.setattr(nc, "_fetch_image_bytes", lambda source: None)
    assert nc.brand_image("https://example.com/missing.jpg", "slug") is None


def test_brand_image_returns_none_on_corrupt_image_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "NEWS_IMAGES_DIR", str(tmp_path / "news-images"))
    monkeypatch.setattr(nc, "_fetch_image_bytes", lambda source: b"not a real image")
    assert nc.brand_image("https://example.com/broken.jpg", "slug") is None


def test_fetch_image_bytes_rejects_non_public_url():
    assert nc._fetch_image_bytes("http://169.254.169.254/latest/meta-data/") is None


def test_fetch_image_bytes_passes_through_raw_bytes_unchanged():
    """The AI-generation tier hands brand_image() already-decoded image
    bytes directly (llm.ask_gemini_image()'s return value) -- no URL/path
    fetch needed, unlike the real-photo/local-asset cases."""
    raw = b"\x89PNG-already-decoded-bytes"
    assert nc._fetch_image_bytes(raw) == raw


def test_brand_image_stamps_raw_bytes_source(tmp_path, monkeypatch):
    """Confirms the AI-image-generation tier can go straight from
    ask_gemini_image()'s in-memory bytes to a branded file, with no
    intermediate fetch/save-then-refetch round trip."""
    monkeypatch.setattr(nc, "NEWS_IMAGES_DIR", str(tmp_path / "news-images"))
    import io as _io
    from PIL import Image
    buf = _io.BytesIO()
    Image.new("RGB", (500, 400), (10, 20, 30)).save(buf, "PNG")

    out = nc.brand_image(buf.getvalue(), "ai-slug")
    assert out == "assets/news-images/ai-slug.jpg"
    assert (tmp_path / "news-images" / "ai-slug.jpg").exists()


def test_scrape_article_text_normalizes_firecrawl_shape(monkeypatch):
    import agents.news_common as nc_mod

    def fake_scrape(url):
        return {"raw": {"markdown": "  Real   article   body   text.  "}}

    monkeypatch.setattr("skillforge.research.scrape", fake_scrape)
    assert nc_mod.scrape_article_text("https://example.com/story") == "Real article body text."


def test_scrape_article_text_normalizes_keyless_fetch_shape(monkeypatch):
    def fake_scrape(url):
        return {"content": "Keyless fetch extracted body text here."}

    monkeypatch.setattr("skillforge.research.scrape", fake_scrape)
    assert nc.scrape_article_text("https://example.com/story") == "Keyless fetch extracted body text here."


def test_scrape_article_text_truncates_to_max_len(monkeypatch):
    def fake_scrape(url):
        return {"content": "word " * 2000}

    monkeypatch.setattr("skillforge.research.scrape", fake_scrape)
    result = nc.scrape_article_text("https://example.com/story", max_len=50)
    assert len(result) == 50


def test_scrape_article_text_returns_none_on_failure(monkeypatch):
    def fake_scrape(url):
        raise RuntimeError("network down")

    monkeypatch.setattr("skillforge.research.scrape", fake_scrape)
    assert nc.scrape_article_text("https://example.com/story") is None


def test_scrape_article_text_returns_none_when_content_empty(monkeypatch):
    monkeypatch.setattr("skillforge.research.scrape", lambda url: {"content": "   "})
    assert nc.scrape_article_text("https://example.com/story") is None
