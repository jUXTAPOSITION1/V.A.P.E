"""Tests for agents/investigate.py::_project_narrative() — the user's
explicit "Project Overview & Narrative" + "Team, Community & Social
Signals" template ask. Hermetic: skillforge.research.search/scrape and
agents.llm.ask_oci_grok_safe are all mocked, no real network/LLM call.
Real gap this closes: _expert_assessment() alone can't cover a project's
actual history/team/community (it only reasons over structured evidence +
the model's own possibly-stale training knowledge) -- this runs a REAL,
separate, targeted web search and grounds the LLM synthesis in those
results plus already-known declared data, degrading honestly to None
whenever the search/LLM path isn't available or turns up nothing relevant.
"""
from unittest import mock

from agents import investigate as inv


_SEARCH_RESULTS = {
    "raw": {"results": [
        {"title": "The Arena — SocialFi on Avalanche", "url": "https://example.com/arena",
         "content": "The Arena is a creator monetization platform, formerly Stars Arena."},
    ]},
}


def _call(llm_response=("Real grounded narrative text.", "xai_1"), search_return=_SEARCH_RESULTS,
          dex=None, cg=None):
    dex = dex if dex is not None else {"websites": [{"url": "https://arena.social"}],
                                        "socials": [{"type": "twitter", "url": "https://x.com/TheArenaApp"}]}
    with mock.patch("skillforge.research.search", return_value=search_return) as m_search, \
         mock.patch("agents.llm.ask_oci_grok_safe", return_value=llm_response) as m_llm:
        result = inv._project_narrative("ARENA", "ArenaToken", dex, cg, "0x" + "aa" * 20, "43114")
    return result, m_search, m_llm


def test_returns_grounded_narrative_with_sources():
    result, _m_search, m_llm = _call()
    assert result is not None
    assert result["text"] == "Real grounded narrative text."
    assert result["sources"] == ["https://example.com/arena"]
    _, kwargs = m_llm.call_args
    assert kwargs["tier"] == "frontier"


def test_prompt_includes_declared_socials_and_coingecko_description():
    cg = {"description": "The Arena is a SocialFi platform.", "homepage": "https://arena.social"}
    dex = {"websites": [{"url": "https://arena.social"}],
           "socials": [{"type": "twitter", "url": "https://x.com/TheArenaApp"}]}
    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "xai_1")) as m_llm:
        inv._project_narrative("ARENA", "ArenaToken", dex, cg, "0x" + "aa" * 20, "43114")
    args, _kwargs = m_llm.call_args
    system, user = args[0], args[1]
    assert "The Arena is a SocialFi platform." in user
    assert "Declared homepage: https://arena.social" in user
    assert "twitter: https://x.com/TheArenaApp" in user
    assert "untrusted external content" in system


def test_returns_none_when_no_project_name_available():
    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "xai_1")) as m_llm:
        result = inv._project_narrative("", "", {}, None, "0x" + "aa" * 20, "43114")
    assert result is None
    m_llm.assert_not_called()


def test_returns_none_when_search_unavailable():
    with mock.patch("skillforge.research.search", side_effect=RuntimeError("boom")), \
         mock.patch("agents.llm.ask_oci_grok_safe", return_value=("text", "xai_1")) as m_llm:
        result = inv._project_narrative("ARENA", "ArenaToken", {}, None, "0x" + "aa" * 20, "43114")
    assert result is None
    m_llm.assert_not_called()


def test_returns_none_when_search_yields_no_usable_results():
    result, _m_search, m_llm = _call(search_return={"raw": {"results": []}})
    assert result is None
    m_llm.assert_not_called()


def test_returns_none_when_llm_unavailable():
    result, _m_search, _m_llm = _call(llm_response=("[llm unavailable: no keys]", None))
    assert result is None


def test_returns_none_when_llm_raises():
    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.llm.ask_oci_grok_safe", side_effect=RuntimeError("boom")):
        result = inv._project_narrative(
            "ARENA", "ArenaToken",
            {"websites": [], "socials": []}, None, "0x" + "aa" * 20, "43114",
        )
    assert result is None


def test_address_identity_unverified_when_no_coingecko_contract():
    """No coingecko_contract passed in -> the address-level check never ran,
    so address_identity_verified must be False and the evidence/prompt must
    say so (CodeRabbit, PR #282: identity-binding gap)."""
    result, m_search, m_llm = _call(cg=None)
    assert result["address_identity_verified"] is False
    args, _kwargs = m_llm.call_args
    system, user = args[0], args[1]
    assert "NOT CONFIRMED" in user
    assert "address-level identity" in system.lower()


def test_address_identity_verified_when_coingecko_contract_present():
    """coingecko_contract non-empty means CoinGecko's own /contract/{address}
    lookup (called with this exact address, per _coingecko_contract_intel())
    independently confirmed the name/symbol -- address_identity_verified
    must be True and the evidence must say CONFIRMED, not NOT CONFIRMED."""
    cg = {"description": "The Arena is a SocialFi platform."}
    result, _m_search, m_llm = _call(cg=cg)
    assert result["address_identity_verified"] is True
    args, _kwargs = m_llm.call_args
    _system, user = args[0], args[1]
    assert "CONFIRMED — an independent market-data lookup verified" in user
    assert "NOT CONFIRMED" not in user


def test_write_report_renders_project_narrative_section(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "TOKEN"}
    narrative = {"text": "The Arena is a SocialFi platform with a documented turnaround history.",
                 "sources": ["https://example.com/arena"]}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
        project_narrative=narrative,
    )
    content = open(path).read()
    assert "## Project Overview & Narrative" in content
    assert "documented turnaround history" in content
    assert "Sources: https://example.com/arena" in content


def test_write_report_project_narrative_honest_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "TOKEN"}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
    )
    content = open(path).read()
    assert "## Project Overview & Narrative" in content
    assert "Not available this cycle" in content


def test_write_report_shows_unverified_identity_banner(tmp_path, monkeypatch):
    """CodeRabbit, PR #282: the reader must see the unverified-identity
    warning in the rendered report itself, not rely solely on the LLM
    having remembered to caveat its own narrative text."""
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "TOKEN"}
    narrative = {"text": "The Arena is a SocialFi platform.",
                 "sources": ["https://example.com/arena"],
                 "address_identity_verified": False}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
        project_narrative=narrative,
    )
    content = open(path).read()
    assert "Unverified identity" in content
    assert "has NOT been independently confirmed" in content


def test_write_report_omits_banner_when_identity_verified(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = {"symbol": "TOKEN"}
    narrative = {"text": "The Arena is a SocialFi platform.",
                 "sources": ["https://example.com/arena"],
                 "address_identity_verified": True}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 100, "PROCEED", [], [],
        project_narrative=narrative,
    )
    content = open(path).read()
    assert "Unverified identity" not in content
