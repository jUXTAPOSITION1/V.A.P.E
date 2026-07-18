"""Tests for agents/llm.py's Grok/xAI wiring — provider composition, the
retry-then-fallthrough behavior, and best-effort usage logging.

All hermetic: urllib.request.urlopen is mocked, no real network call, no
real API key. Provider ordering is asserted independently of whatever real
env vars happen to be set when the suite runs.
"""
import json
import urllib.error
from unittest import mock

import pytest

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


def test_xai_provider_has_no_fast_or_bulk_model():
    """xai_1 must only define deep/frontier models — a bare tier="fast"
    call reaching it (e.g. if everyone else is down) must never silently
    resolve to Grok via the deep-model fallback for what was meant to be a
    cheap/easy task... except through the documented deep-model fallback,
    which is fine for tier="deep"/"frontier" specifically. What must NOT
    exist is a distinct "fast"/"bulk" key that would make xai a *preferred*
    fast-tier provider."""
    for name, _env, _url, models in llm.PROVIDERS:
        if name == "xai_1":
            assert "fast" not in models
            assert "bulk" not in models
            assert models.get("deep") == "grok-4-1-fast-reasoning"
            assert models.get("frontier") == "grok-4-1-fast-reasoning"


def test_default_providers_order_unchanged_xai_appended_last():
    names = [p[0] for p in llm.PROVIDERS]
    assert names[:6] == ["groq", "cerebras", "openrouter", "gemini", "github", "together"]
    assert names[6:] == ["xai_1"]


def test_frontier_order_is_grok_then_groq_then_gemini_then_rest():
    names = [p[0] for p in llm.FRONTIER_ORDER]
    assert names[:3] == ["xai_1", "groq", "gemini"]
    assert set(names) == set(p[0] for p in llm.PROVIDERS)  # nothing dropped


def test_xai_429_falls_through_to_next_provider(monkeypatch):
    """A real 429 on the xai key falls through to the next provider in
    provider_order immediately (no repeated hammering of an already
    rate-limited key)."""
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setenv("GROQ_API_KEY", "groqkey")
    xai_attempts = {"n": 0}

    def fake_urlopen(req, timeout=None):
        if req.headers.get("Authorization") == "Bearer key1":
            xai_attempts["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 429, "rate limited", {}, None)
        return _fake_response("via groq")

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
        text, provider = llm.ask("sys", "usr", tier="frontier",
                                 provider_order=llm.FRONTIER_ORDER,
                                 retries_per_provider=2)
    assert provider == "groq" and text == "via groq"
    assert xai_attempts["n"] == 1  # one try, immediate fallthrough — not hammered


def test_xai_non_429_error_retries_same_key_before_falling_through(monkeypatch):
    """A non-429 error (5xx, connection issue) DOES retry the same key up to
    retries_per_provider times before moving to the next provider."""
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setenv("GROQ_API_KEY", "groqkey")
    xai_attempts = {"n": 0}

    def fake_urlopen(req, timeout=None):
        if req.headers.get("Authorization") == "Bearer key1":
            xai_attempts["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 503, "upstream error", {}, None)
        return _fake_response("via groq")

    with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen), \
         mock.patch("time.sleep"):  # skip the real backoff delay in tests
        text, provider = llm.ask("sys", "usr", tier="frontier",
                                 provider_order=llm.FRONTIER_ORDER,
                                 retries_per_provider=2)
    assert provider == "groq" and text == "via groq"
    assert xai_attempts["n"] == 2  # fully exhausted its retry budget


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


def _write_usage_rows(path, rows):
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


class TestDailySpendCap:
    """agents/llm.py's daily $ spend cap — the only provider it can apply to
    is xai_1 (real money); every other provider is free/quota-limited and
    has no entry in PROVIDER_PRICING_USD_PER_M_TOKENS at all."""

    def test_todays_spend_sums_only_todays_rows_for_the_priced_provider(self, monkeypatch, tmp_path):
        usage_log = tmp_path / "llm_usage.jsonl"
        monkeypatch.setattr(llm, "USAGE_LOG", str(usage_log))
        today = llm.datetime.now(llm.timezone.utc).strftime("%Y-%m-%d")
        _write_usage_rows(usage_log, [
            {"ts": f"{today}T00:00:00Z", "provider": "xai_1", "prompt_tokens": 1_000_000, "completion_tokens": 0},
            {"ts": f"{today}T01:00:00Z", "provider": "xai_1", "prompt_tokens": 0, "completion_tokens": 1_000_000},
            {"ts": "2020-01-01T00:00:00Z", "provider": "xai_1", "prompt_tokens": 1_000_000, "completion_tokens": 0},
            {"ts": f"{today}T02:00:00Z", "provider": "groq", "prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
        ])
        spend = llm._todays_paid_spend_usd("xai_1")
        assert spend == pytest.approx(0.20 + 0.50)  # only today's two xai_1 rows

    def test_free_provider_has_zero_spend_regardless_of_usage(self, monkeypatch, tmp_path):
        usage_log = tmp_path / "llm_usage.jsonl"
        monkeypatch.setattr(llm, "USAGE_LOG", str(usage_log))
        today = llm.datetime.now(llm.timezone.utc).strftime("%Y-%m-%d")
        _write_usage_rows(usage_log, [
            {"ts": f"{today}T00:00:00Z", "provider": "groq", "prompt_tokens": 10**9, "completion_tokens": 10**9},
        ])
        assert llm._todays_paid_spend_usd("groq") == 0.0

    def test_cap_reached_skips_xai_and_falls_through_to_groq(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        usage_log = tmp_path / "llm_usage.jsonl"
        findings_log = tmp_path / "findings.jsonl"
        monkeypatch.setattr(llm, "USAGE_LOG", str(usage_log))
        monkeypatch.setattr(llm, "FINDINGS_LOG", str(findings_log))
        monkeypatch.setenv("XAI_DAILY_SPEND_CAP_USD", "1.00")
        today = llm.datetime.now(llm.timezone.utc).strftime("%Y-%m-%d")
        # 10M input tokens @ $0.20/M = $2.00, already over the $1.00 cap.
        _write_usage_rows(usage_log, [
            {"ts": f"{today}T00:00:00Z", "provider": "xai_1", "prompt_tokens": 10_000_000, "completion_tokens": 0},
        ])
        xai_attempts = {"n": 0}

        def fake_urlopen(req, timeout=None):
            if req.headers.get("Authorization") == "Bearer key1":
                xai_attempts["n"] += 1
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask("sys", "usr", tier="frontier", provider_order=llm.FRONTIER_ORDER)

        assert provider == "groq" and text == "via groq"
        assert xai_attempts["n"] == 0  # never even attempted, no wasted retry/backoff
        findings = findings_log.read_text().strip().splitlines()
        assert len(findings) == 1
        finding = json.loads(findings[0])
        assert finding["severity"] == "MEDIUM"
        assert "xai_1" in finding["title"]

    def test_cap_reached_finding_is_not_duplicated_within_the_same_day(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        usage_log = tmp_path / "llm_usage.jsonl"
        findings_log = tmp_path / "findings.jsonl"
        monkeypatch.setattr(llm, "USAGE_LOG", str(usage_log))
        monkeypatch.setattr(llm, "FINDINGS_LOG", str(findings_log))
        monkeypatch.setenv("XAI_DAILY_SPEND_CAP_USD", "1.00")
        today = llm.datetime.now(llm.timezone.utc).strftime("%Y-%m-%d")
        _write_usage_rows(usage_log, [
            {"ts": f"{today}T00:00:00Z", "provider": "xai_1", "prompt_tokens": 10_000_000, "completion_tokens": 0},
        ])

        def fake_urlopen(req, timeout=None):
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask("sys", "usr", tier="frontier", provider_order=llm.FRONTIER_ORDER)
            llm.ask("sys", "usr", tier="frontier", provider_order=llm.FRONTIER_ORDER)

        assert len(findings_log.read_text().strip().splitlines()) == 1

    def test_default_cap_is_used_when_env_var_unset(self, monkeypatch):
        monkeypatch.delenv("XAI_DAILY_SPEND_CAP_USD", raising=False)
        assert llm._daily_cap_usd("xai_1") == llm.DEFAULT_DAILY_SPEND_CAP_USD


class TestCandidateProvider:
    """agents/llm.py's opt-in fine-tuned-candidate provider (training/) —
    must stay entirely absent from the default chain until explicitly
    requested, per data/finetune/DATASET_CARD.md's evaluate-before-real-
    traffic rule."""

    def test_candidate_absent_from_default_providers_and_frontier_order(self):
        assert "vape_candidate" not in [p[0] for p in llm.PROVIDERS]
        assert "vape_candidate" not in [p[0] for p in llm.FRONTIER_ORDER]

    def test_candidate_order_is_plain_providers_when_url_unset(self, monkeypatch):
        monkeypatch.delenv("VAPE_CANDIDATE_URL", raising=False)
        order = llm.candidate_provider_order()
        assert [p[0] for p in order] == [p[0] for p in llm.PROVIDERS]

    def test_candidate_order_prepends_candidate_when_url_set(self, monkeypatch):
        monkeypatch.setenv("VAPE_CANDIDATE_URL", "http://localhost:8000/v1")
        order = llm.candidate_provider_order()
        assert order[0][0] == "vape_candidate"
        assert order[0][2] == "http://localhost:8000/v1/chat/completions"
        assert order[0][3] == {"fast": "vape-candidate", "deep": "vape-candidate", "bulk": "vape-candidate"}
        assert [p[0] for p in order[1:]] == [p[0] for p in llm.PROVIDERS]

    def test_candidate_order_honors_custom_model_name(self, monkeypatch):
        monkeypatch.setenv("VAPE_CANDIDATE_URL", "http://localhost:8000/v1")
        monkeypatch.setenv("VAPE_CANDIDATE_MODEL", "vape-gemma-lora")
        order = llm.candidate_provider_order()
        assert order[0][3]["fast"] == "vape-gemma-lora"

    def test_ask_candidate_reaches_candidate_first_when_configured(self, monkeypatch):
        monkeypatch.setenv("VAPE_CANDIDATE_URL", "http://localhost:8000/v1")

        def fake_urlopen(req, timeout=None):
            return _fake_response("candidate reply")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_candidate("sys", "usr")
        assert provider == "vape_candidate" and text == "candidate reply"

    def test_ask_candidate_falls_through_to_free_chain_when_unset(self, monkeypatch):
        monkeypatch.delenv("VAPE_CANDIDATE_URL", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")

        def fake_urlopen(req, timeout=None):
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_candidate("sys", "usr")
        assert provider == "groq" and text == "via groq"
