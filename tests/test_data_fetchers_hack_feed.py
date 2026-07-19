"""Tests for agents/data_fetchers.py's get_hack_feed()/_incident_source_url() —
each incident now carries a real per-incident source_url (DeFiLlama's own
link to the original disclosure/article) when the raw feed actually has
one, alongside VAPE's own analysis_report (a different, independently
attached field — see agents/security_sweep.py). Never fabricates a URL:
absent/malformed candidate fields simply yield source_url=None, same
honest-degradation as every other optional field in this pipeline.
"""
from unittest import mock

from agents import data_fetchers as df


def test_incident_source_url_prefers_real_source_field():
    assert df._incident_source_url({"source": "https://twitter.com/foo/status/123"}) == "https://twitter.com/foo/status/123"


def test_incident_source_url_falls_back_through_candidates():
    assert df._incident_source_url({"link": "https://rekt.news/foo"}) == "https://rekt.news/foo"
    assert df._incident_source_url({"url": "https://example.com/a"}) == "https://example.com/a"


def test_incident_source_url_none_when_absent():
    assert df._incident_source_url({}) is None
    assert df._incident_source_url({"name": "SomeHack"}) is None


def test_incident_source_url_rejects_non_url_values():
    # A non-URL string (or wrong type) must never be surfaced as a link.
    assert df._incident_source_url({"source": "Twitter thread"}) is None
    assert df._incident_source_url({"source": 12345}) is None
    assert df._incident_source_url({"source": None}) is None


def test_get_hack_feed_passes_through_real_source_url():
    raw = [{"date": 1737331200, "name": "Foo Protocol", "amount": 1_000_000,
            "chain": ["Base"], "technique": "Reentrancy", "source": "https://rekt.news/foo-rekt"}]
    with mock.patch.object(df, "_get", return_value=raw):
        feed = df.get_hack_feed(limit=5)
    assert feed["incidents"][0]["source_url"] == "https://rekt.news/foo-rekt"


def test_get_hack_feed_incident_with_no_source_has_none():
    raw = [{"date": 1737331200, "name": "Bar Protocol", "amount": 500_000,
            "chain": ["Ethereum"], "technique": None}]
    with mock.patch.object(df, "_get", return_value=raw):
        feed = df.get_hack_feed(limit=5)
    assert feed["incidents"][0]["source_url"] is None
