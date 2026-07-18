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


class TestVertexBackend:
    """VAPE_EVAL_BACKEND=vertex lets this same eval harness grade the
    Vertex-tuned candidate (agents/llm.py::ask_vertex_candidate()) instead of
    the self-hosted-GPU one, without duplicating the verdict-match/safety-
    campaign logic above."""

    def test_default_backend_is_vllm(self):
        assert ec.EVAL_BACKEND == "vllm"

    def test_label_reflects_vllm_backend_by_default(self):
        assert ec._candidate_label() == f"{ec.CANDIDATE_MODEL} at {ec.CANDIDATE_URL}"

    def test_label_reflects_vertex_backend(self, monkeypatch):
        monkeypatch.setattr(ec, "EVAL_BACKEND", "vertex")
        label = ec._candidate_label()
        assert "vertex-tuned-gemini" in label
        assert "87858016172" in label

    def test_vertex_generate_returns_text_when_reached(self, monkeypatch):
        from agents import llm as agents_llm
        monkeypatch.setattr(agents_llm, "ask_vertex_candidate",
                             lambda system, user, **kw: ("real reply", "vertex_tuned"))
        assert ec._candidate_generate_vertex("sys", "usr", 400, 0.2) == "real reply"

    def test_vertex_generate_raises_when_fallen_through(self, monkeypatch):
        """A reply that actually came from the free chain (provider !=
        vertex_tuned) must never be silently graded as the candidate's own
        output — that would corrupt the comparison this whole script exists
        to make."""
        from agents import llm as agents_llm
        monkeypatch.setattr(agents_llm, "ask_vertex_candidate",
                             lambda system, user, **kw: ("fallback reply", "groq"))
        try:
            ec._candidate_generate_vertex("sys", "usr", 400, 0.2)
            assert False, "expected RuntimeError"
        except RuntimeError as e:
            assert "groq" in str(e)

    def test_candidate_generate_dispatches_to_vertex_when_selected(self, monkeypatch):
        from agents import llm as agents_llm
        monkeypatch.setattr(ec, "EVAL_BACKEND", "vertex")
        monkeypatch.setattr(agents_llm, "ask_vertex_candidate",
                             lambda system, user, **kw: ("via vertex", "vertex_tuned"))
        assert ec.candidate_generate("sys", "usr") == "via vertex"

    def test_run_verdict_match_treats_vertex_fallthrough_as_a_graded_miss(self, monkeypatch):
        """The RuntimeError from a vertex fallthrough must be caught by
        run_verdict_match's per-example error handling, not propagate and
        crash the whole eval run."""
        val_rows = [{"messages": [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "Verdict: CAUTION\n\nRationale..."},
        ]}]

        def _raise(system, user, **kw):
            raise RuntimeError("did not reach the Vertex candidate — fell through to 'groq'")

        monkeypatch.setattr(ec, "candidate_generate", _raise)
        result = ec.run_verdict_match(val_rows)
        assert result["n"] == 1
        assert result["matches"] == 0
        assert "[error:" in result["examples"][0]["actual"]
