"""Tests for agents/run.py's ask_llm()/_ask_with_signal_retry() search=True
forwarding — the primary bounty-report generation path
(run() -> _ask_with_signal_retry(VAPE_REPORT_SYSTEM, ...) -> ask_llm()) opts
into xAI Live Search by default at its real call site; these pin that the
kwarg actually reaches agents.llm.ask_oci_grok() rather than being dropped
somewhere in the two wrapper layers above it. Hermetic: run._llm_ask_oci_grok
is monkeypatched, no real network/LLM call.
"""
from agents import run


def test_ask_llm_forwards_search_true(monkeypatch):
    captured = {}

    def fake_ask_oci_grok(system, query, tier="fast", temperature=0.7, provider_order=None,
                           max_tokens=2048, search=False):
        captured["search"] = search
        return ("some report text", "xai_1")

    monkeypatch.setattr(run, "_llm_ask_oci_grok", fake_ask_oci_grok)
    monkeypatch.setattr(run, "_llm_available", lambda: ["xai_1"])
    run.ask_llm("sys", "usr", search=True)
    assert captured["search"] is True


def test_ask_llm_defaults_search_false(monkeypatch):
    captured = {}

    def fake_ask_oci_grok(system, query, tier="fast", temperature=0.7, provider_order=None,
                           max_tokens=2048, search=False):
        captured["search"] = search
        return ("some report text", "xai_1")

    monkeypatch.setattr(run, "_llm_ask_oci_grok", fake_ask_oci_grok)
    monkeypatch.setattr(run, "_llm_available", lambda: ["xai_1"])
    run.ask_llm("sys", "usr")
    assert captured["search"] is False


def test_ask_with_signal_retry_forwards_search(monkeypatch):
    captured = []

    def fake_ask_llm(system, prompt, tier="deep", temperature=0.4, provider_order=None,
                      max_tokens=3200, search=False):
        captured.append(search)
        return "SIGNAL: LOW\nnothing changed"

    monkeypatch.setattr(run, "ask_llm", fake_ask_llm)
    result = run._ask_with_signal_retry("sys", "prompt", search=True)
    assert result == "SIGNAL: LOW\nnothing changed"
    assert captured == [True]
