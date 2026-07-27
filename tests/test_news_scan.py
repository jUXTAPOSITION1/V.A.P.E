"""Tests for agents/news_scan.py's editorial ordering rule: crypto/blockchain
headlines always occupy the ticker's leading slots, even when a non-crypto
(macro/stocks) headline is more recent. Hermetic: gather_headlines() and the
feed file write are both mocked/redirected, no real network or repo writes.
"""
import json
from unittest import mock

from agents import news_common as nc
from agents import news_scan


def test_is_crypto_topic_classifies_beats_correctly():
    assert nc.is_crypto_topic("base") is True
    assert nc.is_crypto_topic("defi-security") is True
    assert nc.is_crypto_topic("web-search") is True
    assert nc.is_crypto_topic("macro") is False
    assert nc.is_crypto_topic("stocks") is False


def test_crypto_headlines_always_lead_even_when_older(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    monkeypatch.setattr(nc, "STATE_PATH", str(tmp_path / "news_state.json"))

    fake_headlines = [
        {"title": "Wall Street rallies on jobs report", "url": "https://a.example/1",
         "source": "Reuters", "published": "Mon, 27 Jul 2026 18:00:00 GMT", "topic": "stocks"},
        {"title": "Base network hits record TVL", "url": "https://b.example/2",
         "source": "CoinDesk", "published": "Mon, 27 Jul 2026 06:00:00 GMT", "topic": "base"},
    ]
    with mock.patch.object(nc, "gather_headlines", return_value=fake_headlines):
        ticker = news_scan.run()

    assert ticker[0]["url"] == "https://b.example/2"  # older crypto story still leads
    assert ticker[1]["url"] == "https://a.example/1"

    with open(nc.FEED_PATH) as f:
        written = json.load(f)
    assert written["headlines"][0]["url"] == "https://b.example/2"
    assert written["headlines"][0]["crypto"] is True
    assert written["headlines"][1]["crypto"] is False


def test_all_crypto_preserves_recency_order(tmp_path, monkeypatch):
    monkeypatch.setattr(nc, "FEED_PATH", str(tmp_path / "news-feed.json"))
    monkeypatch.setattr(nc, "STATE_PATH", str(tmp_path / "news_state.json"))

    fake_headlines = [
        {"title": "Older DeFi story", "url": "https://a.example/1",
         "source": "X", "published": "Mon, 27 Jul 2026 06:00:00 GMT", "topic": "defi-security"},
        {"title": "Newer Base story", "url": "https://b.example/2",
         "source": "Y", "published": "Mon, 27 Jul 2026 18:00:00 GMT", "topic": "base"},
    ]
    with mock.patch.object(nc, "gather_headlines", return_value=fake_headlines):
        ticker = news_scan.run()

    assert ticker[0]["url"] == "https://b.example/2"
    assert ticker[1]["url"] == "https://a.example/1"
