"""Tests for agents/investigate.py::_categorize_report_reasons() and its
wiring into write_report()'s new "Risk Breakdown by Category" section --
pure presentation over score()'s already-computed reasons/positive_signals
(no new data, no scoring change), directly answering the user's ask for a
multi-dimensional "how does this rank across categories" view rather than
a single flat score.
"""
from agents import investigate as inv
from tests.conftest import clean_gp, clean_dex


def test_categorize_buckets_security_reasons():
    result = inv._categorize_report_reasons(["[-60] GoPlus: HONEYPOT detected"], [])
    names = [name for name, _ in result]
    assert "Security & Contract Risk" in names


def test_categorize_buckets_distribution_reasons():
    result = inv._categorize_report_reasons(
        ["[-20] Very few holders (10) — thin, easily manipulated distribution"], [])
    names = [name for name, _ in result]
    assert "Holder Distribution & Liquidity" in names


def test_categorize_buckets_tokenomics_reasons():
    result = inv._categorize_report_reasons(
        ["[-40] Token name/symbol claims a major stablecoin brand but trades far from the real $1 peg"], [])
    names = [name for name, _ in result]
    assert "Tokenomics & Track Record" in names


def test_categorize_buckets_transparency_reasons():
    result = inv._categorize_report_reasons(
        ["[-15] Contract source UNVERIFIED"], [])
    names = [name for name, _ in result]
    assert "Transparency & Provenance" in names


def test_categorize_unmatched_reason_falls_back_to_other():
    result = inv._categorize_report_reasons(["[-5] Some brand-new future reason nobody wrote a keyword for"], [])
    names = [name for name, _ in result]
    assert "Other" in names


def test_categorize_drops_empty_categories():
    result = inv._categorize_report_reasons(["[-60] GoPlus: HONEYPOT detected"], [])
    assert len(result) == 1
    assert result[0][0] == "Security & Contract Risk"


def test_categorize_empty_input_returns_empty_list():
    assert inv._categorize_report_reasons([], []) == []


def test_categorize_positive_signals_also_bucketed():
    result = inv._categorize_report_reasons([], ["500 holders — reasonably distributed"])
    names = [name for name, _ in result]
    assert "Holder Distribution & Liquidity" in names
    bucket = dict(result)["Holder Distribution & Liquidity"]
    assert bucket["signals"] == ["500 holders — reasonably distributed"]
    assert bucket["flags"] == []


def test_write_report_renders_risk_breakdown_section(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = clean_dex(symbol="TOKEN")
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT",
        ["[-60] GoPlus: HONEYPOT detected"], [],
    )
    content = open(path).read()
    assert "## Risk Breakdown by Category" in content
    assert "**Security & Contract Risk** — 1 flag(s), 0 positive signal(s)" in content
    assert "GoPlus: HONEYPOT detected" in content


def test_write_report_risk_breakdown_honest_when_nothing_to_show(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = clean_dex(symbol="TOKEN")
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "## Risk Breakdown by Category" in content
    assert "Nothing to categorize this cycle." in content
