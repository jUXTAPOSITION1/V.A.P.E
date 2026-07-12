"""Tests for agents/llm.py's Grok/xAI wiring — provider composition, the
key-exhaustion-then-fallthrough behavior (xAI ToS: no rapid key switching),
and best-effort usage logging.

All hermetic: urllib.request.urlopen is mocked, no real network call, no
real API key. Provider ordering is asserted independently of whatever real
env vars happen to be set when the suite runs.
"""
import json
import urllib.error
from unittest import mock

from agents import llm


def _fake_response(content, usage=None):
    body = {"choices": [{"message": {"content": content}}]}
    if usage is not None:
        body["usage"] = usage
    payload = json.dumps(body).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload
    return Resp()


def test_xai_providers_have_no_fast_or_bulk_model():
    """xai_1/xai_2 must only define deep/frontier models — a bare tier="fast"
    call reaching them (e.g. if everyone else is down) must never silently
    resolve to Grok via the deep-model fallback for what was meant to be a
    cheap/easy task... except through the documented deep-model fallback,
    which is fine for tier="deep"/"frontier" specifically. What must NOT
    exist is a distinct "fast"/"bulk" key that would make xai a *preferred*
    fast-tier provider."""
    for name, _env, _url, models in llm.PROVIDERS:
        if name in ("xai_1", "xai_2"):
            assert "fast" not in models
            assert "bulk" not in models
            assert models.get("deep") == "grok-4-1-fast-reasoning"
            assert models.get("frontier") == "grok-4-1-fast-reasoning"


def test_default_providers_order_unchanged_xai_appended_last():
    names = [p[0] for p in llm.PROVIDERS]
    assert names[:6] == ["groq", "cerebras", "openrouter", "gemini", "github", "together"]
    assert names[6:] == ["xai_1", "xai_2"]


def test_frontier_order_is_grok_then_groq_then_gemini_then_rest():
    names = [p[0] for p in llm.FRONTIER_ORDER]
    assert names[:4] == ["xai_1", "xai_2", "groq", "gemini"]
    assert set(names) == set(p[0] for p in llm.PROVIDERS)  # nothing dropped


def test_key1_429_falls_through_to_key2_without_hammering(monkeypatch):
    """The core anti-abuse property: a real 429 on key 1 falls through to
    key 2 immediately (no repeated hammering of an already-rate-limited
    key) — key 1 is always tried FIRST and is never alternated call-by-call
    with key 2."""
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setenv("XAI_API_KEY_2", "key2")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    key1_attempts = {"n": 0}

    def fake_urlopen(req, timeout=None):
        if req.headers.get("Authorization") == "Bearer key1":
            key1_attempts["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 429, "rate limited", {}, None)
        return _fake_response("via key2")

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        text, provider = llm.ask("sys", "usr", tier="frontier",
                                 provider_order=[p for p in llm.PROVIDERS if p[0].startswith("xai")],
                                 retries_per_provider=2)
    assert provider == "xai_2" and text == "via key2"
    assert key1_attempts["n"] == 1  # one try, immediate fallthrough — not hammered


def test_key1_non_429_error_retries_same_key_before_key2(monkeypatch):
    """A non-429 error (5xx, connection issue) DOES retry the same key up to
    retries_per_provider times before moving to key 2 — key 1 is exhausted,
    not skipped after one soft failure."""
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setenv("XAI_API_KEY_2", "key2")
    key1_attempts = {"n": 0}

    def fake_urlopen(req, timeout=None):
        if req.headers.get("Authorization") == "Bearer key1":
            key1_attempts["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 503, "upstream error", {}, None)
        return _fake_response("via key2")

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         mock.patch("time.sleep"):  # skip the real backoff delay in tests
        text, provider = llm.ask("sys", "usr", tier="frontier",
                                 provider_order=[p for p in llm.PROVIDERS if p[0].startswith("xai")],
                                 retries_per_provider=2)
    assert provider == "xai_2" and text == "via key2"
    assert key1_attempts["n"] == 2  # fully exhausted its retry budget


def test_default_fast_tier_call_never_reaches_xai_when_groq_available(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groqkey")
    monkeypatch.setenv("XAI_API_KEY_1", "xaikey")

    def fake_urlopen(req, timeout=None):
        return _fake_response(req.headers.get("Authorization"))

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        text, provider = llm.ask("sys", "usr", tier="fast")  # no provider_order override
    assert provider == "groq"


def test_usage_is_logged_on_success(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    log_path = tmp_path / "llm_usage.jsonl"
    monkeypatch.setattr(llm, "USAGE_LOG", str(log_path))

    def fake_urlopen(req, timeout=None):
        return _fake_response("ok", usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        llm.ask("sys", "usr", tier="frontier", provider_order=llm.FRONTIER_ORDER)

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["provider"] == "xai_1"
    assert row["model"] == "grok-4-1-fast-reasoning"
    assert row["total_tokens"] == 15


def test_usage_logging_is_a_noop_when_usage_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    log_path = tmp_path / "llm_usage.jsonl"
    monkeypatch.setattr(llm, "USAGE_LOG", str(log_path))

    def fake_urlopen(req, timeout=None):
        return _fake_response("ok")  # no usage field

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        llm.ask("sys", "usr", tier="frontier", provider_order=llm.FRONTIER_ORDER)
    assert not log_path.exists()


def test_ask_frontier_defaults_to_frontier_order(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")

    def fake_urlopen(req, timeout=None):
        return _fake_response("grok reply")

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        text, provider = llm.ask_frontier("sys", "usr")
    assert provider == "xai_1" and text == "grok reply"


def test_ask_safe_still_never_raises_when_all_absent(monkeypatch):
    for _name, env, _url, _models in llm.PROVIDERS:
        monkeypatch.delenv(env, raising=False)
    text, provider = llm.ask_safe("sys", "usr")
    assert provider is None
    assert text.startswith("[llm unavailable")
