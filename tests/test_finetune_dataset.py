"""Tests for scripts/build_finetune_dataset.py's investigation parser. The
corpus is only trustworthy if every training pair traces to a real verdict, so
these pin: both report-format generations parse, the label is never fabricated
when the fields are missing, and the split is deterministic."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "build_finetune_dataset", os.path.join(ROOT, "scripts", "build_finetune_dataset.py"))
bf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bf)

OLD_FORMAT = """# 🕵️ VAPE Investigation — OpenAI

- **Target:** `0xcC67e54FC715246E5B27a97E69747Ecd4c6375B6`
- **Chain:** 8453 (Base)
- **Verdict:** 🟡 **CAUTION**
- **Safety Score:** 68/100

## Verdict Rationale
- [-10] Low liquidity $26,641

## Market & Liquidity (DexScreener)
- Symbol/Name: OpenAI / OpenAI
- Liquidity: $26640.62
"""

NEW_FORMAT = """# Investigation — ASOS

- **Target:** `0xB8Cb9F0630fc8C956B6461A8425097230B1E0aCa`
- **Chain:** 8453 (Base)
- **Verdict:** CAUTION (68/100)

## Verdict Rationale (risk factors)
- [-12] Mintable supply (dilution risk)

## Positive Signals (real legitimacy evidence found)
- 41844 holders — reasonably distributed

## Token Security (GoPlus)
- is_honeypot: `0`
"""


def _write(tmp_path, text):
    p = tmp_path / "investigation-x.md"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parses_old_format(tmp_path):
    rec = bf.parse_investigation(_write(tmp_path, OLD_FORMAT))
    assert rec is not None
    assert rec["verdict"] == "CAUTION"
    assert rec["score"] == 68
    assert len(rec["messages"]) == 3
    assert "OpenAI" in rec["messages"][1]["content"]        # recon in user turn
    assert "Verdict: CAUTION" in rec["messages"][2]["content"]  # verdict in assistant turn


def test_parses_new_format_with_embedded_score(tmp_path):
    rec = bf.parse_investigation(_write(tmp_path, NEW_FORMAT))
    assert rec is not None
    assert rec["verdict"] == "CAUTION"
    assert rec["score"] == 68  # pulled from "(68/100)" in the verdict line
    assert "Positive signals" in rec["messages"][2]["content"]


def test_rejects_report_without_verdict(tmp_path):
    bad = "# Investigation — X\n- **Target:** `0xabc`\n## Market & Liquidity\n- x\n"
    assert bf.parse_investigation(_write(tmp_path, bad)) is None


def test_rejects_report_without_recon(tmp_path):
    bad = "# Investigation — X\n- **Target:** `0xabc`\n- **Verdict:** REJECT (10/100)\n"
    assert bf.parse_investigation(_write(tmp_path, bad)) is None


def test_split_is_deterministic():
    t = "0xB8Cb9F0630fc8C956B6461A8425097230B1E0aCa".lower()
    assert bf._is_val(t) == bf._is_val(t)  # stable across calls


def test_system_prompt_encodes_the_design_law():
    # The 'absence of red flags is not safety' posture is the whole point of
    # VAPE's scoring — the training system prompt must carry it.
    assert "ABSENCE" in bf.SYSTEM_PROMPT
    assert "REJECT" in bf.SYSTEM_PROMPT
