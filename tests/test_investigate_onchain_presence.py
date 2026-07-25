"""Tests for agents/investigate.py::onchain_presence() — the real on-chain
eth_getCode check every investigation/deep-dive report's "Is contract"
field comes from. Hermetic: urllib.request.urlopen is mocked, no real
network call.

Real, confirmed bug this guards (2026-07-25): a live report,
audit-deep-dive-virtual-2026-07-23.md, reported the real, heavily-traded
VIRTUAL token contract as an EOA with zero code — root cause was
onchain_presence() having zero retries and silently treating ANY RPC
failure (timeout, rate limit, transient error) as "confirmed no code",
identical to a real empty eth_getCode response. These tests pin the fix:
a failing/erroring RPC now reports an honest is_contract=None ("unknown"),
never a fabricated False, and is retried before giving up.
"""
import json
import time
import urllib.error
from unittest import mock

from agents.investigate import onchain_presence


def _fake_response(result):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": result}).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return body
    return Resp()


def test_real_contract_reports_is_contract_true_with_code_size():
    with mock.patch("urllib.request.urlopen", return_value=_fake_response("0x6080604052")):
        result = onchain_presence("0x" + "aa" * 20, "8453")
    assert result["is_contract"] is True
    assert result["code_size_bytes"] == 5


def test_real_eoa_reports_is_contract_false():
    with mock.patch("urllib.request.urlopen", return_value=_fake_response("0x")):
        result = onchain_presence("0x" + "aa" * 20, "8453")
    assert result == {"is_contract": False, "code_size_bytes": 0}


def test_rpc_failure_reports_honest_unknown_not_fabricated_eoa(monkeypatch):
    """The exact regression: every attempt errors (timeout/connection
    reset/etc) — must report is_contract=None, never False."""
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        result = onchain_presence("0x" + "aa" * 20, "8453")
    assert result["is_contract"] is None
    assert result["code_size_bytes"] is None
    assert "timed out" in result["error"]


def test_rpc_retries_before_giving_up(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def flaky(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.URLError("connection reset")
        return _fake_response("0x6080604052")

    with mock.patch("urllib.request.urlopen", side_effect=flaky):
        result = onchain_presence("0x" + "aa" * 20, "8453")
    assert calls["n"] == 3
    assert result["is_contract"] is True


def test_rpc_stops_retrying_after_three_attempts(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_: None)
    calls = {"n": 0}

    def always_fails(req, timeout=None):
        calls["n"] += 1
        raise urllib.error.URLError("connection reset")

    with mock.patch("urllib.request.urlopen", side_effect=always_fails):
        result = onchain_presence("0x" + "aa" * 20, "8453")
    assert calls["n"] == 3
    assert result["is_contract"] is None
