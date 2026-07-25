"""Tests for agents/investigate.py::_category_subscores() and the new
"Executive Summary" report section — the user's explicit template ask:
"Executive Summary + Overall Ranking Score (composite with category
breakdown, e.g., Security 95/100, Fundamentals 70/100, Tokenomics 60/100 ->
overall rank)". Derived entirely from score()'s own reasons (no new data,
no scoring change) and explicitly labeled as a presentation aid, not a
second scoring engine — the real score/verdict stays authoritative.
"""
from agents import investigate as inv
from tests.conftest import clean_gp, clean_dex


def test_category_subscores_starts_all_categories_at_100_with_no_reasons():
    subs = inv._category_subscores([])
    assert set(subs) == {name for name, _ in inv._RISK_CATEGORIES}
    assert all(v == 100 for v in subs.values())


def test_category_subscores_nets_penalty_against_its_own_category():
    subs = inv._category_subscores(["[-60] GoPlus: HONEYPOT detected"])
    assert subs["Security & Contract Risk"] == 40
    # Unrelated categories are untouched by a Security-bucketed penalty.
    assert subs["Holder Distribution & Liquidity"] == 100


def test_category_subscores_clamped_at_zero_not_negative():
    subs = inv._category_subscores(["[-60] GoPlus: HONEYPOT detected", "[-60] Something else honeypot-y"])
    assert subs["Security & Contract Risk"] == 0


def test_category_subscores_ignores_the_global_cap_line():
    """A "[capped at N] ..." line is a whole-score adjustment, not
    attributable to any single category — must not be parsed as a weight."""
    subs = inv._category_subscores(["[capped at 55] Only 0 positive legitimacy signal(s) found"])
    assert all(v == 100 for v in subs.values())


def test_category_subscores_refund_nets_positive_but_stays_clamped_at_100():
    text = "[+25] Verified major stablecoin (CoinGecko: Tether, ...) — mint/owner-controlled-freeze refunded"
    subs = inv._category_subscores([text])
    bucketed = inv._bucket_for_report_reason(text)
    assert subs[bucketed] == 100  # 100 + 25, clamped back down to the 100 ceiling


def test_write_report_renders_executive_summary_with_category_table(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = clean_dex(symbol="TOKEN")
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 40, "REJECT",
        ["[-60] GoPlus: HONEYPOT detected"], [],
    )
    content = open(path).read()
    assert "## Executive Summary" in content
    assert "**Overall: REJECT (40/100)**" in content
    assert "| Security & Contract Risk | 40/100 |" in content
    assert "| Holder Distribution & Liquidity | 100/100 |" in content
    assert "authoritative verdict" in content
