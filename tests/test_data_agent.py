"""Tests for agents/data_agent.py — DATA AGENT's own quota/wallet-safety
logic and the hire loop, independent of any real x402/network call.

Hermetic: no real private key, no real HTTP call, no real x402 SDK traffic.
_build_session's own signing/network path is exercised only through a fake
session double so these tests never touch the real x402 SDK or worker.

Each test gets a fresh data_agent._State pointed at tmp_path (via monkeypatch
on module-level _CDP_STATE) rather than the real shared quota/ledger files,
so tests never interfere with each other or with real automated runs.
"""
import json

import pytest
from eth_account import Account

from agents import data_agent


@pytest.fixture(autouse=True)
def _isolated_growth_epoch(tmp_path, monkeypatch):
    """run_for_investigation()/run_standalone() now compute a growing daily
    target on every call (see data_agent.py's module docstring), which reads/
    writes a real, shared epoch file on first use — never let a test touch
    that real repo file. Every test in this module gets its own fresh epoch
    (day_index always 0, i.e. today == epoch) unless it explicitly backdates
    the epoch itself."""
    monkeypatch.setattr(data_agent, "GROWTH_EPOCH_PATH", str(tmp_path / "growth_epoch.json"))


class _FakeResponse:
    def __init__(self, status_code=200, body=None, text=""):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = text

    def json(self):
        return self._body


class _FakeSession:
    def __init__(self, responder):
        self._responder = responder

    def get(self, url, params=None, timeout=None):
        return self._responder(url, params)


def _fresh_state(tmp_path):
    state = data_agent._State("test_data_agent")
    state.quota_path = str(tmp_path / "quota.json")
    state.ledger_path = str(tmp_path / "ledger.jsonl")
    return state


def test_non_base_chain_is_skipped_with_no_network_attempt(monkeypatch):
    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", "0x" + "11" * 32)
    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="1")
    assert result["hired"] == []
    assert "8453" in result["note"]


def test_missing_key_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path))
    monkeypatch.delenv("DATA_AGENT_PRIVATE_KEY", raising=False)
    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="8453")
    assert result["hired"] == []
    assert "DATA_AGENT_PRIVATE_KEY" in result["note"]


def test_wallet_mismatch_refuses_to_spend(monkeypatch):
    # A real, validly-formatted private key that does NOT derive
    # EXPECTED_WALLET — must refuse rather than sign with the wrong identity.
    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", "0x" + "22" * 32)
    derived = Account.from_key("0x" + "22" * 32).address
    assert derived.lower() != data_agent.EXPECTED_WALLET.lower()
    session = data_agent._build_session("data-agent")
    assert session is None


def test_quota_tracking_persists_and_resets_daily(tmp_path):
    state = _fresh_state(tmp_path)

    assert state.remaining_today() == data_agent.DAILY_CAP
    state.record_hires(4)
    assert state.remaining_today() == data_agent.DAILY_CAP - 4
    state.record_hires(3)
    assert state.remaining_today() == data_agent.DAILY_CAP - 7

    # Simulate a stale entry from a previous day — must reset, not accumulate.
    stale = json.loads(open(state.quota_path).read())
    stale["date"] = "2000-01-01"
    with open(state.quota_path, "w") as f:
        json.dump(stale, f)
    assert state.remaining_today() == data_agent.DAILY_CAP


def test_growth_target_already_met_today_skips_without_touching_session(monkeypatch, tmp_path):
    state = _fresh_state(tmp_path)
    main_target, _ = data_agent._daily_targets()
    state.record_hires(main_target)  # today's growing minimum already hit
    monkeypatch.setattr(data_agent, "_CDP_STATE", state)

    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", "0x" + "11" * 32)
    called = {"n": 0}
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: called.update(n=called["n"] + 1))
    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="8453")
    assert result["hired"] == []
    assert "not due yet" in result["note"]
    assert called["n"] == 0  # never even tried to build a session once today's target is met


def test_run_for_investigation_hires_exactly_one(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path))

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(responder))

    result = data_agent.run_for_investigation("0x" + "bb" * 20, chain="8453")
    n = len(result["hired"])
    assert n == data_agent.HIRES_PER_RUN == 1
    assert all(h["paid"] for h in result["hired"])
    assert result["cost_usd"] == round(n * 0.01, 2)
    assert data_agent._CDP_STATE.count_today() == n
    ledger_path = data_agent._CDP_STATE.ledger_path
    assert __import__("os").path.exists(ledger_path)
    logged = json.loads(open(ledger_path).read().strip().splitlines()[-1])
    assert logged["paid"] == n


def test_hire_reports_unpaid_on_non_200():
    session = _FakeSession(lambda url, params: _FakeResponse(402, text="payment required"))
    deliverable, paid = data_agent.hire(session, "token_intel", {"address": "0x" + "aa" * 20})
    assert paid is False
    assert "error" in deliverable


def test_immediate_second_call_is_not_yet_due_without_touching_session(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path))

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(responder))

    first = data_agent.run_for_investigation("0x" + "cc" * 20, chain="8453")
    assert len(first["hired"]) > 0  # real hire happened, last_ts is now "now"

    called = {"n": 0}
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: called.update(n=called["n"] + 1))
    second = data_agent.run_for_investigation("0x" + "dd" * 20, chain="8453")
    assert second["hired"] == []
    assert "not due yet" in second["note"]
    assert called["n"] == 0  # gated before ever building a session


def test_call_after_1hr_elapsed_is_allowed(monkeypatch, tmp_path):
    state = _fresh_state(tmp_path)
    from datetime import datetime, timedelta, timezone
    stale_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z")
    with open(state.quota_path, "w") as f:
        json.dump({"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "count": 0, "last_ts": stale_ts}, f)
    monkeypatch.setattr(data_agent, "_CDP_STATE", state)

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(responder))

    result = data_agent.run_for_investigation("0x" + "ee" * 20, chain="8453")
    assert len(result["hired"]) > 0


def test_hire_reports_paid_on_200_even_if_deliverable_reports_error():
    # A real upstream miss still means the x402 payment already settled —
    # same as any other paid job that comes back with "no data".
    session = _FakeSession(lambda url, params: _FakeResponse(
        200, {"offering": "bridges", "status": "error", "error": "upstream miss"}))
    deliverable, paid = data_agent.hire(session, "bridges", {})
    assert paid is True
    assert deliverable == {"offering": "bridges", "status": "error", "error": "upstream miss"}


def test_build_session_tags_client_header(monkeypatch):
    # EXPECTED_WALLET must be swapped for a key this test actually holds —
    # the real wallet's key isn't available (or safe) to use in a test.
    fake_key = "0x" + "33" * 32
    monkeypatch.setattr(data_agent, "EXPECTED_WALLET", Account.from_key(fake_key).address)
    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", fake_key)
    session = data_agent._build_session("data-agent-vapor")
    assert session.headers["X-VAPE-Client"] == "data-agent-vapor"
