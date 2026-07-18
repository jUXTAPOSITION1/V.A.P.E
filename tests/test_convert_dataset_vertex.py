"""Tests for scripts/convert_dataset_vertex.py — the OpenAI-messages ->
Vertex AI tuning-schema reshape. Must be lossless (every row survives,
nothing fabricated) and must fail loudly on a shape it doesn't recognize
rather than silently emitting a bad row Vertex would train on."""
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "convert_dataset_vertex", os.path.join(ROOT, "scripts", "convert_dataset_vertex.py"))
cv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cv)


def test_convert_row_maps_system_user_assistant():
    row = {"messages": [
        {"role": "system", "content": "You are VAPE."},
        {"role": "user", "content": "Target: 0xabc"},
        {"role": "assistant", "content": "Verdict: CAUTION"},
    ]}
    out = cv.convert_row(row)
    assert out["systemInstruction"] == {"role": "system", "parts": [{"text": "You are VAPE."}]}
    assert out["contents"] == [
        {"role": "user", "parts": [{"text": "Target: 0xabc"}]},
        {"role": "model", "parts": [{"text": "Verdict: CAUTION"}]},
    ]


def test_convert_row_without_system_message_omits_system_instruction():
    row = {"messages": [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]}
    out = cv.convert_row(row)
    assert "systemInstruction" not in out
    assert out["contents"][0]["role"] == "user"
    assert out["contents"][1]["role"] == "model"


def test_assistant_role_becomes_model_not_assistant():
    row = {"messages": [
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a"},
    ]}
    out = cv.convert_row(row)
    assert out["contents"][1]["role"] == "model"
    assert "assistant" not in json.dumps(out)


def test_missing_messages_key_raises():
    with pytest.raises(ValueError):
        cv.convert_row({"not_messages": []})


def test_unrecognized_role_raises():
    row = {"messages": [
        {"role": "user", "content": "u"},
        {"role": "narrator", "content": "???"},
    ]}
    with pytest.raises(ValueError):
        cv.convert_row(row)


def test_two_system_messages_raises():
    row = {"messages": [
        {"role": "system", "content": "s1"},
        {"role": "system", "content": "s2"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a"},
    ]}
    with pytest.raises(ValueError):
        cv.convert_row(row)


def test_wrong_turn_count_raises():
    row = {"messages": [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a"},
    ]}
    with pytest.raises(ValueError):
        cv.convert_row(row)


def test_convert_file_is_lossless(tmp_path):
    src = tmp_path / "in.jsonl"
    rows = [
        {"messages": [{"role": "system", "content": "s"},
                      {"role": "user", "content": f"u{i}"},
                      {"role": "assistant", "content": f"a{i}"}]}
        for i in range(5)
    ]
    src.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    dst = tmp_path / "out" / "converted.jsonl"

    n_in, n_out = cv.convert_file(str(src), str(dst))

    assert n_in == 5 and n_out == 5
    out_lines = dst.read_text().strip().splitlines()
    assert len(out_lines) == 5
    for i, line in enumerate(out_lines):
        parsed = json.loads(line)
        assert parsed["contents"][0]["parts"][0]["text"] == f"u{i}"
        assert parsed["contents"][1]["parts"][0]["text"] == f"a{i}"


def test_convert_file_skips_blank_lines(tmp_path):
    src = tmp_path / "in.jsonl"
    row = {"messages": [{"role": "user", "content": "u"}, {"role": "assistant", "content": "a"}]}
    src.write_text(json.dumps(row) + "\n\n" + json.dumps(row) + "\n")
    dst = tmp_path / "out.jsonl"

    n_in, n_out = cv.convert_file(str(src), str(dst))
    assert n_in == 2 and n_out == 2
