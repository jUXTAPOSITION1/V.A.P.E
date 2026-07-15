"""Tests for skillforge/findings_chain.py — tamper-evidence over
findings.jsonl via periodic hash-chained seals, independent of the
schema/writer of any individual finding line.

Every test points FINDINGS_PATH/CHAIN_PATH at tmp_path files (via
monkeypatch) rather than the real skillforge/memory/ files, so these never
touch or depend on VAPE's real, live findings log.
"""
import json

from skillforge import findings_chain as fc


def _write_lines(path, lines):
    with open(path, "w") as f:
        for line in lines:
            f.write(line if line.endswith("\n") else line + "\n")


def _finding(title):
    return json.dumps({"category": "finding", "title": title})


def test_seal_on_empty_findings_file_is_a_noop(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(tmp_path / "findings.chain.jsonl"))
    assert fc.seal() is None
    assert not (tmp_path / "findings.chain.jsonl").exists()


def test_seal_covers_exactly_the_new_lines_since_last_seal(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a"), _finding("b")])
    first = fc.seal()
    assert first["sealed_through_line"] == 2
    assert first["new_lines_sealed"] == 2

    _write_lines(findings, [_finding("a"), _finding("b"), _finding("c")])
    second = fc.seal()
    assert second["sealed_through_line"] == 3
    assert second["new_lines_sealed"] == 1  # only the new line, not re-hashing a+b
    assert second["chain_hash"] != first["chain_hash"]


def test_seal_again_with_no_new_lines_is_a_noop(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a")])
    fc.seal()
    assert fc.seal() is None
    assert len(chain.read_text().strip().splitlines()) == 1


def test_verify_ok_on_a_clean_sealed_file(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a"), _finding("b")])
    fc.seal()
    _write_lines(findings, [_finding("a"), _finding("b"), _finding("c")])
    fc.seal()

    result = fc.verify()
    assert result == {"ok": True, "seals_checked": 2, "lines_covered": 3, "unsealed_lines": 0}


def test_verify_reports_unsealed_lines_without_failing(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a")])
    fc.seal()
    _write_lines(findings, [_finding("a"), _finding("b")])  # new line, not sealed yet

    result = fc.verify()
    assert result["ok"] is True
    assert result["lines_covered"] == 1
    assert result["unsealed_lines"] == 1


def test_verify_with_no_seals_at_all_is_ok(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(tmp_path / "findings.chain.jsonl"))
    result = fc.verify()
    assert result == {"ok": True, "seals_checked": 0, "lines_covered": 0, "unsealed_lines": 0}


def test_verify_detects_a_sealed_line_being_altered(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a"), _finding("b")])
    fc.seal()

    # Tamper: rewrite an already-sealed line's content.
    _write_lines(findings, [_finding("a-TAMPERED"), _finding("b")])

    result = fc.verify()
    assert result["ok"] is False
    assert result["broken_at_seal"] == 0
    assert "altered" in result["reason"]


def test_verify_detects_a_sealed_line_being_deleted(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a"), _finding("b"), _finding("c")])
    fc.seal()

    # Tamper: delete a sealed line outright, shrinking the file.
    _write_lines(findings, [_finding("a"), _finding("c")])

    result = fc.verify()
    assert result["ok"] is False
    assert result["broken_at_seal"] == 0
    assert "deleted" in result["reason"]


def test_verify_detects_tampering_in_a_later_seal_segment(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain = tmp_path / "findings.chain.jsonl"
    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain))

    _write_lines(findings, [_finding("a")])
    fc.seal()
    _write_lines(findings, [_finding("a"), _finding("b")])
    fc.seal()
    _write_lines(findings, [_finding("a"), _finding("b"), _finding("c")])
    fc.seal()

    # Tamper with the SECOND seal's segment (line "b"), leaving the first
    # seal's segment ("a") untouched — the break must be attributed to
    # seal #1, not #0.
    _write_lines(findings, [_finding("a"), _finding("b-TAMPERED"), _finding("c")])

    result = fc.verify()
    assert result["ok"] is False
    assert result["broken_at_seal"] == 1


def test_seal_is_deterministic_given_the_same_content(monkeypatch, tmp_path):
    findings = tmp_path / "findings.jsonl"
    chain1 = tmp_path / "chain1.jsonl"
    chain2 = tmp_path / "chain2.jsonl"

    _write_lines(findings, [_finding("a"), _finding("b")])

    monkeypatch.setattr(fc, "FINDINGS_PATH", str(findings))
    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain1))
    hash1 = fc.seal()["chain_hash"]

    monkeypatch.setattr(fc, "CHAIN_PATH", str(chain2))
    hash2 = fc.seal()["chain_hash"]

    assert hash1 == hash2
