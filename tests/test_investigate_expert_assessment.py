"""Tests for agents/investigate.py's expert assessment — the real synthesis
layer added on top of score()'s deterministic verdict. Hermetic:
agents.llm.ask_oci_grok_safe is mocked, no real network/LLM call.
"""
from unittest import mock

from agents import investigate as inv
from agents.llm import FRONTIER_ORDER


def _call(response_text):
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=(response_text, "xai_1")) as m:
        result = inv._expert_assessment(
            "0x" + "aa" * 20, "TOKEN", "8453", "REJECT", 10, ["HONEYPOT"], [],
            {"is_honeypot": "1"}, {"symbol": "TOKEN"}, {"is_contract": True}, {},
            [], None, [], None, None,
        )
    return result, m


def test_agree_response_is_parsed_correctly():
    result, m = _call("AGREE: this is clearly a honeypot, the verdict is correct.")
    assert result["disagrees"] is False
    assert result["text"].startswith("AGREE:")
    _, kwargs = m.call_args
    assert kwargs["tier"] == "frontier"
    assert kwargs["provider_order"] == FRONTIER_ORDER


def test_disagree_response_is_parsed_correctly():
    result, _m = _call("DISAGREE: the liquidity depth argues against this being a scam.")
    assert result["disagrees"] is True
    assert result["text"].startswith("DISAGREE:")


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
    assessment = {"text": "AGREE: real analysis here.", "disagrees": False}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
        expert_assessment=assessment,
    )
    content = open(path).read()
    assert "## Expert Assessment" in content
    assert "(Grok)" not in content
    assert "AGREE: real analysis here." in content
    assert "Agrees with the verdict above" in content


def test_write_report_renders_disagreement_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = {}, {"symbol": "TOKEN"}, {"is_contract": True}, {}
    assessment = {"text": "DISAGREE: real counter-analysis.", "disagrees": True}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
        expert_assessment=assessment,
    )
    content = open(path).read()
    assert "DISAGREES with the verdict above" in content


def test_write_report_handles_missing_assessment(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, dex, onchain, verif = {}, {"symbol": "TOKEN"}, {"is_contract": True}, {}
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 10, "REJECT", ["HONEYPOT"], [],
    )
    content = open(path).read()
    assert "Expert assessment not available this cycle." in content
