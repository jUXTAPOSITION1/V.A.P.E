"""Tests for agents/data_agent.py — DATA AGENT's own quota/wallet-safety
logic and the hire loop, independent of any real x402/network call.

Hermetic: no real private key, no real HTTP call, no real x402 SDK traffic.
_build_session's own signing/network path is exercised only through a fake
session double so these tests never touch the real x402 SDK or worker.
"""
import json

from eth_account import Account

from agents import data_agent


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


def test_non_base_chain_is_skipped_with_no_network_attempt(monkeypatch):
    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", "0x" + "11" * 32)
    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="1")
    assert result["hired"] == []
    assert "8453" in result["note"]


def test_missing_key_is_skipped(monkeypatch, tmp_path):
    # Needs a fresh QUOTA_PATH — the real skillforge/memory/data_agent_quota.json
    # accumulates a real last_ts from real automated runs, which would otherwise
    # make this hit the unrelated 2h-interval gate instead of the missing-key check.
    monkeypatch.setattr(data_agent, "QUOTA_PATH", str(tmp_path / "data_agent_quota.json"))
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
    session = data_agent._build_session()
    assert session is None


def test_quota_tracking_persists_and_resets_daily(monkeypatch, tmp_path):
    quota_path = tmp_path / "data_agent_quota.json"
    monkeypatch.setattr(data_agent, "QUOTA_PATH", str(quota_path))

    assert data_agent._remaining_today() == data_agent.DAILY_CAP
    data_agent._record_hires(4)
    assert data_agent._remaining_today() == data_agent.DAILY_CAP - 4
    data_agent._record_hires(3)
    assert data_agent._remaining_today() == data_agent.DAILY_CAP - 7

    # Simulate a stale entry from a previous day — must reset, not accumulate.
    stale = json.loads(quota_path.read_text())
    stale["date"] = "2000-01-01"
    quota_path.write_text(json.dumps(stale))
    assert data_agent._remaining_today() == data_agent.DAILY_CAP


def test_daily_cap_reached_skips_without_touching_session(monkeypatch, tmp_path):
    quota_path = tmp_path / "data_agent_quota.json"
    monkeypatch.setattr(data_agent, "QUOTA_PATH", str(quota_path))
    data_agent._record_hires(data_agent.DAILY_CAP - 1)  # only 1 slot left, below MIN_PER_RUN

    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", "0x" + "11" * 32)
    called = {"n": 0}
    monkeypatch.setattr(data_agent, "_build_session", lambda: called.update(n=called["n"] + 1))
    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="8453")
    assert result["hired"] == []
    assert "cap reached" in result["note"]
    assert called["n"] == 0  # never even tried to build a session once capped


def test_run_for_investigation_hires_between_min_and_max(monkeypatch, tmp_path):
    quota_path = tmp_path / "data_agent_quota.json"
    ledger_path = tmp_path / "data_agent_ledger.jsonl"
    monkeypatch.setattr(data_agent, "QUOTA_PATH", str(quota_path))
    monkeypatch.setattr(data_agent, "LEDGER_PATH", str(ledger_path))

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda: _FakeSession(responder))

    result = data_agent.run_for_investigation("0x" + "bb" * 20, chain="8453")
    n = len(result["hired"])
    assert data_agent.MIN_PER_RUN <= n <= data_agent.MAX_PER_RUN
    assert all(h["paid"] for h in result["hired"])
    assert result["cost_usd"] == round(n * 0.01, 2)
    assert data_agent._remaining_today() == data_agent.DAILY_CAP - n
    assert ledger_path.exists()
    logged = json.loads(ledger_path.read_text().strip().splitlines()[-1])
    assert logged["paid"] == n


def test_hire_reports_unpaid_on_non_200(monkeypatch):
    session = _FakeSession(lambda url, params: _FakeResponse(402, text="payment required"))
    deliverable, paid = data_agent.hire(session, "token_intel", {"address": "0x" + "aa" * 20})
    assert paid is False
    assert "error" in deliverable


def test_second_call_within_2h_is_skipped_without_touching_session(monkeypatch, tmp_path):
    quota_path = tmp_path / "data_agent_quota.json"
    ledger_path = tmp_path / "data_agent_ledger.jsonl"
    monkeypatch.setattr(data_agent, "QUOTA_PATH", str(quota_path))
    monkeypatch.setattr(data_agent, "LEDGER_PATH", str(ledger_path))

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda: _FakeSession(responder))

    first = data_agent.run_for_investigation("0x" + "cc" * 20, chain="8453")
    assert len(first["hired"]) > 0  # real hire happened, last_ts is now "now"

    called = {"n": 0}
    monkeypatch.setattr(data_agent, "_build_session", lambda: called.update(n=called["n"] + 1))
    second = data_agent.run_for_investigation("0x" + "dd" * 20, chain="8453")
    assert second["hired"] == []
    assert "2h interval" in second["note"]
    assert called["n"] == 0  # gated before ever building a session


def test_call_after_2h_elapsed_is_allowed(monkeypatch, tmp_path):
    quota_path = tmp_path / "data_agent_quota.json"
    monkeypatch.setattr(data_agent, "QUOTA_PATH", str(quota_path))

    from datetime import datetime, timedelta, timezone
    stale_ts = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat().replace("+00:00", "Z")
    quota_path.write_text(json.dumps({"date": data_agent._today(), "count": 0, "last_ts": stale_ts}))

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "LEDGER_PATH", str(quota_path.parent / "ledger.jsonl"))
    monkeypatch.setattr(data_agent, "_build_session", lambda: _FakeSession(responder))

    result = data_agent.run_for_investigation("0x" + "ee" * 20, chain="8453")
    assert len(result["hired"]) > 0


def test_hire_reports_paid_on_200_even_if_deliverable_reports_error(monkeypatch):
    # A real upstream miss still means the x402 payment already settled —
    # same as any other paid job that comes back with "no data".
    session = _FakeSession(lambda url, params: _FakeResponse(
        200, {"offering": "bridges", "status": "error", "error": "upstream miss"}))
    deliverable, paid = data_agent.hire(session, "bridges", {})
    assert paid is True
    assert deliverable == {"offering": "bridges", "status": "error", "error": "upstream miss"}
