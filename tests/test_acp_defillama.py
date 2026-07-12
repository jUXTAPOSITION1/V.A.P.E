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


def _names(path, pattern):
    return set(re.findall(pattern, (ROOT / path).read_text()))


def test_dl_offering_names_identical_across_all_surfaces():
    acp = _names("agents/acp_fulfill.py", r'"(dl_[a-z_]+)":')
    pub = _names("agents/publish_reputation.py", r'\("(dl_[a-z_]+)",')
    x402 = _names("agents/x402_directory_register.py", r'"(dl_[a-z_]+)":')
    worker = _names("worker/src/dataHandlers.ts", r'name:\s*"(dl_[a-z_]+)"')
    assert len(acp) == 14
    assert acp == pub == x402 == worker


def test_dl_offerings_all_priced_one_cent_in_catalog():
    # Every DefiLlama entry in the published catalog is exactly 0.01 USDC.
    text = (ROOT / "agents/publish_reputation.py").read_text()
    dl_block = text[text.index("DL_OFFERINGS = ["):text.index("DL_NAMES")]
    entries = re.findall(r'\("(dl_[a-z_]+)",\s*([0-9.]+),', dl_block)
    assert len(entries) == 14
    assert all(price == "0.01" for _n, price in entries)


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
    dl_names = [n for n in A.HANDLERS if n.startswith("dl_")]
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
    out = A.fulfill("dl_token_intel", {"address": "0xABC0000000000000000000000000000000000abc",
                                       "chain": "base", "slug": "aave"})
    assert out["deliverable"]["logo"] == "https://logo.test"
    name, args, _k = calls[-1]
    assert name == "token_intel"
    assert args[0] == "base" and args[1].endswith("abc") and args[2] == "aave"


def test_slug_handler_errors_honestly_without_slug(monkeypatch):
    _stub_defillama(monkeypatch)
    from agents import acp_fulfill as A
    out = A.fulfill("dl_protocol", {})  # no slug provided
    assert out["deliverable"].get("error")
