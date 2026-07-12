"""DefiLlama tools as ACP/x402 offerings — cross-surface parity + dispatch.

The 14 DefiLlama micro-services must stay identical across the four places
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


# The 14 market-data tools, by name (no prefix). This literal set is the
# contract every surface must match — if a tool is added/renamed, this and all
# four surfaces move together or the test fails.
DATA_TOOLS = {
    "token_intel", "token_chart", "protocol", "protocol_fees", "unlocks", "treasury",
    "chain_protocols", "chain_overview", "chain_fees", "dex_volumes", "derivatives",
    "yields", "stablecoins", "bridges",
}


def test_data_offering_names_identical_across_all_surfaces():
    from agents.publish_reputation import DL_NAMES
    from agents.x402_directory_register import DATA_OFFERINGS
    from agents.acp_fulfill import HANDLERS
    # worker/src/dataHandlers.ts declares the data tools as `name: "..."` (the
    # only place in that file that does), so this captures exactly the tier.
    worker = set(re.findall(r'name:\s*"([a-z_]+)"', (ROOT / "worker/src/dataHandlers.ts").read_text()))
    assert DL_NAMES == DATA_TOOLS                 # published catalog
    assert set(DATA_OFFERINGS) == DATA_TOOLS      # x402 directory
    assert worker == DATA_TOOLS                   # paid worker routes
    assert DATA_TOOLS <= set(HANDLERS)            # every data tool is ACP-fulfillable


def test_data_offerings_all_priced_one_cent():
    from agents.publish_reputation import DL_OFFERINGS
    from agents.x402_directory_register import DATA_OFFERINGS
    assert len(DL_OFFERINGS) == 14
    assert all(price == 0.01 for _n, price, _s in DL_OFFERINGS)
    assert all(meta[0] == "0.01" for meta in DATA_OFFERINGS.values())


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
               "derivatives_volumes", "yield_pools", "stablecoins", "bridges"]:
        setattr(fake, fn, rec(fn))
    monkeypatch.setitem(sys.modules, "agents.defillama", fake)
    monkeypatch.setattr(agents, "defillama", fake, raising=False)
    return calls


def test_every_dl_offering_has_a_working_handler(monkeypatch):
    _stub_defillama(monkeypatch)
    from agents import acp_fulfill as A
    monkeypatch.setattr(A, "_dl_token_logo", lambda a: None)  # no network for logo enrichment
    dl_names = [n for n in A.HANDLERS if n in DATA_TOOLS]
    assert len(dl_names) == 14
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
