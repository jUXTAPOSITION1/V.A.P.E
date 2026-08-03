"""Tests for agents/investigate.py::_project_narrative() — the user's
explicit "Project Overview & Narrative" + "Team, Community & Social
Signals" template ask. Hermetic: skillforge.research.search and
agents.research_engine.synthesize are all mocked, no real network/LLM call.
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


def _synth(narrative="Real grounded narrative text."):
    return {"narrative": narrative, "header": {}, "trailers": {}, "gaps": [], "verdict": None,
            "provider": "xai_1"}


def _call(narrative="Real grounded narrative text.", search_return=_SEARCH_RESULTS,
          dex=None, cg=None, scrape_excerpt=None):
    dex = dex if dex is not None else {"websites": [{"url": "https://arena.social"}],
                                        "socials": [{"type": "twitter", "url": "https://x.com/TheArenaApp"}]}
    # _scrape_excerpt mocked to None (an honest "couldn't crawl" miss) by
    # default -- it hits skillforge.research.scrape()'s real provider chain,
    # which must never fire for real in a hermetic test. Override via
    # scrape_excerpt=<callable> to exercise the real-crawl path.
    with mock.patch("skillforge.research.search", return_value=search_return) as m_search, \
         mock.patch("agents.research_engine.synthesize", return_value=_synth(narrative)) as m_llm, \
         mock.patch.object(inv, "_scrape_excerpt", side_effect=scrape_excerpt or (lambda *a, **k: None)) as m_scrape:
        result = inv._project_narrative("ARENA", "ArenaToken", dex, cg, "0x" + "aa" * 20, "43114")
    return result, m_search, m_llm, m_scrape


def test_returns_grounded_narrative_with_sources():
    result, _m_search, m_llm, _m_scrape = _call()
    assert result is not None
    assert result["text"] == "Real grounded narrative text."
    assert result["sources"] == ["https://example.com/arena"]
    _, kwargs = m_llm.call_args
    assert kwargs["max_tokens"] == 500


def test_prompt_includes_declared_socials_and_coingecko_description():
    cg = {"description": "The Arena is a SocialFi platform.", "homepage": "https://arena.social"}
    dex = {"websites": [{"url": "https://arena.social"}],
           "socials": [{"type": "twitter", "url": "https://x.com/TheArenaApp"}]}
    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.research_engine.synthesize", return_value=_synth()) as m_llm, \
         mock.patch.object(inv, "_scrape_excerpt", return_value=None):
        inv._project_narrative("ARENA", "ArenaToken", dex, cg, "0x" + "aa" * 20, "43114")
    args, kwargs = m_llm.call_args
    result_arg = args[0]
    grounding = result_arg["raw_user_block"]
    assert "The Arena is a SocialFi platform." in grounding
    assert "Declared homepage: https://arena.social" in grounding
    assert "twitter: https://x.com/TheArenaApp" in grounding
    assert "address-level identity" in kwargs["extra_instructions"].lower()


def test_crawls_declared_links_and_includes_real_excerpts():
    """Per explicit request: this function should directly crawl the
    declared website/social URLs, not just search by project name. A
    successful crawl's real excerpt must reach the LLM's own grounding
    block, capped at 3 URLs (website first, then socials in order)."""
    dex = {"websites": [{"url": "https://arena.social"}],
           "socials": [{"type": "twitter", "url": "https://x.com/TheArenaApp"}]}

    def fake_scrape(url, max_len=500):
        if url == "https://arena.social":
            return "Welcome to The Arena — creator monetization for the next generation."
        return None

    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.research_engine.synthesize", return_value=_synth()) as m_llm, \
         mock.patch.object(inv, "_scrape_excerpt", side_effect=fake_scrape):
        inv._project_narrative("ARENA", "ArenaToken", dex, None, "0x" + "aa" * 20, "43114")
    args, _kwargs = m_llm.call_args
    grounding = args[0]["raw_user_block"]
    assert "Welcome to The Arena" in grounding
    assert "Direct excerpt from declared website page" in grounding


def test_crawl_failure_is_an_honest_miss_not_a_fabrication():
    dex = {"websites": [{"url": "https://arena.social"}]}
    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.research_engine.synthesize", return_value=_synth()) as m_llm, \
         mock.patch.object(inv, "_scrape_excerpt", return_value=None):
        inv._project_narrative("ARENA", "ArenaToken", dex, None, "0x" + "aa" * 20, "43114")
    args, _kwargs = m_llm.call_args
    grounding = args[0]["raw_user_block"]
    assert "none could be crawled" in grounding
    assert "Direct excerpt" not in grounding


def test_returns_none_when_no_project_name_available():
    with mock.patch("skillforge.research.search", return_value=_SEARCH_RESULTS), \
         mock.patch("agents.research_engine.synthesize", return_value=_synth()) as m_llm:
        result = inv._project_narrative("", "", {}, None, "0x" + "aa" * 20, "43114")
    assert result is None
    m_llm.assert_not_called()


def test_returns_none_when_search_unavailable():
    with mock.patch("skillforge.research.search", side_effect=RuntimeError("boom")), \
         mock.patch("agents.research_engine.synthesize", return_value=_synth()) as m_llm:
        result = inv._project_narrative("ARENA", "ArenaToken", {}, None, "0x" + "aa" * 20, "43114")
    assert result is None
    m_llm.assert_not_called()


def test_falls_back_to_declared_data_when_search_yields_no_usable_results():
    """Real gap this pins (investigation-20260802-203111-0xd7A73942.md): the
    function used to hard-bail to None the moment search came back empty,
    even when the token had a real declared website/Twitter/Telegram sitting
    right there in already-fetched dex data -- a thinner but real narrative
    was always possible from that alone. Only bail when there's truly
    nothing to synthesize from: no search hits AND no declared presence."""
    result, _m_search, m_llm, _m_scrape = _call(search_return={"raw": {"results": []}})
    assert result is not None
    assert result["text"] == "Real grounded narrative text."
    m_llm.assert_called_once()


def test_returns_none_when_search_empty_and_no_declared_data_either():
    result, _m_search, m_llm, _m_scrape = _call(search_return={"raw": {"results": []}}, dex={})
    assert result is None
    m_llm.assert_not_called()


def test_returns_none_when_llm_unavailable():
    result, _m_search, _m_llm, _m_scrape = _call(narrative="_Synthesis unavailable this cycle (no LLM provider reachable)._")
    assert result is None


def test_address_identity_unverified_when_no_coingecko_contract():
    """No coingecko_contract passed in -> the address-level check never ran,
    so address_identity_verified must be False and the evidence/prompt must
    say so (CodeRabbit, PR #282: identity-binding gap)."""
    result, m_search, m_llm, _m_scrape = _call(cg=None)
    assert result["address_identity_verified"] is False
    args, kwargs = m_llm.call_args
    grounding = args[0]["raw_user_block"]
    assert "NOT CONFIRMED" in grounding
    assert "address-level identity" in kwargs["extra_instructions"].lower()


def test_address_identity_verified_when_coingecko_contract_present():
    """coingecko_contract non-empty means CoinGecko's own /contract/{address}
    lookup (called with this exact address, per _coingecko_contract_intel())
    independently confirmed the name/symbol -- address_identity_verified
    must be True and the evidence must say CONFIRMED, not NOT CONFIRMED."""
    cg = {"description": "The Arena is a SocialFi platform."}
    result, _m_search, m_llm, _m_scrape = _call(cg=cg)
    assert result["address_identity_verified"] is True
    args, _kwargs = m_llm.call_args
    grounding = args[0]["raw_user_block"]
    assert "CONFIRMED — an independent market-data lookup verified" in grounding
    assert "NOT CONFIRMED" not in grounding


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
