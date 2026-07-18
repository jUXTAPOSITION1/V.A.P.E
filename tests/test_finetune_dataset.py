"""Tests for scripts/build_finetune_dataset.py's investigation parser. The
corpus is only trustworthy if every training pair traces to a real verdict, so
these pin: both report-format generations parse, the label is never fabricated
when the fields are missing, and the split is deterministic."""
import importlib.util
import json
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


SECURITY_SWEEP = """# VAPE Security Sweep Report

**Generated:** 2026-07-17 08:11 UTC

---

## THREAT LEVEL: \U0001F534 HIGH

Computed deterministically: 7 incident(s) in the last 7 days across the
tracked feed, 0 of which exceeded $50M within the last 14 days.

---

## Recent DeFi/Crypto Incidents (real, DeFiLlama hacks feed)

| Date | Protocol | Amount Lost |
|------|----------|-------------|
| 2026-07-16 | DefiTuna Lending | $0.58M |

---

### Summary
Some narrative prose that must never end up in the assistant output.
"""

SENTIMENT_SWEEP = """# Sentiment Sweep Report

---

## SENTIMENT SCORE: 2.5/10 (Fear / Bearish-leaning)

Real Fear & Greed index: **25** (Extreme Fear).
Previous reading: 22 (Extreme Fear).

---

## Web Signals — Virtuals / AI Agents

_No results returned this cycle._
"""


def _write_named(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_parse_sweep_report_extracts_deterministic_verdict_only(tmp_path):
    fp = _write_named(tmp_path, "security-x.md", SECURITY_SWEEP)
    rec = bf.parse_sweep_report(fp, "security")
    assert rec is not None
    assistant = rec["messages"][2]["content"]
    assert "THREAT LEVEL" in assistant
    assert "Computed deterministically" in assistant
    # The narrative prose under ### Summary must never leak into the output.
    assert "must never end up" not in assistant


def test_parse_sweep_report_input_excludes_narrative_headings(tmp_path):
    fp = _write_named(tmp_path, "security-x.md", SECURITY_SWEEP)
    rec = bf.parse_sweep_report(fp, "security")
    user = rec["messages"][1]["content"]
    assert "Recent DeFi/Crypto Incidents" in user


def test_parse_sweep_report_sentiment_has_no_separate_input_table(tmp_path):
    # Documented, expected behavior (see build_finetune_dataset.py's comment)
    # — sentiment reports have no real-data table distinct from the score
    # body itself, so they don't contribute examples via this parser.
    fp = _write_named(tmp_path, "sentiment-x.md", SENTIMENT_SWEEP)
    assert bf.parse_sweep_report(fp, "sentiment") is None


def test_parse_sweep_report_rejects_report_without_the_verdict_heading(tmp_path):
    fp = _write_named(tmp_path, "security-x.md", "# Report\n\nJust some text.\n")
    assert bf.parse_sweep_report(fp, "security") is None


def test_parse_lesson_requires_title_and_content():
    good = json.dumps({"id": "abc123", "title": "T", "content": "C",
                        "metadata": {"verdict": "PROCEED"}})
    rec = bf.parse_lesson(good)
    assert rec is not None
    assert rec["key"] == "abc123"
    assert "verdict: PROCEED" in rec["messages"][1]["content"]
    assert rec["messages"][2]["content"] == "C"

    missing_content = json.dumps({"id": "x", "title": "T"})
    assert bf.parse_lesson(missing_content) is None

    not_json = "not json at all"
    assert bf.parse_lesson(not_json) is None


def test_is_val_works_for_arbitrary_string_keys():
    # Renamed from a target-address-only key to a generic per-example key —
    # must still work for report filenames and lesson ids, not just addresses.
    assert bf._is_val("security-2026-07-17-08.md") == bf._is_val("security-2026-07-17-08.md")
