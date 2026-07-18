"""Tests for scripts/build_external_corpus.py's transform + merge logic.
Hermetic — no live network call (this sandbox's egress proxy blocks
services.nvd.nist.gov/api.github.com anyway; the real fetch functions only
run for real on a normal GitHub Actions runner or the training GPU box).
Fixtures below mirror the real NVD/GitHub API response shapes captured
during development, not invented ones."""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "build_external_corpus", os.path.join(ROOT, "scripts", "build_external_corpus.py"))
bec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bec)


# Real NVD API 2.0 `vulnerabilities[]` entry shape (fields trimmed to what the
# parser reads).
_CVE_ITEM = {
    "cve": {
        "id": "CVE-2023-99999",
        "descriptions": [
            {"lang": "es", "value": "Descripcion en espanol, debe ser ignorada."},
            {"lang": "en", "value": "A reentrancy vulnerability in a Solidity smart contract allows an attacker to drain funds."},
        ],
        "metrics": {
            "cvssMetricV31": [{"cvssData": {"baseSeverity": "HIGH", "baseScore": 8.1}}],
        },
    }
}


def test_cve_to_row_extracts_english_description_and_severity():
    row = bec.cve_to_row(_CVE_ITEM)
    assert row["source"] == "cve"
    assert row["source_id"] == "CVE-2023-99999"
    assert "reentrancy" in row["messages"][1]["content"]
    assert "espanol" not in row["messages"][1]["content"]
    assert row["messages"][2]["content"] == "Severity: HIGH"


def test_cve_to_row_none_without_english_description():
    item = {"cve": {"id": "CVE-1", "descriptions": [{"lang": "fr", "value": "..."}],
                    "metrics": {"cvssMetricV31": [{"cvssData": {"baseSeverity": "HIGH"}}]}}}
    assert bec.cve_to_row(item) is None


def test_cve_to_row_none_without_cvss_severity():
    item = {"cve": {"id": "CVE-2", "descriptions": [{"lang": "en", "value": "desc"}], "metrics": {}}}
    assert bec.cve_to_row(item) is None


def test_cve_to_row_falls_back_through_cvss_versions():
    item = {"cve": {"id": "CVE-3", "descriptions": [{"lang": "en", "value": "desc"}],
                    "metrics": {"cvssMetricV2": [{"baseSeverity": "MEDIUM"}]}}}
    row = bec.cve_to_row(item)
    assert row["messages"][2]["content"] == "Severity: MEDIUM"


# Real code-423n4 data/*.json index entry shape (captured from
# code-423n4/2023-01-numoen-findings/data/0Kage-229.json).
_C4R_INDEX_H = {"contest": 207, "handle": "someAuditor", "risk": "H",
                "title": "Reentrancy drains vault", "issueId": 42,
                "issueUrl": "https://github.com/code-423n4/2023-01-numoen-findings/issues/42"}
_C4R_INDEX_GAS = {"contest": 207, "handle": "0Kage", "risk": "G",
                  "title": "Gas Optimizations", "issueId": 229,
                  "issueUrl": "https://github.com/code-423n4/2023-01-numoen-findings/issues/229"}


def test_code4rena_row_built_for_high_risk_finding():
    row = bec.code4rena_finding_to_row("code-423n4/2023-01-numoen-findings", _C4R_INDEX_H,
                                        "Detailed real writeup of the reentrancy path.")
    assert row["source"] == "code4rena"
    assert row["source_id"] == "code-423n4/2023-01-numoen-findings#42"
    assert row["messages"][2]["content"] == "Severity: HIGH"
    assert "reentrancy path" in row["messages"][1]["content"]


def test_code4rena_row_none_for_gas_finding():
    assert bec.code4rena_finding_to_row("repo", _C4R_INDEX_GAS, "some gas writeup") is None


def test_code4rena_row_none_without_issue_body():
    assert bec.code4rena_finding_to_row("repo", _C4R_INDEX_H, None) is None
    assert bec.code4rena_finding_to_row("repo", _C4R_INDEX_H, "") is None


def test_merge_rows_fresh_wins_on_collision_else_union():
    cached = [
        {"source": "cve", "source_id": "CVE-1", "messages": [{"role": "assistant", "content": "Severity: LOW"}]},
        {"source": "cve", "source_id": "CVE-2", "messages": [{"role": "assistant", "content": "Severity: HIGH"}]},
    ]
    fresh = [
        {"source": "cve", "source_id": "CVE-1", "messages": [{"role": "assistant", "content": "Severity: CRITICAL"}]},
    ]
    merged = bec.merge_rows(cached, fresh)
    by_id = {r["source_id"]: r for r in merged}
    assert len(merged) == 2
    assert by_id["CVE-1"]["messages"][0]["content"] == "Severity: CRITICAL"  # fresh won
    assert by_id["CVE-2"]["messages"][0]["content"] == "Severity: HIGH"      # untouched cached row kept


def test_source_counts():
    rows = [{"source": "cve"}, {"source": "cve"}, {"source": "code4rena"}]
    assert bec._source_counts(rows) == {"cve": 2, "code4rena": 1}
