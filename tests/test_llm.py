"""Tests for agents/llm.py's Grok/xAI wiring — provider composition, the
retry-then-fallthrough behavior, and best-effort usage logging.

All hermetic: urllib.request.urlopen is mocked, no real network call, no
real API key. Provider ordering is asserted independently of whatever real
env vars happen to be set when the suite runs.
"""
import io
import json
import urllib.error
import urllib.parse
from datetime import datetime, timezone
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


def test_frontier_order_is_groq_then_gemini_then_grok_then_rest():
    """By explicit direction (2026-07-25): xai_1 (direct paid xAI) is the
    fallback BELOW free-tier groq/gemini, not the primary pick — OCI Grok
    4.3/Vertex (agents/llm.py::ask_oci_grok()) remain the real primary route
    ahead of this whole chain; FRONTIER_ORDER is only reached once both of
    those have failed or aren't configured."""
    names = [p[0] for p in llm.FRONTIER_ORDER]
    assert names[:3] == ["groq", "gemini", "xai_1"]
    assert set(names) == set(p[0] for p in llm.PROVIDERS)  # nothing dropped


def _xai_then_groq_order():
    """An explicit [xai_1, groq] provider_order for tests of the generic
    retry-then-fallthrough mechanics, independent of FRONTIER_ORDER's real
    ordering (which, by explicit direction 2026-07-25, now tries groq/gemini
    BEFORE xai_1 — see test_frontier_order_is_groq_then_gemini_then_grok_
    then_rest). These tests care about the fallthrough behavior itself, not
    which provider happens to be first in the real chain."""
    by_name = {p[0]: p for p in llm.PROVIDERS}
    return [by_name["xai_1"], by_name["groq"]]


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
                                 provider_order=_xai_then_groq_order(),
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
                                 provider_order=_xai_then_groq_order(),
                                 retries_per_provider=2)
    assert provider == "groq" and text == "via groq"
    assert xai_attempts["n"] == 2  # fully exhausted its retry budget


class TestSearchGrounding:
    """search=True opts into xAI's real Live Search — gated strictly to the
    xai_1 provider (the only one whose endpoint understands the field),
    silently absent for every other provider even when search=True is
    passed on the call."""

    def test_search_true_adds_search_parameters_for_xai(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai with search")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask("sys", "usr", tier="frontier",
                                      provider_order=llm.FRONTIER_ORDER, search=True)
        assert provider == "xai_1"
        assert captured["body"]["search_parameters"] == {"mode": "auto", "return_citations": True}

    def test_search_false_omits_search_parameters_for_xai(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai no search")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask("sys", "usr", tier="frontier", provider_order=llm.FRONTIER_ORDER)
        assert "search_parameters" not in captured["body"]

    def test_search_true_does_not_leak_into_non_xai_provider_payload(self, monkeypatch):
        """No xai_1 key configured this run (falls through to groq, the next
        entry in FRONTIER_ORDER) — search=True must never add
        search_parameters to a provider that doesn't support it, even
        when explicitly requested on the call."""
        monkeypatch.delenv("XAI_API_KEY_1", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask("sys", "usr", tier="frontier",
                                      provider_order=llm.FRONTIER_ORDER, search=True)
        assert provider == "groq"
        assert "search_parameters" not in captured["body"]


class TestSearchThreadsThroughFallbackChain:
    """search=True was added to ask() first; ask_vertex_candidate(),
    ask_oci_grok(), and ask_oci_grok_frontier() all sit above it in the
    real fallback chain used by every report-generating call site, so each
    must forward the kwarg rather than silently dropping it."""

    def test_ask_vertex_candidate_skips_direct_call_when_search_true_even_with_token(self, monkeypatch):
        """Same class of bug as ask_oci_grok()'s OCI branch: Vertex's own
        generateContent call has no search-grounding equivalent, so
        search=True must route around it even when VAPE_VERTEX_ACCESS_TOKEN
        is configured, rather than the token winning the race."""
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-vertex-token")
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            hostname = urllib.parse.urlparse(req.full_url).hostname
            if "aiplatform" in hostname:
                raise AssertionError("search=True must not call Vertex's endpoint at all")
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai with search")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _, provider = llm.ask_vertex_candidate("sys", "usr", tier="frontier",
                                                     provider_order=llm.FRONTIER_ORDER, search=True)
        assert provider == "xai_1"
        assert captured["body"]["search_parameters"] == {"mode": "auto", "return_citations": True}

    def test_ask_vertex_candidate_forwards_search(self, monkeypatch):
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_vertex_candidate("sys", "usr", tier="frontier",
                                      provider_order=llm.FRONTIER_ORDER, search=True)
        assert captured["body"]["search_parameters"] == {"mode": "auto", "return_citations": True}

    def test_ask_oci_grok_forwards_search(self, monkeypatch):
        monkeypatch.delenv("OCI_GENAI_API_KEY", raising=False)
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_oci_grok("sys", "usr", tier="frontier",
                              provider_order=llm.FRONTIER_ORDER, search=True)
        assert captured["body"]["search_parameters"] == {"mode": "auto", "return_citations": True}

    def test_ask_oci_grok_frontier_forwards_search(self, monkeypatch):
        monkeypatch.delenv("OCI_GENAI_API_KEY", raising=False)
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_oci_grok_frontier("sys", "usr", search=True)
        assert captured["body"]["search_parameters"] == {"mode": "auto", "return_citations": True}

    def test_search_defaults_false_through_the_chain(self, monkeypatch):
        monkeypatch.delenv("OCI_GENAI_API_KEY", raising=False)
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_oci_grok_frontier("sys", "usr")
        assert "search_parameters" not in captured["body"]


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
            text, provider = llm.ask("sys", "usr", tier="frontier", provider_order=_xai_then_groq_order())

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
            llm.ask("sys", "usr", tier="frontier", provider_order=_xai_then_groq_order())
            llm.ask("sys", "usr", tier="frontier", provider_order=_xai_then_groq_order())

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


def _fake_vertex_response(text, usage_meta=None, finish_reason=None):
    body = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
    if finish_reason is not None:
        body["candidates"][0]["finishReason"] = finish_reason
    if usage_meta is not None:
        body["usageMetadata"] = usage_meta
    payload = json.dumps(body).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload
    return Resp()


class TestVertexTunedCandidate:
    """agents/llm.py's second, independently-hosted candidate — VAPE's
    Vertex-AI-supervised-tuned Gemini model, called via generateContent
    (not OpenAI-compatible, unlike every other provider here) using a
    short-lived WIF access token. Must stay opt-in-only, same as the
    self-hosted-GPU candidate above."""

    def test_falls_through_to_free_chain_when_token_unset(self, monkeypatch):
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")

        def fake_urlopen(req, timeout=None):
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_vertex_candidate("sys", "usr")
        assert provider == "groq" and text == "via groq"

    def test_reaches_vertex_when_token_set(self, monkeypatch, tmp_path):
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setattr(llm, "USAGE_LOG", str(tmp_path / "llm_usage.jsonl"))
        # Hermetic: don't depend on the real, regenerable repo_digest.md —
        # the repo-digest prepending behavior itself has its own dedicated
        # tests below.
        monkeypatch.setattr(llm, "_load_repo_digest", lambda: "")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["auth"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode())
            return _fake_vertex_response("vertex reply",
                                          {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_vertex_candidate("sys prompt", "usr prompt")
        assert provider == "vertex_tuned" and text == "vertex reply"
        assert captured["auth"] == "Bearer fake-token"
        assert captured["url"] == (
            "https://aiplatform.us.rep.googleapis.com/v1/projects/87858016172"
            "/locations/us/endpoints/7011119457397374976:generateContent")
        assert captured["body"]["contents"] == [{"role": "user", "parts": [{"text": "usr prompt"}]}]
        assert captured["body"]["systemInstruction"] == {"parts": [{"text": "sys prompt"}]}

    def test_accepts_candidate_with_explicit_stop_finish_reason(self, monkeypatch):
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")

        def fake_urlopen(req, timeout=None):
            return _fake_vertex_response("a complete reply.", finish_reason="STOP")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_vertex_candidate("sys", "usr")
        assert provider == "vertex_tuned" and text == "a complete reply."

    def test_rejects_truncated_candidate_and_falls_through_to_free_chain(self, monkeypatch):
        """Real, live bug (2026-08-01): a security-adjacent news story
        tripped Gemini's own safety/recitation classifier mid-generation,
        and this code used to take the resulting partial candidate as a
        complete answer regardless of finishReason, publishing a story cut
        off mid-sentence inside an unclosed markdown link. A non-STOP
        finishReason (SAFETY here, but the same applies to RECITATION,
        MAX_TOKENS, OTHER, etc.) must now be treated as a failed call that
        falls through to the next real provider, not a success."""
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(urllib.parse.urlparse(req.full_url).hostname)
            if calls[-1] == "aiplatform.us.rep.googleapis.com":
                return _fake_vertex_response("...cut off mid-sentence about the [CoinDesk report](https://x",
                                              finish_reason="SAFETY")
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_vertex_candidate("sys", "usr")
        assert provider == "groq" and text == "via groq"
        assert len(calls) == 2

    def test_honors_env_overrides_for_project_location_endpoint(self, monkeypatch):
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setenv("VAPE_VERTEX_PROJECT_NUMBER", "999")
        monkeypatch.setenv("VAPE_VERTEX_LOCATION", "eu")
        monkeypatch.setenv("VAPE_VERTEX_ENDPOINT_ID", "123")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_vertex_response("ok")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_vertex_candidate("sys", "usr")
        assert captured["url"] == (
            "https://aiplatform.eu.rep.googleapis.com/v1/projects/999"
            "/locations/eu/endpoints/123:generateContent")

    def test_uses_classic_host_format_for_a_real_single_region(self, monkeypatch):
        """Only the two documented Vertex multi-region values (us/eu) get the
        aiplatform.{location}.rep.googleapis.com host — an actual single
        region like us-central1 keeps the classic
        {location}-aiplatform.googleapis.com form."""
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setenv("VAPE_VERTEX_LOCATION", "us-central1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_vertex_response("ok")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_vertex_candidate("sys", "usr")
        assert captured["url"].startswith("https://us-central1-aiplatform.googleapis.com/")

    def test_falls_through_to_free_chain_on_vertex_error(self, monkeypatch):
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if urllib.parse.urlparse(req.full_url).hostname == "aiplatform.us.rep.googleapis.com":
                raise urllib.error.URLError("connection refused")
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_vertex_candidate("sys", "usr")
        assert provider == "groq" and text == "via groq"
        assert len(calls) == 2

    def test_fallback_honors_caller_supplied_tier_and_provider_order(self, monkeypatch):
        """A real production call site (e.g. skillforge/synthesize.py) that
        normally calls ask(tier="deep", provider_order=FRONTIER_ORDER) must
        degrade to EXACTLY that when the candidate isn't configured — not
        silently drop to tier="fast" on the plain free chain, which would be
        a real quality regression for every run that hasn't opted in."""
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("XAI_API_KEY_1", "key1")

        def fake_urlopen(req, timeout=None):
            return _fake_response("grok reply")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_vertex_candidate(
                "sys", "usr", tier="deep", provider_order=llm.FRONTIER_ORDER)
        assert provider == "xai_1" and text == "grok reply"

    def test_http_error_body_is_surfaced_not_swallowed(self, monkeypatch, capsys):
        """A prior version only printed str(HTTPError) ("HTTP Error 400: Bad
        Request"), discarding Google's actual explanation of what was wrong
        with the request — the one piece of information needed to fix a
        real 400 from generateContent. Confirms the response body reaches
        stderr now."""
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        error_body = b'{"error": {"code": 400, "message": "Unknown name \\"systemInstruction\\"", "status": "INVALID_ARGUMENT"}}'

        def fake_urlopen(req, timeout=None):
            if urllib.parse.urlparse(req.full_url).hostname == "aiplatform.us.rep.googleapis.com":
                raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(error_body))
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_vertex_candidate("sys", "usr")
        assert "INVALID_ARGUMENT" in capsys.readouterr().err


def _fake_image_response(image_b64, mime="image/png"):
    body = {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": mime, "data": image_b64}}]}}]}
    payload = json.dumps(body).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload
    return Resp()


def _fake_imagen_response(image_b64, mime="image/png"):
    body = {"predictions": [{"mimeType": mime, "bytesBase64Encoded": image_b64}]} if image_b64 else {"predictions": []}
    payload = json.dumps(body).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload
    return Resp()


class TestGeminiImage:
    """agents/llm.py::ask_gemini_image() — VAPE's real image-generation
    route. Tries Vertex AI's Imagen (_call_vertex_imagen(), the ADC/OAuth-
    native path, explicit direction 2026-08-01: no API keys) first when
    VAPE_VERTEX_ACCESS_TOKEN is set, falling back to the Gemini Developer
    API's own image model ("Nano Banana", gemini-3.1-flash-lite-image) via
    GEMINI_API_KEY's x-goog-api-key header -- the same key already used by
    the 'gemini' free-tier text provider in PROVIDERS, not a new secret.

    Vertex Imagen replaced an earlier design (an OAuth-Bearer variant of the
    Gemini Developer API call itself) after live confirmation (2026-08-01)
    that generativelanguage.googleapis.com's generateContent method rejects
    ANY OAuth token outright (HTTP 403 ACCESS_TOKEN_SCOPE_INSUFFICIENT)
    regardless of scope/IAM/API-enablement -- that host is structurally
    API-key-only for inference. Imagen is a real, different Vertex publisher
    model built around OAuth/ADC as its native auth."""

    def test_returns_none_when_neither_auth_method_set(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        with mock.patch("urllib.request.urlopen") as mocked:
            assert llm.ask_gemini_image("a photo of coins") is None
        mocked.assert_not_called()

    def test_reaches_gemini_developer_api_and_decodes_bytes(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        import base64
        raw_bytes = b"\x89PNG-fake-image-bytes"
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["api_key_header"] = req.get_header("X-goog-api-key")
            captured["body"] = json.loads(req.data.decode())
            return _fake_image_response(base64.b64encode(raw_bytes).decode())

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = llm.ask_gemini_image("a close-up of gold coins on a dark table")
        assert result == raw_bytes
        assert captured["api_key_header"] == "fake-gemini-key"
        assert captured["url"] == (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-3.1-flash-lite-image:generateContent")
        assert captured["body"]["contents"] == [
            {"role": "user", "parts": [{"text": "a close-up of gold coins on a dark table"}]}]
        assert captured["body"]["generationConfig"]["responseModalities"] == ["IMAGE"]
        assert captured["body"]["generationConfig"]["imageConfig"]["aspectRatio"] == "16:9"

    def test_honors_env_override_for_model(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)
        monkeypatch.setenv("VAPE_GEMINI_IMAGE_MODEL", "some-other-image-model")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_image_response("")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_gemini_image("prompt")
        assert captured["url"] == (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "some-other-image-model:generateContent")

    def test_returns_none_on_http_error(self, monkeypatch, capsys):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {},
                                          io.BytesIO(b'{"error":{"message":"bad modality"}}'))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_gemini_image("prompt") is None
        assert "bad modality" in capsys.readouterr().err

    def test_returns_none_when_response_has_no_inline_image(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
        monkeypatch.delenv("VAPE_VERTEX_ACCESS_TOKEN", raising=False)

        def fake_urlopen(req, timeout=None):
            return _fake_vertex_response("just text, no image")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_gemini_image("prompt") is None

    def test_prefers_vertex_imagen_over_api_key_when_both_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-adc-token")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project-real-id")
        import base64
        raw_bytes = b"\x89PNG-fake-imagen-bytes"
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["auth_header"] = req.get_header("Authorization")
            captured["api_key_header"] = req.get_header("X-goog-api-key")
            captured["body"] = json.loads(req.data.decode())
            return _fake_imagen_response(base64.b64encode(raw_bytes).decode())

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = llm.ask_gemini_image("prompt")
        assert result == raw_bytes
        assert captured["url"] == (
            "https://us-central1-aiplatform.googleapis.com/v1/projects/project-real-id"
            "/locations/us-central1/publishers/google/models/imagen-4.0-generate-001:predict")
        assert captured["auth_header"] == "Bearer fake-adc-token"
        assert captured["api_key_header"] is None
        assert captured["body"]["instances"] == [{"prompt": "prompt"}]
        assert captured["body"]["parameters"]["aspectRatio"] == "16:9"

    def test_falls_back_to_gemini_developer_api_when_vertex_imagen_returns_none(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-adc-token")
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if urllib.parse.urlparse(req.full_url).hostname == "us-central1-aiplatform.googleapis.com":
                return _fake_imagen_response("")
            return _fake_image_response("ZmFrZQ==")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = llm.ask_gemini_image("prompt")
        assert result == b"fake"
        assert len(calls) == 2
        assert urllib.parse.urlparse(calls[0]).hostname == "us-central1-aiplatform.googleapis.com"
        assert urllib.parse.urlparse(calls[1]).hostname == "generativelanguage.googleapis.com"

    def test_vertex_imagen_project_resolution_order(self, monkeypatch):
        # VAPE_VERTEX_PROJECT_ID > GOOGLE_CLOUD_PROJECT > CLOUDSDK_CORE_PROJECT >
        # VAPE_VERTEX_PROJECT_NUMBER > the hardcoded default -- explicit env vars
        # win over the auto-exported ones google-github-actions/auth sets.
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-adc-token")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "from-google-cloud-project")
        monkeypatch.setenv("CLOUDSDK_CORE_PROJECT", "from-cloudsdk-core-project")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_imagen_response("")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_gemini_image("prompt")
        assert "/projects/from-google-cloud-project/" in captured["url"]

        monkeypatch.setenv("VAPE_VERTEX_PROJECT_ID", "from-explicit-project-id")
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_gemini_image("prompt")
        assert "/projects/from-explicit-project-id/" in captured["url"]

    def test_vertex_imagen_falls_back_to_default_project_number(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-adc-token")
        monkeypatch.delenv("VAPE_VERTEX_PROJECT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("CLOUDSDK_CORE_PROJECT", raising=False)
        monkeypatch.delenv("VAPE_VERTEX_PROJECT_NUMBER", raising=False)
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_imagen_response("")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_gemini_image("prompt")
        assert f"/projects/{llm.VERTEX_TUNED_DEFAULT_PROJECT_NUMBER}/" in captured["url"]

    def test_honors_env_overrides_for_imagen_location_and_model(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-adc-token")
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project-real-id")
        monkeypatch.setenv("VAPE_VERTEX_IMAGE_LOCATION", "europe-west4")
        monkeypatch.setenv("VAPE_VERTEX_IMAGE_MODEL", "imagen-4.0-fast-generate-001")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_imagen_response("")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_gemini_image("prompt")
        assert captured["url"] == (
            "https://europe-west4-aiplatform.googleapis.com/v1/projects/project-real-id"
            "/locations/europe-west4/publishers/google/models/imagen-4.0-fast-generate-001:predict")

    def test_returns_none_when_vertex_imagen_errors_and_no_api_key_fallback(self, monkeypatch, capsys):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-adc-token")

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {},
                                          io.BytesIO(b'{"error":{"message":"denied"}}'))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_gemini_image("prompt") is None
        assert "vertex_imagen:HTTP403" in capsys.readouterr().err


def _fake_xai_image_response(url):
    payload = json.dumps({"data": [{"url": url}]}).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return payload
    return Resp()


class TestXaiImage:
    """agents/llm.py::ask_xai_image() — VAPE's real, working image-gen route
    (promoted to primary 2026-08-01, since Gemini/Vertex are both confirmed
    dead ends right now), behind xAI's Grok Imagine Image (grok-imagine-image
    -- grok-2-image-1212 was deprecated by xAI 2026-02-28 and 404s), a
    separate billed-per-image product from every other xAI text use in this
    file, hence its own daily-count cap file rather than the token-based
    rate limiting used elsewhere."""

    def test_returns_none_when_key_unset(self, monkeypatch):
        monkeypatch.delenv("XAI_API_KEY_1", raising=False)
        with mock.patch("urllib.request.urlopen") as mocked:
            assert llm.ask_xai_image("a photo of coins") is None
        mocked.assert_not_called()

    def test_reaches_xai_and_returns_url(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["auth"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode())
            return _fake_xai_image_response("https://xai.example/generated.png")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = llm.ask_xai_image("a close-up of gold coins on a dark table")
        assert result == "https://xai.example/generated.png"
        assert captured["url"] == "https://api.x.ai/v1/images/generations"
        assert captured["auth"] == "Bearer fake-xai-key"
        assert captured["body"]["model"] == "grok-imagine-image"
        assert captured["body"]["prompt"] == "a close-up of gold coins on a dark table"
        assert captured["body"]["aspect_ratio"] == "16:9"

    def test_passes_through_a_non_default_aspect_ratio(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_xai_image_response("https://xai.example/generated.png")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_xai_image("a tall portrait shot", aspect_ratio="9:16")
        assert captured["body"]["aspect_ratio"] == "9:16"

    def test_records_usage_on_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        usage_path = tmp_path / "xai_image_usage.json"
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(usage_path))

        def fake_urlopen(req, timeout=None):
            return _fake_xai_image_response("https://xai.example/one.png")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_xai_image("prompt")
        assert json.loads(usage_path.read_text())["count"] == 1

    def test_returns_none_once_daily_cap_reached(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setenv("XAI_IMAGE_DAILY_CAP", "1")
        usage_path = tmp_path / "xai_image_usage.json"
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(usage_path))
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        usage_path.write_text(json.dumps({"date": today, "count": 1}))

        with mock.patch("urllib.request.urlopen") as mocked:
            assert llm.ask_xai_image("prompt") is None
        mocked.assert_not_called()
        assert "daily cap" in capsys.readouterr().out

    def test_returns_none_on_http_error(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, io.BytesIO(b"boom"))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_xai_image("prompt") is None

    def test_returns_none_when_response_has_no_url(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))

        def fake_urlopen(req, timeout=None):
            payload = json.dumps({"data": [{}]}).encode()

            class Resp:
                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    pass

                def read(self):
                    return payload
            return Resp()

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_xai_image("prompt") is None

    def test_retries_once_after_a_transient_failure_then_succeeds(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, io.BytesIO(b"boom"))
            return _fake_xai_image_response("https://xai.example/second-try.png")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = llm.ask_xai_image("prompt")
        assert result == "https://xai.example/second-try.png"
        assert calls["n"] == 2

    def test_returns_none_after_exhausting_retries(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, io.BytesIO(b"boom"))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_xai_image("prompt") is None
        assert calls["n"] == 2  # one original attempt + one retry, default retries=1

    def test_retries_param_zero_disables_retry(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, io.BytesIO(b"boom"))

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            assert llm.ask_xai_image("prompt", retries=0) is None
        assert calls["n"] == 1

    def test_retry_does_not_double_count_daily_usage_on_eventual_success(self, monkeypatch, tmp_path):
        monkeypatch.setenv("XAI_API_KEY_1", "fake-xai-key")
        usage_path = tmp_path / "xai_image_usage.json"
        monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(usage_path))
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.HTTPError(req.full_url, 500, "Server Error", {}, io.BytesIO(b"boom"))
            return _fake_xai_image_response("https://xai.example/ok.png")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_xai_image("prompt")
        assert json.loads(usage_path.read_text())["count"] == 1


class TestOciGrok:
    """agents/llm.py's third candidate — Oracle Cloud's hosted xAI Grok 4.3,
    reached via OCI's OpenAI-compatible endpoint (same request/response
    shape as _call()/PROVIDERS, unlike the Vertex candidate above). Must
    stay opt-in-only, gated on OCI_GENAI_API_KEY, with its own daily-spend
    cap since this path runs outside ask()'s provider loop."""

    def test_falls_through_to_free_chain_when_key_unset(self, monkeypatch):
        monkeypatch.delenv("OCI_GENAI_API_KEY", raising=False)
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")

        def fake_urlopen(req, timeout=None):
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok("sys", "usr")
        assert provider == "groq" and text == "via groq"

    def test_reaches_oci_when_key_set(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.delenv("OCI_COMPARTMENT_OCID", raising=False)
        monkeypatch.setattr(llm, "USAGE_LOG", str(tmp_path / "llm_usage.jsonl"))
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["auth"] = req.get_header("Authorization")
            captured["compartment_header"] = req.get_header("Compartmentid")
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("grok via oci", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok("sys prompt", "usr prompt")
        assert provider == "oci_grok" and text == "grok via oci"
        assert captured["auth"] == "Bearer fake-oci-key"
        assert captured["url"] == (
            "https://inference.generativeai.us-ashburn-1.oci.oraclecloud.com"
            "/20231130/actions/v1/chat/completions")
        assert captured["body"]["model"] == "xai.grok-4.3"
        assert captured["body"]["messages"] == [
            {"role": "system", "content": "sys prompt"},
            {"role": "user", "content": "usr prompt"},
        ]
        assert captured["compartment_header"] is None  # not set unless OCI_COMPARTMENT_OCID is

    def test_compartment_header_sent_when_configured(self, monkeypatch):
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.setenv("OCI_COMPARTMENT_OCID", "ocid1.compartment.oc1..abc")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["compartment_header"] = req.get_header("Compartmentid")
            return _fake_response("ok")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_oci_grok("sys", "usr")
        assert captured["compartment_header"] == "ocid1.compartment.oc1..abc"

    def test_honors_env_overrides_for_region_and_model(self, monkeypatch):
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.setenv("OCI_REGION", "us-chicago-1")
        monkeypatch.setenv("OCI_GROK_MODEL", "xai.grok-4.20")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("ok")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_oci_grok("sys", "usr")
        assert captured["url"].startswith("https://inference.generativeai.us-chicago-1.oci.oraclecloud.com")
        assert captured["body"]["model"] == "xai.grok-4.20"

    def test_falls_through_to_free_chain_on_oci_error(self, monkeypatch):
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(req.full_url)
            if urllib.parse.urlparse(req.full_url).hostname.startswith("inference.generativeai"):
                raise urllib.error.URLError("connection refused")
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok("sys", "usr")
        assert provider == "groq" and text == "via groq"
        assert len(calls) == 2

    def test_search_true_skips_oci_direct_call_even_when_key_set(self, monkeypatch):
        """Confirmed real bug this pins: OCI_GENAI_API_KEY is configured in
        every real production workflow (OCI Grok is VAPE's primary
        reasoning route), so ask_oci_grok() was winning the race and
        returning at its own OCI branch on every call — meaning every
        caller's search=True never actually reached ask()'s xai_1 provider
        at all, silently making the entire Live Search rollout a no-op in
        production. OCI's endpoint has no search-grounding equivalent, so
        search=True must route around it."""
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.setenv("XAI_API_KEY_1", "key1")
        captured = {}

        def fake_urlopen(req, timeout=None):
            hostname = urllib.parse.urlparse(req.full_url).hostname
            if hostname.startswith("inference.generativeai"):
                raise AssertionError("search=True must not call OCI Grok's endpoint at all")
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("via xai with search")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _, provider = llm.ask_oci_grok("sys", "usr", tier="frontier",
                                            provider_order=llm.FRONTIER_ORDER, search=True)
        assert provider == "xai_1"
        assert captured["body"]["search_parameters"] == {"mode": "auto", "return_citations": True}

    def test_search_false_still_reaches_oci_when_key_set(self, monkeypatch):
        """The fix must not change any existing search=False (default)
        behavior — OCI Grok is still tried first exactly as before."""
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")

        def fake_urlopen(req, timeout=None):
            return _fake_response("grok via oci")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok("sys", "usr")
        assert provider == "oci_grok" and text == "grok via oci"

    def test_fallback_honors_caller_supplied_tier_and_provider_order(self, monkeypatch):
        monkeypatch.delenv("OCI_GENAI_API_KEY", raising=False)
        monkeypatch.setenv("XAI_API_KEY_1", "key1")

        def fake_urlopen(req, timeout=None):
            return _fake_response("grok reply")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok(
                "sys", "usr", tier="deep", provider_order=llm.FRONTIER_ORDER)
        assert provider == "xai_1" and text == "grok reply"

    def test_http_error_body_is_surfaced_not_swallowed(self, monkeypatch, capsys):
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        error_body = b'{"code": "NotAuthenticated", "message": "The required information to complete authentication was not provided"}'

        def fake_urlopen(req, timeout=None):
            if urllib.parse.urlparse(req.full_url).hostname.startswith("inference.generativeai"):
                raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, io.BytesIO(error_body))
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_oci_grok("sys", "usr")
        assert "NotAuthenticated" in capsys.readouterr().err

    def test_cap_reached_skips_oci_and_falls_through_to_groq(self, monkeypatch, tmp_path):
        monkeypatch.setenv("OCI_GENAI_API_KEY", "fake-oci-key")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        usage_log = tmp_path / "llm_usage.jsonl"
        findings_log = tmp_path / "findings.jsonl"
        monkeypatch.setattr(llm, "USAGE_LOG", str(usage_log))
        monkeypatch.setattr(llm, "FINDINGS_LOG", str(findings_log))
        monkeypatch.setenv("OCI_GROK_DAILY_SPEND_CAP_USD", "1.00")
        today = llm.datetime.now(llm.timezone.utc).strftime("%Y-%m-%d")
        # 1M output tokens @ $2.50/M = $2.50, already over the $1.00 cap.
        _write_usage_rows(usage_log, [
            {"ts": f"{today}T00:00:00Z", "provider": "oci_grok", "prompt_tokens": 0, "completion_tokens": 1_000_000},
        ])
        oci_attempts = {"n": 0}

        def fake_urlopen(req, timeout=None):
            if req.headers.get("Authorization") == "Bearer fake-oci-key":
                oci_attempts["n"] += 1
            return _fake_response("via groq")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok("sys", "usr")

        assert provider == "groq" and text == "via groq"
        assert oci_attempts["n"] == 0
        findings = findings_log.read_text().strip().splitlines()
        assert len(findings) == 1
        assert "oci_grok" in json.loads(findings[0])["title"]

    def test_default_cap_is_used_when_env_var_unset(self, monkeypatch):
        monkeypatch.delenv("OCI_GROK_DAILY_SPEND_CAP_USD", raising=False)
        assert llm._oci_grok_daily_cap_usd() == llm.DEFAULT_OCI_GROK_DAILY_SPEND_CAP_USD == 10.00

    def test_falls_back_to_vertex_candidate_when_configured_before_frontier(self, monkeypatch):
        """The real chain is now OCI Grok -> Vertex-tuned candidate ->
        frontier chain — when OCI is unset/errors but Vertex IS configured
        (VAPE_VERTEX_ACCESS_TOKEN set), Vertex must be reached, not skipped
        straight to FRONTIER_ORDER."""
        monkeypatch.delenv("OCI_GENAI_API_KEY", raising=False)
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setattr(llm, "_load_repo_digest", lambda: "")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_vertex_response("vertex reply")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            text, provider = llm.ask_oci_grok("sys", "usr")
        assert provider == "vertex_tuned" and text == "vertex reply"
        assert "aiplatform" in captured["url"]


class TestRepoDigest:
    """The real, regenerable repo-grounding doc (scripts/build_repo_digest.py)
    prepended ONLY to the Vertex candidate's systemInstruction — never the
    frontier ask()/ask_frontier() chain, per the explicit "only vertex"
    scope this was built to."""

    def setup_method(self):
        # _load_repo_digest() memoizes in a module global — reset it before
        # each test so tests don't leak state into each other regardless of
        # execution order.
        llm._repo_digest_cache = None

    def teardown_method(self):
        llm._repo_digest_cache = None

    def test_load_repo_digest_returns_empty_string_when_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr(llm, "REPO_DIGEST_PATH", str(tmp_path / "does-not-exist.md"))
        assert llm._load_repo_digest() == ""

    def test_load_repo_digest_reads_real_file_and_caches(self, monkeypatch, tmp_path):
        digest_path = tmp_path / "repo_digest.md"
        digest_path.write_text("REAL DIGEST CONTENT")
        monkeypatch.setattr(llm, "REPO_DIGEST_PATH", str(digest_path))
        assert llm._load_repo_digest() == "REAL DIGEST CONTENT"
        # Mutate the file after the first read — cached value must not change,
        # confirming this doesn't re-read the file on every single LLM call.
        digest_path.write_text("CHANGED")
        assert llm._load_repo_digest() == "REAL DIGEST CONTENT"

    def test_digest_is_prepended_to_vertex_system_instruction_when_present(self, monkeypatch):
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setattr(llm, "_load_repo_digest", lambda: "REAL REPO DIGEST TEXT")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_vertex_response("ok")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_vertex_candidate("my real instructions", "usr")
        system_text = captured["body"]["systemInstruction"]["parts"][0]["text"]
        assert "REAL REPO DIGEST TEXT" in system_text
        assert "my real instructions" in system_text

    def test_no_digest_means_bare_system_text_unchanged(self, monkeypatch):
        monkeypatch.setenv("VAPE_VERTEX_ACCESS_TOKEN", "fake-token")
        monkeypatch.setattr(llm, "_load_repo_digest", lambda: "")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_vertex_response("ok")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask_vertex_candidate("sys prompt", "usr")
        assert captured["body"]["systemInstruction"] == {"parts": [{"text": "sys prompt"}]}

    def test_frontier_chain_never_sees_the_repo_digest(self, monkeypatch):
        """The digest is scoped to _call_vertex_tuned() only — a bare
        ask()/ask_frontier() call (what every real production call site
        other than the 3 Vertex-wired ones still uses) must never have it
        injected."""
        monkeypatch.setattr(llm, "_load_repo_digest", lambda: "REPO DIGEST SHOULD NOT APPEAR")
        monkeypatch.setenv("GROQ_API_KEY", "groqkey")
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode())
            return _fake_response("plain reply")

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            llm.ask("sys prompt", "usr")
        system_sent = captured["body"]["messages"][0]["content"]
        assert system_sent == "sys prompt"
        assert "REPO DIGEST" not in system_sent


class TestDescribeUnavailable:
    """describe_unavailable() is the ONLY form of an all-providers-failed
    exception allowed into a customer-facing report (see
    agents/deep_dive_audit.py/external_audit.py's except branches) — the raw
    exception names internal provider identifiers (xai_1/groq/gemini/
    cerebras/oci_grok) and can embed a provider's raw HTTP error body
    verbatim, confirmed to include that provider's own internal account/org
    identifier in a real observed failure, not just a generic message."""

    def test_no_key_configured_case_is_generic(self):
        exc = RuntimeError("no LLM provider key set (need one of: GROQ_API_KEY, XAI_API_KEY_1)")
        msg = llm.describe_unavailable(exc)
        assert "GROQ_API_KEY" not in msg
        assert "XAI_API_KEY_1" not in msg
        assert "configured" in msg.lower()

    def test_all_providers_failed_case_never_leaks_provider_names_or_bodies(self):
        exc = RuntimeError(
            "all LLM providers failed/absent: xai_1:HTTP410 {\"error\":\"Live search is deprecated\"}, "
            "groq:HTTP429 {\"error\":{\"message\":\"...org_01kvrrkqgsfk4thyv722a2ttvm...\"}}, "
            "gemini:HTTP429 [...], cerebras:HTTP404 {...}"
        )
        msg = llm.describe_unavailable(exc)
        for leaked in ("xai_1", "groq", "gemini", "cerebras", "org_01kvrrkqgsfk4thyv722a2ttvm", "HTTP410", "HTTP429"):
            assert leaked not in msg, f"{leaked!r} leaked into customer-facing message: {msg!r}"
        assert "unavailable" in msg.lower() or "unreachable" in msg.lower() or "rate-limited" in msg.lower()

    def test_distinguishes_no_key_from_all_failed(self):
        no_key = llm.describe_unavailable(RuntimeError("no LLM provider key set (need one of: X)"))
        all_failed = llm.describe_unavailable(RuntimeError("all LLM providers failed/absent: xai_1:HTTP410 x"))
        assert no_key != all_failed
