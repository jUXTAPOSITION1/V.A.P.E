"""Tests for agents/web_sourcer.py. Hermetic: no real network, robots.txt
fetches, LLM calls, or skillforge.research calls — everything that touches
the outside world is monkeypatched/mocked.
"""
import json
from unittest import mock

from agents import web_sourcer as ws


# ── entity extraction ───────────────────────────────────────────────────────
def test_default_entity_extractor_finds_all_four_classes():
    text = ("Contract 0x1234567890123456789012345678901234567890 exploited via "
            "tx 0x" + "ab" * 32 + " — see CVE-2026-12345. $USDC drained.")
    entities = ws.default_entity_extractor(text)
    assert "0x1234567890123456789012345678901234567890" in entities
    assert "0x" + "ab" * 32 in entities
    assert "CVE-2026-12345" in entities
    assert "$USDC" in entities


def test_default_entity_extractor_empty_input():
    assert ws.default_entity_extractor("") == []
    assert ws.default_entity_extractor(None) == []


def test_default_entity_extractor_no_matches():
    assert ws.default_entity_extractor("just an ordinary sentence") == []


# ── robots.txt gating ────────────────────────────────────────────────────────
def test_allowed_by_robots_fails_open_on_unreachable_robots_txt(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    with mock.patch("urllib.robotparser.RobotFileParser.read", side_effect=Exception("network down")):
        assert sourcer.allowed_by_robots("https://example.com/page") is True


def test_allowed_by_robots_respects_real_disallow(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))

    def fake_read(self):
        self.parse(["User-agent: *", "Disallow: /private/"])

    with mock.patch("urllib.robotparser.RobotFileParser.read", fake_read):
        assert sourcer.allowed_by_robots("https://example.com/private/secret") is False
        assert sourcer.allowed_by_robots("https://example.com/public/page") is True


def test_allowed_by_robots_no_domain_is_disallowed(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    assert sourcer.allowed_by_robots("not-a-url") is False


# ── persistent cache + cross-run dedup ──────────────────────────────────────
def test_fetch_page_skips_already_seen_url(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    sourcer.seen_urls.add("https://example.com/already-done")
    assert sourcer.fetch_page("https://example.com/already-done") is None


def test_fetch_page_skips_robots_disallowed(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    with mock.patch.object(sourcer, "allowed_by_robots", return_value=False):
        assert sourcer.fetch_page("https://example.com/blocked") is None


def test_fetch_page_uses_cache_on_second_call(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    fake_result = {"provider": "firecrawl", "raw": {"content": "real page content here"}}
    with mock.patch("skillforge.research.scrape", return_value=fake_result) as mock_scrape:
        lead1 = sourcer.fetch_page("https://example.com/page")
        assert lead1["content"] == "real page content here"
        assert mock_scrape.call_count == 1

        # Second sourcer (fresh seen_urls in-memory, same cache dir) still hits
        # the on-disk cache, not a network call.
        sourcer2 = ws.WebSourcer(cache_dir=str(tmp_path))
        lead2 = sourcer2.fetch_page("https://example.com/page")
        assert lead2["content"] == "real page content here"
        assert mock_scrape.call_count == 1  # not called again


def test_fetch_page_expired_cache_refetches(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path), cache_ttl=0)
    fake_result = {"provider": "firecrawl", "raw": {"content": "first version"}}
    with mock.patch("skillforge.research.scrape", return_value=fake_result):
        sourcer.fetch_page("https://example.com/page")

    fake_result2 = {"provider": "firecrawl", "raw": {"content": "second version"}}
    sourcer2 = ws.WebSourcer(cache_dir=str(tmp_path), cache_ttl=0)
    with mock.patch("skillforge.research.scrape", return_value=fake_result2) as mock_scrape2:
        lead = sourcer2.fetch_page("https://example.com/page")
        assert lead["content"] == "second version"
        assert mock_scrape2.call_count == 1


def test_fetch_page_returns_none_on_empty_content(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    with mock.patch("skillforge.research.scrape", return_value={"provider": "urllib-keyless", "content": ""}):
        assert sourcer.fetch_page("https://example.com/blank") is None


def test_save_seen_persists_across_instances(tmp_path):
    cache_dir = str(tmp_path)
    sourcer1 = ws.WebSourcer(cache_dir=cache_dir)
    sourcer1.seen_urls.add("https://example.com/a")
    sourcer1.save_seen()

    sourcer2 = ws.WebSourcer(cache_dir=cache_dir)
    assert "https://example.com/a" in sourcer2.seen_urls


# ── link extraction ──────────────────────────────────────────────────────────
def test_extract_links_from_html(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    html = '<p>See <a href="/relative/page">this</a> and <a href="https://other.com/x">that</a>.</p>'
    links = sourcer._extract_links(html, "https://example.com/base")
    assert "https://example.com/relative/page" in links
    assert "https://other.com/x" in links


def test_extract_links_from_markdown(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    md = "Check out [this report](https://example.com/report) for details."
    links = sourcer._extract_links(md, "https://example.com/")
    assert "https://example.com/report" in links


# ── LLM link scoring ─────────────────────────────────────────────────────────
def test_score_links_returns_all_when_under_top_n(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    links = ["https://a.com", "https://b.com"]
    assert sourcer._score_links("query", links, top_n=5) == links


def test_score_links_parses_llm_response(tmp_path):
    calls = []

    def fake_llm(system, user, **kw):
        calls.append((system, user))
        return "2, 0, 5", "test-provider"

    sourcer = ws.WebSourcer(cache_dir=str(tmp_path), llm_call=fake_llm)
    links = [f"https://example.com/{i}" for i in range(6)]
    scored = sourcer._score_links("query", links, top_n=3)
    assert scored == ["https://example.com/2", "https://example.com/0", "https://example.com/5"]
    assert len(calls) == 1


def test_score_links_degrades_on_llm_unavailable(tmp_path):
    def fake_llm(system, user, **kw):
        return "[llm unavailable: no provider]", None

    sourcer = ws.WebSourcer(cache_dir=str(tmp_path), llm_call=fake_llm)
    links = [f"https://example.com/{i}" for i in range(6)]
    scored = sourcer._score_links("query", links, top_n=3)
    assert scored == links[:3]  # degrades to original order


def test_score_links_degrades_on_llm_exception(tmp_path):
    def fake_llm(system, user, **kw):
        raise RuntimeError("network error")

    sourcer = ws.WebSourcer(cache_dir=str(tmp_path), llm_call=fake_llm)
    links = [f"https://example.com/{i}" for i in range(6)]
    scored = sourcer._score_links("query", links, top_n=3)
    assert scored == links[:3]


# ── sources.yaml integration ─────────────────────────────────────────────────
def test_load_sources_from_yaml_real_file(tmp_path):
    yaml_content = """
sources:
  - name: Test Outlet
    rss_url: https://test.example/feed
    priority: 1
    topics: [crypto-markets]
  - name: Other Outlet
    base_url: https://other.example/news
    priority: 2
    topics: [security]
"""
    yaml_path = tmp_path / "sources.yaml"
    yaml_path.write_text(yaml_content)
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))

    all_sources = sourcer.load_sources_from_yaml(yaml_path=str(yaml_path))
    assert set(all_sources) == {"https://test.example/feed", "https://other.example/news"}

    filtered = sourcer.load_sources_from_yaml(yaml_path=str(yaml_path), topic="security")
    assert filtered == ["https://other.example/news"]

    empty = sourcer.load_sources_from_yaml(yaml_path=str(yaml_path), topic="nonexistent")
    assert empty == []


def test_load_sources_from_yaml_missing_file(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    assert sourcer.load_sources_from_yaml(yaml_path=str(tmp_path / "nope.yaml")) == []


def test_load_sources_from_yaml_real_config_file_parses():
    """The real config/sources.yaml this repo ships must actually parse and
    contain at least one real, non-empty source URL — catches a syntax typo
    or an accidental empty-file regression."""
    sourcer = ws.WebSourcer()
    sources = sourcer.load_sources_from_yaml()
    assert len(sources) > 0
    assert all(s.startswith("http") for s in sources)


# ── process_query / intelligent_crawl (search + fetch orchestration) ───────
def test_process_query_scrapes_search_results(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    fake_search = {"available": True, "provider": "tavily",
                   "results": [{"title": "A", "url": "https://a.example/1", "snippet": ""},
                               {"title": "B", "url": "https://b.example/2", "snippet": ""}]}
    fake_scrape = {"provider": "firecrawl", "raw": {"content": "real content"}}
    with mock.patch.object(ws, "web_search_snippets", return_value=fake_search), \
         mock.patch("skillforge.research.scrape", return_value=fake_scrape):
        leads = sourcer.process_query("test query", max_pages=2)
    assert len(leads) == 2
    assert {l["url"] for l in leads} == {"https://a.example/1", "https://b.example/2"}


def test_process_query_no_search_results(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    with mock.patch.object(ws, "web_search_snippets", return_value={"available": True, "results": []}):
        leads = sourcer.process_query("nothing found")
    assert leads == []


def test_intelligent_crawl_respects_max_depth_one(tmp_path):
    """depth=1 should behave like process_query — no link-following, no LLM call."""
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    fake_search = {"available": True, "results": [{"title": "A", "url": "https://a.example/1", "snippet": ""}]}
    fake_scrape = {"provider": "firecrawl", "raw": {"content": "content with <a href='https://a.example/2'>link</a>"}}
    with mock.patch.object(ws, "web_search_snippets", return_value=fake_search), \
         mock.patch("skillforge.research.scrape", return_value=fake_scrape) as mock_scrape:
        leads = sourcer.intelligent_crawl("query", max_depth=1, max_pages_per_level=5)
    assert len(leads) == 1
    assert mock_scrape.call_count == 1  # never followed the embedded link


def test_intelligent_crawl_follows_links_at_depth_two(tmp_path):
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path))
    fake_search = {"available": True, "results": [{"title": "A", "url": "https://a.example/1", "snippet": ""}]}

    def fake_scrape(url):
        if url == "https://a.example/1":
            return {"provider": "firecrawl", "raw": {"content": "<a href='https://a.example/2'>next</a>"}}
        return {"provider": "firecrawl", "raw": {"content": "leaf page, no more links"}}

    with mock.patch.object(ws, "web_search_snippets", return_value=fake_search), \
         mock.patch("skillforge.research.scrape", side_effect=fake_scrape):
        leads = sourcer.intelligent_crawl("query", max_depth=2, max_pages_per_level=5)
    urls = {l["url"] for l in leads}
    assert urls == {"https://a.example/1", "https://a.example/2"}


# ── save_leads ───────────────────────────────────────────────────────────────
def test_save_leads_writes_real_json_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "LEADS_DIR", str(tmp_path))
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path / "cache"))
    leads = [{"url": "https://example.com", "entities": []}]
    path = sourcer.save_leads(leads, "my label!!")
    assert path is not None
    assert "my-label" in path
    with open(path) as f:
        written = json.load(f)
    assert written["count"] == 1
    assert written["leads"] == leads


def test_save_leads_no_leads_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "LEADS_DIR", str(tmp_path))
    sourcer = ws.WebSourcer(cache_dir=str(tmp_path / "cache"))
    assert sourcer.save_leads([], "empty") is None


# ── module-level research() convenience function ────────────────────────────
def test_research_depth_one_calls_process_query(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "CACHE_DIR", str(tmp_path))
    with mock.patch.object(ws.WebSourcer, "process_query", return_value=[{"url": "https://x.example"}]) as m, \
         mock.patch.object(ws.WebSourcer, "intelligent_crawl") as m2:
        out = ws.research("q", max_depth=1)
    assert out["count"] == 1
    m.assert_called_once()
    m2.assert_not_called()


def test_research_depth_two_calls_intelligent_crawl(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "CACHE_DIR", str(tmp_path))
    with mock.patch.object(ws.WebSourcer, "intelligent_crawl", return_value=[]) as m, \
         mock.patch.object(ws.WebSourcer, "process_query") as m2:
        ws.research("q", max_depth=2)
    m.assert_called_once()
    m2.assert_not_called()
