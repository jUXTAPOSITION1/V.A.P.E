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
    def __init__(self, status_code=200, body=None, text="", headers=None):
        self.status_code = status_code
        self._body = body if body is not None else {}
        self.text = text
        self.headers = headers if headers is not None else {}

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


def test_no_offering_this_module_hires_exceeds_the_price_ceiling():
    """MAX_OFFERING_PRICE_USD is the documented contract for what this
    module will ever hire -- every real entry in OFFERING_PARAMS and
    CATALOG_OFFERINGS must actually clear it, not just the ones priced
    individually in SCAN_TIER_PRICE_USD."""
    for name in data_agent.OFFERING_PARAMS:
        assert data_agent._price_for(name) <= data_agent.MAX_OFFERING_PRICE_USD
    for name, _prefix, _kind in data_agent.CATALOG_OFFERINGS:
        assert data_agent._price_for(name) <= data_agent.MAX_OFFERING_PRICE_USD


def test_prefix_for_matches_scan_tier_membership():
    assert data_agent._prefix_for("dossier_check") == "scan"
    assert data_agent._prefix_for("rug_pull_alert") == "scan"
    assert data_agent._prefix_for("market_intel") == "scan"
    assert data_agent._prefix_for("token_intel") == "data"


def test_known_evm_chain_is_no_longer_rejected(monkeypatch, tmp_path):
    """Real bug this pins the fix for: run_for_investigation() used to
    hard-reject every chain except Base even though CHAIN_META already has a
    confirmed-correct DefiLlama slug for 7 chains (Ethereum included) and
    run_catalog_sweep() already proved the same offering set works fine
    against all of them. Ethereum (chain id "1") must now proceed past the
    chain gate and actually attempt a hire."""
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path))

    def responder(url, params):
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(responder))
    monkeypatch.setattr(data_agent.random, "sample", lambda seq, k: ["dossier_check"])

    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="1")
    assert result["hired"][0]["paid"]
    assert result["hired"][0]["params"] == {"address": "0x" + "aa" * 20, "chain": "1"}


def test_unknown_chain_is_skipped_with_no_network_attempt(monkeypatch):
    monkeypatch.setenv("DATA_AGENT_PRIVATE_KEY", "0x" + "11" * 32)
    called = {"n": 0}
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: called.update(n=called["n"] + 1))
    result = data_agent.run_for_investigation("0x" + "aa" * 20, chain="999999")
    assert result["hired"] == []
    assert "999999" in result["note"]
    assert called["n"] == 0  # chain gate rejects before ever touching the session/network


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
    # OFFERING_PARAMS now spans several real prices (see SCAN_TIER_PRICE_USD)
    # -- whichever offering actually got picked, not a flat $0.01.
    expected = round(sum(data_agent._price_for(h["offering"]) for h in result["hired"]), 2)
    assert result["cost_usd"] == expected
    assert data_agent._CDP_STATE.count_today() == n
    ledger_path = data_agent._CDP_STATE.ledger_path
    assert __import__("os").path.exists(ledger_path)
    logged = json.loads(open(ledger_path).read().strip().splitlines()[-1])
    assert logged["paid"] == n


def test_run_for_investigation_routes_scan_tier_pick_to_scan_prefix(monkeypatch, tmp_path):
    """Real bug this pins: OFFERING_PARAMS used to be all $0.01 DL data-tier
    offerings, so _run()/_run_growth() never passed hire() a prefix and it
    defaulted to "data". Once rug_pull_alert/dossier_check/market_intel (the
    scan tier, up to MAX_OFFERING_PRICE_USD) were added, a pick landing on
    one of those without the fix would hit the wrong route (/data/... instead
    of /scan/...) and silently fail to ever actually pay for it."""
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path))
    monkeypatch.setattr(data_agent.random, "sample", lambda seq, k: ["dossier_check"])

    seen = {}

    def responder(url, params):
        seen["url"] = url
        offering = url.rsplit("/", 1)[-1]
        return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})

    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(responder))

    result = data_agent.run_for_investigation("0x" + "bb" * 20, chain="8453")
    assert "/scan/dossier_check" in seen["url"]
    assert result["hired"][0]["params"] == {"address": "0x" + "bb" * 20, "chain": "8453"}
    assert result["cost_usd"] == 0.10


def test_offering_params_resolves_per_chain_defillama_slug():
    """_offering_params() must resolve each chain's own confirmed-correct
    DefiLlama slug (CHAIN_META), not hardcode Base's -- e.g. Polygon's fee
    slug is "polygon", not "base"."""
    assert data_agent._offering_params("token_intel", "0xabc", "137") == {"address": "0xabc", "chain": "polygon"}
    assert data_agent._offering_params("chain_overview", "0xabc", "137") == {"chain": "Polygon"}
    assert data_agent._offering_params("dossier_check", "0xabc", "137") == {"address": "0xabc", "chain": "137"}
    assert data_agent._offering_params("yields", "0xabc", "137") == {}
    # Unknown chain id falls back to Base rather than crashing.
    assert data_agent._offering_params("token_intel", "0xabc", "999999") == {"address": "0xabc", "chain": "base"}


def test_hire_reports_unpaid_on_non_200():
    session = _FakeSession(lambda url, params: _FakeResponse(402, text="payment required"))
    deliverable, paid = data_agent.hire(session, "token_intel", {"address": "0x" + "aa" * 20})
    assert paid is False
    assert "error" in deliverable
    assert "settlement" not in deliverable  # no PAYMENT-RESPONSE header -> nothing to decode


def test_hire_surfaces_decoded_settlement_error_on_rejected_payment():
    # The worker's 402 body is always the literal `{}` regardless of whether
    # a payment was ever attempted -- the x402 SDK instead puts the real
    # settlement outcome (success/error_reason/error_message) base64-encoded
    # in the PAYMENT-RESPONSE header on a rejected paid retry.
    import base64
    settle = {"success": False, "error_reason": "insufficient_funds",
              "error_message": "payer balance too low", "transaction": "0xdead"}
    header = base64.b64encode(json.dumps(settle).encode()).decode()
    session = _FakeSession(lambda url, params: _FakeResponse(
        402, text="{}", headers={"PAYMENT-RESPONSE": header}))
    deliverable, paid = data_agent.hire(session, "token_intel", {"address": "0x" + "aa" * 20})
    assert paid is False
    assert deliverable["settlement"]["error_reason"] == "insufficient_funds"


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


def test_patch_x402_missing_scheme_network_injects_top_level_fields(monkeypatch):
    # Confirmed via a live payload capture (scripts/diag_x402_payload.py):
    # CDP's real /settle endpoint rejects every v2 paymentPayload with HTTP
    # 400 "invalid request body" because the x402 SDK's own V2 model omits
    # top-level scheme/network (it only nests them under `accepted`, per the
    # SDK's own get_scheme()/get_network() docstrings: "V2 uses
    # accepted.scheme"/"accepted.network"). This asserts the wire-level
    # patch actually adds them back without touching the signed payload.
    monkeypatch.setattr(data_agent, "_X402_SCHEME_NETWORK_PATCHED", False)
    data_agent._patch_x402_missing_scheme_network()

    import base64

    from x402.http import x402_http_client_base as base_mod
    from x402.schemas import PaymentPayload, PaymentRequirements

    req = PaymentRequirements(
        scheme="exact",
        network="eip155:8453",
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        amount="10000",
        payTo="0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15",
        maxTimeoutSeconds=300,
        extra={"name": "USD Coin", "version": "2"},
    )
    payload = PaymentPayload(
        x402Version=2,
        payload={
            "authorization": {
                "from": "0xabc", "to": "0xdef", "value": "10000",
                "validAfter": "0", "validBefore": "123", "nonce": "0x00",
            },
            "signature": "0xsig",
        },
        accepted=req,
    )
    header_val = base_mod.encode_payment_signature_header(payload)
    decoded = json.loads(base64.b64decode(header_val))
    assert decoded["scheme"] == "exact"
    assert decoded["network"] == "eip155:8453"
    # the signed authorization + signature themselves are untouched
    assert decoded["payload"]["signature"] == "0xsig"
    assert decoded["payload"]["authorization"]["nonce"] == "0x00"
