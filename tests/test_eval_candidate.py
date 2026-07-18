"""Tests for training/eval_candidate.py's hermetic (non-network) helpers —
the verdict-token matching logic that grades a fine-tuned candidate against
VAPE's real held-out data. The actual HTTP call to a served model and the
deepteam safety campaign both need a live GPU box, so those are exercised for
real on the training runner, not here."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "eval_candidate", os.path.join(ROOT, "training", "eval_candidate.py"))
ec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ec)


def test_first_line_skips_leading_blank_lines():
    assert ec._first_line("\n\n  Verdict: CAUTION\nmore text") == "Verdict: CAUTION"


def test_first_line_empty_for_blank_text():
    assert ec._first_line("") == ""
    assert ec._first_line("   \n  \n") == ""


def test_verdict_tokens_matches_investigation_style():
    assert ec._verdict_tokens("Verdict: CAUTION") == {"CAUTION"}


def test_verdict_tokens_matches_security_sweep_style():
    assert ec._verdict_tokens("THREAT LEVEL: \U0001F534 HIGH") == {"HIGH"}


def test_verdict_tokens_matches_macro_sweep_style():
    assert ec._verdict_tokens("MACRO TREND: ⚠️ RISK-OFF") == {"RISK-OFF"}


def test_verdict_tokens_case_insensitive():
    assert ec._verdict_tokens("verdict: proceed") == {"PROCEED"}


def test_verdict_tokens_empty_when_no_known_category():
    assert ec._verdict_tokens("PROTOCOL HEALTH: 6.0/10") == set()


def test_run_verdict_match_scores_exact_and_wrong_predictions(monkeypatch):
    val_rows = [
        {"messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "Verdict: CAUTION\n\nRationale..."},
        ]},
        {"messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u2"},
            {"role": "assistant", "content": "Verdict: REJECT\n\nRationale..."},
        ]},
    ]
    responses = iter(["Verdict: CAUTION", "Verdict: PROCEED"])  # 1 right, 1 wrong
    monkeypatch.setattr(ec, "candidate_generate", lambda system, user, **kw: next(responses))

    result = ec.run_verdict_match(val_rows)
    assert result["n"] == 2
    assert result["matches"] == 1
    assert result["rate"] == 0.5


def test_run_verdict_match_handles_empty_val_set():
    result = ec.run_verdict_match([])
    assert result == {"n": 0, "matches": 0, "rate": None, "examples": []}
