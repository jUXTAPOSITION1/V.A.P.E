"""Tests for agents/investigate.py's expert assessment — the real synthesis
layer added on top of score()'s deterministic verdict, routed through
agents/research_engine.py::synthesize() (see PR #373's evidence_lines/
verdict_options additions). Hermetic: agents.llm.ask_oci_grok_safe is
mocked (synthesize() imports it fresh per call, so patching the module
attribute still intercepts it) — no real network/LLM call.
"""
from unittest import mock

from agents import investigate as inv
from agents.llm import FRONTIER_ORDER


def _call(response_text, dex=None, project_narrative=None):
    dex = dex if dex is not None else {"symbol": "TOKEN"}
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(response_text, "xai_1")) as m:
        result = inv._expert_assessment(
            "0x" + "aa" * 20, "TOKEN", "8453", "REJECT", 10, ["HONEYPOT"], [],
            {"is_honeypot": "1"}, dex, {"is_contract": True}, {},
            [], None, [], None, None, project_narrative=project_narrative,
        )
    return result, m


def test_declared_website_and_socials_reach_the_llm_as_evidence():
    """Real bug this pins (confirmed against a live report,
    investigation-20260803-181357-0xfD181Ca5.md): the evidence this
    function built never included dex's own declared website/social
    links, so the model had zero signal they existed and confidently wrote
    "no social proof available" while the SAME report's Project Links
    section showed them. The declared links must reach the model's own
    prompt (the `user` block passed to ask_oci_grok_safe), not just get
    silently dropped."""
    dex = {"symbol": "TOKEN", "websites": [{"url": "https://dogpunk.app"}],
           "socials": [{"type": "twitter", "url": "https://x.com/dogpunkV4"}]}
    _result, m = _call("Some analysis.\n\nVERDICT ALIGNMENT: AGREE", dex=dex)
    args, _kwargs = m.call_args
    user_block = args[1]
    assert "https://dogpunk.app" in user_block
    assert "https://x.com/dogpunkV4" in user_block


def test_no_declared_web_presence_is_stated_as_a_real_absence():
    dex = {"symbol": "TOKEN"}
    _result, m = _call("Some analysis.\n\nVERDICT ALIGNMENT: AGREE", dex=dex)
    args, _kwargs = m.call_args
    user_block = args[1]
    assert "none found" in user_block.lower()


def test_project_narrative_research_reaches_the_llm_as_evidence():
    """The dedicated real web-search synthesis (_project_narrative(), which
    now runs BEFORE this function per investigate()'s own call-order fix)
    must be visible to this function too, not just the raw declared
    links -- otherwise this function still can't say anything about
    whether that research actually found a coherent project story."""
    narrative = {"text": "DogPunk presents as a meme-coin community project with an active Twitter presence.",
                 "address_identity_verified": False}
    _result, m = _call("Some analysis.\n\nVERDICT ALIGNMENT: AGREE", project_narrative=narrative)
    args, _kwargs = m.call_args
    user_block = args[1]
    assert "DogPunk presents as a meme-coin community project" in user_block
    assert "NOT independently confirmed" in user_block


def test_agree_response_is_parsed_correctly():
    result, m = _call(
        "This is clearly a honeypot given the flagged mint function and zero holders.\n\n"
        "VERDICT ALIGNMENT: AGREE"
    )
    assert result["disagrees"] is False
    assert "honeypot" in result["text"]
    assert "VERDICT ALIGNMENT" not in result["text"]  # marker line stripped from rendered text
    _, kwargs = m.call_args
    assert kwargs["tier"] == "frontier"
    assert kwargs["provider_order"] == FRONTIER_ORDER
    assert kwargs.get("search") is not True  # must not bypass OCI Grok/Vertex


def test_disagree_response_is_parsed_correctly():
    result, _m = _call(
        "The liquidity depth and holder distribution argue against this being a scam.\n\n"
        "VERDICT ALIGNMENT: DISAGREE"
    )
    assert result["disagrees"] is True
    assert "liquidity depth" in result["text"]
    assert "VERDICT ALIGNMENT" not in result["text"]


def test_malformed_response_without_marker_defaults_to_agree():
    """A response missing the required trailing marker is a formatting
    miss, not evidence of disagreement — same 'never claim disagreement
    without a real, parseable signal' principle as everywhere else in this
    pipeline that degrades honestly rather than guessing."""
    result, _m = _call("Some real analysis text with no marker line at all.")
    assert result["disagrees"] is False
    assert result["text"].startswith("Some real analysis text with no marker line at all.")
    assert "## Gaps & Confidence" in result["text"]  # always appended, even when the model flagged none


def test_early_marker_occurrence_does_not_hijack_final_verdict():
    """Real bug this pins (CodeRabbit, PR #277): the old re.search() matched
    the FIRST 'VERDICT ALIGNMENT: ...' occurrence anywhere in the text — an
    earlier mention (e.g. the model quoting/restating the instruction, or
    injected content) with the opposite verdict from the model's real final
    line would silently flip `disagrees`. Only the last non-empty line is a
    valid marker."""
    result, _m = _call(
        "VERDICT ALIGNMENT: AGREE\n\n"
        "Some analysis discusses the above, then reconsiders.\n\n"
        "VERDICT ALIGNMENT: DISAGREE"
    )
    assert result["disagrees"] is True
    assert "VERDICT ALIGNMENT: AGREE" in result["text"]  # not the final line, so left in the rendered analysis
    assert "VERDICT ALIGNMENT: DISAGREE" not in result["text"]  # the final marker line is stripped


def test_marker_not_on_its_own_final_line_is_not_matched():
    """A marker embedded mid-sentence on the final line (not a standalone
    'VERDICT ALIGNMENT: X') must not match — re.fullmatch() on the trimmed
    final line requires the whole line to be exactly the marker."""
    result, _m = _call(
        "Some analysis.\n\n"
        "In summary the VERDICT ALIGNMENT: DISAGREE with the stated risk."
    )
    assert result["disagrees"] is False


def test_llm_unavailable_returns_none():
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("[llm unavailable: no keys]", None)):
        result = inv._expert_assessment(
            "0x" + "aa" * 20, "TOKEN", "8453", "REJECT", 10, [], [],
            {}, {}, {}, {}, [], None, [], None, None,
        )
    assert result is None


def test_exception_is_swallowed():
    with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=RuntimeError("boom")):
        result = inv._expert_assessment(
            "0x" + "aa" * 20, "TOKEN", "8453", "REJECT", 10, [], [],
            {}, {}, {}, {}, [], None, [], None, None,
        )
    assert result is None


def test_log_expert_disagreement_calls_append_to_memory(monkeypatch):
    calls = []
    monkeypatch.setattr(inv, "append_to_memory", lambda **kw: calls.append(kw))
    inv._log_expert_disagreement("0x" + "aa" * 20, "8453", "TOKEN", "REJECT", 10, "DISAGREE: because X")
    assert len(calls) == 1
    assert calls[0]["category"] == "lesson"
    assert "TOKEN" in calls[0]["title"]
    assert calls[0]["metadata"]["verdict"] == "REJECT"


def test_log_expert_disagreement_noop_without_memory(monkeypatch):
    monkeypatch.setattr(inv, "append_to_memory", None)
    inv._log_expert_disagreement("0x" + "aa" * 20, "8453", "TOKEN", "REJECT", 10, "text")  # must not raise


def test_write_report_renders_assessment_section(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = {}, {"symbol": "TOKEN"}, {"is_contract": True}, {}
    assessment = {"text": "Real analysis here.", "disagrees": False}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
        expert_assessment=assessment,
    )
    content = open(path).read()
    assert "## Expert Assessment" in content
    assert "(Grok)" not in content
    assert "Real analysis here." in content


def test_write_report_never_renders_agree_disagree_framing(tmp_path, monkeypatch):
    """The internal disagrees flag is real (see _log_expert_disagreement()
    and the module's own docstring) but must never surface as a published
    "Agrees/Disagrees with the verdict above" tag — the Expert Assessment is
    the primary synthesis now, not a second opinion on the score."""
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = {}, {"symbol": "TOKEN"}, {"is_contract": True}, {}
    assessment = {"text": "Real counter-analysis.", "disagrees": True}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
        expert_assessment=assessment,
    )
    content = open(path).read()
    assert "Real counter-analysis." in content
    assert "DISAGREES with the verdict above" not in content
    assert "Agrees with the verdict above" not in content


def test_expert_assessment_is_the_first_section_after_the_header(tmp_path, monkeypatch):
    """Real gap this closes: the Expert Assessment used to sit halfway down
    the report, after the Executive Summary/Project Narrative/Verdict
    Rationale sections — reading as a second opinion checking someone
    else's work rather than the detective's own lead conclusion. It's the
    first substantive section now, right after the header/verdict line."""
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = {}, {"symbol": "TOKEN"}, {"is_contract": True}, {}
    assessment = {"text": "Real analysis here.", "disagrees": False}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
        expert_assessment=assessment,
    )
    content = open(path).read()
    assert content.index("## Expert Assessment") < content.index("## Scoring Dashboard")
    assert content.index("## Expert Assessment") < content.index("## Verdict Rationale")


def test_write_report_handles_missing_assessment(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = {}, {"symbol": "TOKEN"}, {"is_contract": True}, {}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
    )
    content = open(path).read()
    assert "Expert assessment not available this cycle." in content
