"""Tests for agents/data_agent.py's decoupled cadence + catalog-sweep stream
(run_standalone(), run_catalog_sweep(), _fresh_candidate(), the token
database helpers) — see the module docstring for the full design.

Hermetic: no real network call, no real x402 SDK traffic. data_fetchers'
GeckoTerminal/DexScreener calls and the /trending-base lookup are exercised
only through fakes.
"""
import json
import os

from agents import data_agent, data_fetchers


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


def _fresh_state(tmp_path, name="test"):
    state = data_agent._State(name)
    state.quota_path = str(tmp_path / f"{name}_quota.json")
    state.ledger_path = str(tmp_path / f"{name}_ledger.jsonl")
    return state


def _ok_responder(url, params):
    offering = url.rsplit("/", 1)[-1]
    return _FakeResponse(200, {"offering": offering, "status": "ok", "deliverable": {"ok": True}})


# ── _fresh_candidate() ───────────────────────────────────────────────────────

def test_fresh_candidate_resolves_a_base_mover_and_skips_recently_seen(monkeypatch, tmp_path):
    db_path = tmp_path / "token_database.jsonl"
    monkeypatch.setattr(data_agent, "TOKEN_DB_PATH", str(db_path))

    stale_addr = "0x" + "aa" * 20
    fresh_addr = "0x" + "bb" * 20
    with open(db_path, "w") as f:
        f.write(json.dumps({
            "ts": data_agent.datetime.now(data_agent.timezone.utc).isoformat().replace("+00:00", "Z"),
            "address": stale_addr, "chain": "8453", "symbol": "STALE", "name": "Stale",
            "source": "base", "offering": "token_intel",
        }) + "\n")

    def fake_get_evm_movers(network, limit=10):
        if network != "base":
            return {"biggest_movers": []}
        return {"biggest_movers": [
            {"name": "STALE/USD", "change_24h_pct": 5},
            {"name": "FRESH/USD", "change_24h_pct": 3},
        ]}

    def fake_resolve(mover_name, dex_slug):
        return {
            "STALE": (stale_addr, "STALE"),
            "FRESH": (fresh_addr, "FRESH"),
        }[mover_name.split("/")[0]]

    monkeypatch.setattr(data_fetchers, "get_evm_movers", fake_get_evm_movers)
    monkeypatch.setattr(data_agent, "_resolve_mover_address", fake_resolve)
    monkeypatch.setattr(data_agent.random, "sample", lambda seq, k: list(seq))

    found = data_agent._fresh_candidate(only_base=True)
    assert found is not None
    addr, chain_id, sym, name, source = found
    assert addr == fresh_addr  # the stale (already-recorded) candidate was skipped
    assert chain_id == "8453"
    assert source == "base"


def test_fresh_candidate_returns_none_when_every_source_is_empty(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "TOKEN_DB_PATH", str(tmp_path / "empty.jsonl"))
    monkeypatch.setattr(data_fetchers, "get_evm_movers", lambda network, limit=10: {"biggest_movers": []})
    import requests
    monkeypatch.setattr(requests, "get", lambda *a, **k: _FakeResponse(503))

    assert data_agent._fresh_candidate() is None


# ── token database round-trip ────────────────────────────────────────────────

def test_record_and_read_back_recent_token_db(monkeypatch, tmp_path):
    db_path = tmp_path / "token_database.jsonl"
    monkeypatch.setattr(data_agent, "TOKEN_DB_PATH", str(db_path))

    addr = "0x" + "cc" * 20
    data_agent._record_token_db(addr, "8453", "SYM", "Name", "base", "exploit_check")

    assert os.path.exists(db_path)
    recent = data_agent._recent_token_db_addresses()
    assert ("8453", addr.lower()) in recent


def test_old_token_db_entries_fall_outside_cooldown(monkeypatch, tmp_path):
    db_path = tmp_path / "token_database.jsonl"
    monkeypatch.setattr(data_agent, "TOKEN_DB_PATH", str(db_path))
    old_ts = (data_agent.datetime.now(data_agent.timezone.utc)
              - data_agent.timedelta(hours=data_agent.TOKEN_DB_COOLDOWN_HOURS + 1)).isoformat().replace("+00:00", "Z")
    addr = "0x" + "dd" * 20
    with open(db_path, "w") as f:
        f.write(json.dumps({"ts": old_ts, "address": addr, "chain": "8453", "symbol": "OLD",
                            "name": "Old", "source": "base", "offering": "token_intel"}) + "\n")

    recent = data_agent._recent_token_db_addresses()
    assert ("8453", addr.lower()) not in recent


# ── run_standalone() ─────────────────────────────────────────────────────────

def test_run_standalone_self_sources_a_candidate(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path, "standalone"))
    fresh_addr = "0x" + "ee" * 20
    monkeypatch.setattr(data_agent, "_fresh_candidate",
                        lambda only_base=False: (fresh_addr, "8453", "SYM", "Name", "base"))
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(_ok_responder))

    result = data_agent.run_standalone()
    assert len(result["hired"]) == 1
    logged = json.loads(open(data_agent._CDP_STATE.ledger_path).read().strip().splitlines()[-1])
    assert logged["target"] == fresh_addr


def test_run_standalone_skips_cleanly_when_no_candidate_found(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_STATE", _fresh_state(tmp_path, "standalone_empty"))
    monkeypatch.setattr(data_agent, "_fresh_candidate", lambda only_base=False: None)
    called = {"n": 0}
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: called.update(n=called["n"] + 1))

    result = data_agent.run_standalone()
    assert result["hired"] == []
    assert "no fresh" in result["note"]
    assert called["n"] == 0  # never even tried to build a session without a candidate


# ── run_catalog_sweep() ──────────────────────────────────────────────────────

def test_catalog_sweep_address_offering_records_token_db(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_CATALOG_STATE", _fresh_state(tmp_path, "catalog"))
    db_path = tmp_path / "token_database.jsonl"
    monkeypatch.setattr(data_agent, "TOKEN_DB_PATH", str(db_path))
    fresh_addr = "0x" + "ff" * 20
    monkeypatch.setattr(data_agent, "_fresh_candidate",
                        lambda only_base=False: (fresh_addr, "8453", "SYM", "Name", "base"))
    monkeypatch.setattr(data_agent.random, "choice", lambda seq: ("exploit_check", "scan", "address"))
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(_ok_responder))

    result = data_agent.run_catalog_sweep()
    assert result["hired"][0]["offering"] == "exploit_check"
    assert result["hired"][0]["paid"] is True
    assert os.path.exists(db_path)
    rec = json.loads(open(db_path).read().strip().splitlines()[-1])
    assert rec["address"] == fresh_addr
    assert rec["offering"] == "exploit_check"


def test_catalog_sweep_no_input_offering_needs_no_candidate(monkeypatch, tmp_path):
    monkeypatch.setattr(data_agent, "_CDP_CATALOG_STATE", _fresh_state(tmp_path, "catalog_none"))
    called = {"n": 0}

    def fail_if_called(only_base=False):
        called["n"] += 1
        return None

    monkeypatch.setattr(data_agent, "_fresh_candidate", fail_if_called)
    monkeypatch.setattr(data_agent.random, "choice", lambda seq: ("bridges", "data", "none"))
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(_ok_responder))

    result = data_agent.run_catalog_sweep()
    assert result["hired"][0]["offering"] == "bridges"
    assert result["hired"][0]["params"] == {}
    assert called["n"] == 0  # a no-input offering never touches candidate sourcing


def test_catalog_sweep_gate_is_independent_of_main_stream(monkeypatch, tmp_path):
    # Exhaust the main stream's daily cap — the catalog stream must be
    # completely unaffected, since each has its own _State file.
    main_state = _fresh_state(tmp_path, "main_exhausted")
    main_state.record_hires(data_agent.DAILY_CAP)
    monkeypatch.setattr(data_agent, "_CDP_STATE", main_state)
    monkeypatch.setattr(data_agent, "_CDP_CATALOG_STATE", _fresh_state(tmp_path, "catalog_fresh"))
    monkeypatch.setattr(data_agent.random, "choice", lambda seq: ("bridges", "data", "none"))
    monkeypatch.setattr(data_agent, "_build_session", lambda tag: _FakeSession(_ok_responder))

    main_result = data_agent.run_for_investigation("0x" + "11" * 20, chain="8453")
    assert "cap reached" in main_result["note"]

    catalog_result = data_agent.run_catalog_sweep()
    assert catalog_result["hired"][0]["paid"] is True
