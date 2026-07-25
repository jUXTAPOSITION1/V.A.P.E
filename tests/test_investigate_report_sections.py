"""Tests for the report-quality additions to agents/investigate.py::write_report():
Project Links, Tokenomics, and Sources & Verification Links. Real gaps these
close (flagged directly against a live report, investigation-20260725-155143-
0xB8d7710f.md, an ARENA/Avalanche investigation): dexscreener()'s own
websites/socials were already fetched but never rendered; CoinGecko's
contract-address response already carried supply/FDV/description data that
was discarded down to 4 fields; and no report ever linked back to a real
source for independent re-verification. All three sections must degrade
honestly (an explicit "not available" line) when the underlying data is
absent, never fabricate a placeholder.
"""
from agents import investigate as inv


def _base_args():
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "ARENA", "name": "ArenaToken", "price_usd": "0.0013",
           "liquidity_usd": 239369, "vol_24h_usd": 313697, "change_24h_pct": 15.8,
           "dex": "traderjoe", "pair_url": "https://dexscreener.com/avalanche/0xpair",
           "websites": [{"url": "https://arena.social"}],
           "socials": [{"type": "twitter", "url": "https://x.com/TheArenaApp"}]}
    return gp, dex, onchain, verif


def test_project_links_rendered_from_dexscreener_data(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = _base_args()
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "43114", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "## Project Links (as declared on DexScreener)" in content
    assert "- Website: https://arena.social" in content
    assert "- twitter: https://x.com/TheArenaApp" in content


def test_project_links_honest_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "TOKEN"}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "No official website/social links declared" in content


def test_tokenomics_rendered_from_coingecko_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = _base_args()
    cg = {"name": "Arena", "symbol": "arena", "coingecko_id": "arena-2",
          "price_usd": 0.0013, "market_cap_usd": 5_500_000, "fdv_usd": 11_700_000,
          "total_supply": 10_000_000_000, "circulating_supply": 4_700_000_000,
          "max_supply": 10_000_000_000, "homepage": "https://arena.social",
          "twitter": "TheArenaApp", "description": "The Arena is a SocialFi platform."}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "43114", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
        coingecko_contract=cg,
    )
    content = open(path).read()
    assert "## Tokenomics (CoinGecko, address-verified)" in content
    assert "Circulating supply: 4,700,000,000 ARENA" in content
    assert "Fully diluted valuation: $11,700,000" in content
    assert "FDV/Market-cap ratio: 2.13x" in content
    assert "still non-circulating (dilution risk)" in content
    assert "The Arena is a SocialFi platform." in content


def test_tokenomics_honest_when_coingecko_untracked(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = _base_args()
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "43114", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
        coingecko_contract=None,
    )
    content = open(path).read()
    assert "## Tokenomics (CoinGecko, address-verified)" in content
    assert "Not available this cycle" in content
    assert "absence noted, not penalized" in content


def test_sources_section_links_explorer_dexscreener_and_coingecko(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = _base_args()
    cg = {"coingecko_id": "arena-2", "market_cap_usd": 5_500_000}
    target = "0x" + "aa" * 20
    path, _sym, _emoji = inv.write_report(
        target, "43114", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
        coingecko_contract=cg,
    )
    content = open(path).read()
    assert "## Sources & Verification Links" in content
    assert f"- Block explorer: https://snowtrace.io/address/{target}" in content
    assert "- DexScreener pair: https://dexscreener.com/avalanche/0xpair" in content
    assert "- CoinGecko: https://www.coingecko.com/en/coins/arena-2" in content


def test_sources_section_omits_missing_links_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "TOKEN"}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "## Sources & Verification Links" in content
    assert "DexScreener pair:" not in content
    assert "CoinGecko:" not in content
