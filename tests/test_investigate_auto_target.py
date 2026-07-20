"""Hermetic test for agents.investigate.auto_target()'s chain-fallback fix.

Real bug this guards against: chains_to_try used to be just [chain] (for the
~2/3 of hours that pick Base directly) or [chain, "8453"] otherwise — if the
one or two chains tried were fully exhausted (every mover candidate already
in the ledger), auto_target() returned None outright with zero fallback,
silently starving agents/data_agent.py (Base-only) of any recruitment
opportunity for the rest of that cycle. Confirmed live in production: two
consecutive real GitHub Actions runs (2026-07-20 17:03 and 19:13 UTC) both
logged "no auto target found this cycle" while chains_to_try was ["8453"]
only. This test pins the fix: every other known chain now gets a turn before
giving up.
"""
import os
import re
import sys
import types
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents import investigate as inv

EXHAUSTED_ADDR = "0x1111111111111111111111111111111111111111"
FRESH_ADDR = "0x2222222222222222222222222222222222222222"

_DEX_SLUG_FOR_GECKO = {info["gecko"]: info["dex"] for info in inv.EVM_CHAINS.values()}


def _fake_get_evm_movers(network, limit=10):
    if network == "base":
        return {"biggest_movers": [{"name": "STALE/USD", "change_24h_pct": 5}]}
    return {"biggest_movers": [{"name": f"FRESH-{network}/USD", "change_24h_pct": 5}]}


def _fake_get(url, timeout=12):
    m = re.search(r"q=([^&]+)", url)
    q = urllib.parse.unquote(m.group(1)) if m else ""
    if q.startswith("FRESH-"):
        network = q[len("FRESH-"):]
        return {"pairs": [{"chainId": _DEX_SLUG_FOR_GECKO.get(network, network),
                            "baseToken": {"address": FRESH_ADDR}}]}
    return {"pairs": [{"chainId": "base", "baseToken": {"address": EXHAUSTED_ADDR}}]}


def test_auto_target_falls_back_past_an_exhausted_base_pool(monkeypatch):
    monkeypatch.setattr(inv, "_pick_chain_for_hour", lambda hour: "8453")
    monkeypatch.setattr(inv, "DF", types.SimpleNamespace(get_evm_movers=_fake_get_evm_movers))
    monkeypatch.setattr(inv, "_get", _fake_get)
    # Base's only candidate is already in the ledger — the exact "exhausted
    # pool" condition that used to make auto_target() give up immediately.
    # Value must be truthy — `ledger.get(key)` is used directly as a boolean
    # gate in auto_target(), so an empty-dict value would (wrongly) read as
    # "not in the ledger" and defeat the whole point of this test.
    monkeypatch.setattr(inv, "_load_ledger", lambda: {inv._ledger_key(EXHAUSTED_ADDR, "8453"): {"verdict": "PROCEED"}})

    picked = inv.auto_target()

    assert picked is not None, "auto_target() gave up instead of falling back to another chain"
    assert picked["address"] == FRESH_ADDR
    assert picked["chain"] != "8453"


def test_auto_target_returns_none_only_when_every_chain_is_exhausted(monkeypatch):
    monkeypatch.setattr(inv, "_pick_chain_for_hour", lambda hour: "8453")
    monkeypatch.setattr(inv, "DF", types.SimpleNamespace(
        get_evm_movers=lambda network, limit=10: {"biggest_movers": [{"name": "STALE/USD", "change_24h_pct": 5}]}))
    monkeypatch.setattr(inv, "_get", _fake_get)
    # Value must be truthy — `ledger.get(key)` is used directly as a boolean
    # gate in auto_target(), so an empty-dict value would (wrongly) read as
    # "not in the ledger" and defeat the whole point of this test.
    monkeypatch.setattr(inv, "_load_ledger", lambda: {inv._ledger_key(EXHAUSTED_ADDR, "8453"): {"verdict": "PROCEED"}})

    assert inv.auto_target() is None
