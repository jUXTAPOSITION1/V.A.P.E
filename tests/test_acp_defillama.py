"""DefiLlama tools as ACP/x402 offerings — cross-surface parity + dispatch.

The 13 DefiLlama micro-services must stay identical across the four places
that declare them, or a buyer hires a name one surface can't fulfill:
  - agents/acp_fulfill.py           HANDLERS (what actually runs)
  - agents/publish_reputation.py    DL_OFFERINGS (the published catalog)
  - agents/x402_directory_register.py DATA_OFFERINGS (the x402 directory)
  - worker/src/dataHandlers.ts       DL_OFFERINGS (the paid worker routes)

These tests pin that parity, and that every ACP handler dispatches to the
right agents/defillama.py function with the right params — all hermetic
(the defillama module is stubbed; no network).
"""
import re
import sys
import types
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


# The 13 market-data tools, by name (no prefix). This literal set is the
# contract every surface must match — if a tool is added/renamed, this and all
# four surfaces move together or the test fails.
#
# `derivatives` was retired 2026-07-14: DefiLlama moved overview/derivatives
# behind its Pro API tier with no free equivalent, so real x402/ACP customers
# paying for it got charged for an error — the offering was pulled rather
# than sold undeliverable. See agents/defillama.py's module docstring.
DATA_TOOLS = {
    "token_intel", "token_chart", "protocol", "protocol_fees", "unlocks", "treasury",
    "chain_protocols", "chain_overview", "chain_fees", "dex_volumes",
    "yields", "stablecoins", "bridges",
}
# wallet_pnl_deepdive is the one /data/* tool NOT backed by DefiLlama — it's
# Codex-backed (agents/codex_data.py / worker/src/lib/codex.ts) and priced at
# $0.25 instead of the uniform $0.01. It shares the same DATA_OFFERINGS dict /
# worker DL_OFFERINGS array / route prefix as the 13 DefiLlama tools, so it's
# included in the cross-surface-parity check below but excluded from the
# "13 DefiLlama tools, all priced $0.01" assertions.
NON_DEFILLAMA_DATA_TOOLS = {"wallet_pnl_deepdive"}
ALL_DATA_TOOLS = DATA_TOOLS | NON_DEFILLAMA_DATA_TOOLS


def test_data_offering_names_identical_across_all_surfaces():
    from agents.publish_reputation import DL_NAMES
    from agents.x402_directory_register import DATA_OFFERINGS
    from agents.acp_fulfill import HANDLERS
    # worker/src/dataHandlers.ts declares the data tools as `name: "..."` (the
    # only place in that file that does), so this captures exactly the tier.
    worker = set(re.findall(r'name:\s*"([a-z_]+)"', (ROOT / "worker/src/dataHandlers.ts").read_text()))
    assert DL_NAMES == DATA_TOOLS                      # published DefiLlama-only catalog subset
    assert set(DATA_OFFERINGS) == ALL_DATA_TOOLS       # x402 directory (DefiLlama + Codex)
    assert worker == ALL_DATA_TOOLS                    # paid worker routes
    assert ALL_DATA_TOOLS <= set(HANDLERS)             # every data tool is ACP-fulfillable


def test_data_offerings_all_priced_one_cent():
    from agents.publish_reputation import DL_OFFERINGS
    from agents.x402_directory_register import DATA_OFFERINGS
    assert len(DL_OFFERINGS) == 13
    assert all(price == 0.01 for _n, price, _s in DL_OFFERINGS)
    assert all(meta[0] == "0.01" for name, meta in DATA_OFFERINGS.items() if name in DATA_TOOLS)
    assert DATA_OFFERINGS["wallet_pnl_deepdive"][0] == "0.25"


def _stub_defillama(monkeypatch):
    """Install a fake agents.defillama that records calls (hermetic — no
    network). acp_fulfill._dl() resolves it via `from agents import defillama`,
    which reads the `agents` package attribute, so we patch BOTH that attribute
    and sys.modules. monkeypatch restores everything after the test."""
    import agents
    fake = types.ModuleType("agents.defillama")
    calls = []

    def rec(name):
        def f(*a, **k):
            calls.append((name, a, k))
            return {"ok": name}
        return f

    for fn in ["token_intel", "token_price_chart", "protocol", "protocol_fees", "unlocks",
               "treasury", "protocols_on_chain", "chain_overview", "chain_fees", "dex_volumes",
               "yield_pools", "stablecoins", "bridges"]:
        setattr(fake, fn, rec(fn))
    monkeypatch.setitem(sys.modules, "agents.defillama", fake)
    monkeypatch.setattr(agents, "defillama", fake, raising=False)
    return calls


def test_every_dl_offering_has_a_working_handler(monkeypatch):
    _stub_defillama(monkeypatch)
    from agents import acp_fulfill as A
    monkeypatch.setattr(A, "_dl_token_logo", lambda a: None)  # no network for logo enrichment
    dl_names = [n for n in A.HANDLERS if n in DATA_TOOLS]
    assert len(dl_names) == 13
    for name in dl_names:
        # Give every handler the union of inputs it might need.
        req = {"address": "0x" + "a" * 40, "chain": "base", "slug": "aave", "span": 7}
        r = A.fulfill(name, req)
        assert r["status"] in ("ok", "error")
        assert "deliverable" in r or r["status"] == "error"


def test_token_handlers_route_chain_address_and_enrich_logo(monkeypatch):
    calls = _stub_defillama(monkeypatch)
    from agents import acp_fulfill as A
    monkeypatch.setattr(A, "_dl_token_logo", lambda a: "https://logo.test")
    out = A.fulfill("token_intel", {"address": "0xABC0000000000000000000000000000000000abc",
                                       "chain": "base", "slug": "aave"})
    assert out["deliverable"]["logo"] == "https://logo.test"
    name, args, _k = calls[-1]
    assert name == "token_intel"
    assert args[0] == "base" and args[1].endswith("abc") and args[2] == "aave"


def test_slug_handler_errors_honestly_without_slug(monkeypatch):
    _stub_defillama(monkeypatch)
    from agents import acp_fulfill as A
    out = A.fulfill("protocol", {})  # no slug provided
    assert out["deliverable"].get("error")


def _stub_codex_data(monkeypatch):
    """Same pattern as _stub_defillama above, for agents.codex_data — a fake
    module recording calls, no network."""
    import agents
    fake = types.ModuleType("agents.codex_data")
    calls = []

    def rec(name):
        def f(*a, **k):
            calls.append((name, a, k))
            return {"ok": name}
        return f

    for fn in ["wallet_balances", "wallet_pnl_stats", "wallet_pnl_chart"]:
        setattr(fake, fn, rec(fn))
    monkeypatch.setitem(sys.modules, "agents.codex_data", fake)
    monkeypatch.setattr(agents, "codex_data", fake, raising=False)
    return calls


def test_wallet_pnl_deepdive_routes_address_and_network_id(monkeypatch):
    calls = _stub_codex_data(monkeypatch)
    from agents import acp_fulfill as A
    wallet = "0x" + "b" * 40
    out = A.fulfill("wallet_pnl_deepdive", {"address": wallet, "chain": "arbitrum"})
    assert out["status"] == "ok"
    d = out["deliverable"]
    assert d["address"] == wallet
    assert d["network_id"] == 42161  # arbitrum, per _CODEX_NETWORK_IDS
    names_and_args = [(n, a) for n, a, _k in calls]
    assert names_and_args == [
        ("wallet_balances", (wallet, [42161])),
        ("wallet_pnl_stats", (wallet, 42161)),
        ("wallet_pnl_chart", (wallet, 42161)),
    ]


def test_wallet_pnl_deepdive_errors_honestly_without_address(monkeypatch):
    _stub_codex_data(monkeypatch)
    from agents import acp_fulfill as A
    out = A.fulfill("wallet_pnl_deepdive", {})
    assert out["deliverable"].get("error")
