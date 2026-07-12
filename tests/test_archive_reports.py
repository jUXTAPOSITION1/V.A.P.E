"""Tests for scripts/archive_reports.py's pure parsing/metadata helpers and a
full byte-identical round-trip through a tarball, so the guarantee 'nothing is
lost, everything is recoverable' is enforced, not just asserted in a comment."""
import hashlib
import importlib.util
import os
import tarfile
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "archive_reports", os.path.join(ROOT, "scripts", "archive_reports.py"))
ar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ar)


def test_parse_date_timestamped():
    assert ar._parse_date("bounty_report_20260704_215941.md", "ts") == date(2026, 7, 4)


def test_parse_date_dashed():
    assert ar._parse_date("security-2026-06-10-08.md", "date") == date(2026, 6, 10)


def test_parse_date_rejects_unparseable():
    assert ar._parse_date("caution-list.md", "date") is None
    assert ar._parse_date("README.md", "ts") is None


def test_threat_extraction():
    assert ar._threat("## THREAT LEVEL: 🔴 HIGH\nbody") == "HIGH"
    assert ar._threat("Verdict: PROCEED (88/100)") == "PROCEED"
    assert ar._threat("no signal here") is None


def test_first_heading():
    assert ar._first_heading("# VAPE Security Sweep\nbody", "fallback") == "VAPE Security Sweep"
    assert ar._first_heading("no heading at all", "fallback") == "fallback"


def test_tarball_roundtrip_is_byte_identical(tmp_path):
    content = "# Report\n\nThreat Level: HIGH\n\nSome real bytes: café 🐇\n".encode("utf-8")
    tar_path = str(tmp_path / "reports-2026-06.tar.gz")
    ar._archive_into_tarball(tar_path, [("security-2026-06-10-08.md", content)], apply=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        got = tf.extractfile("security-2026-06-10-08.md").read()
    assert got == content
    assert hashlib.sha256(got).hexdigest() == hashlib.sha256(content).hexdigest()


def test_tarball_append_preserves_existing(tmp_path):
    tar_path = str(tmp_path / "reports-2026-06.tar.gz")
    ar._archive_into_tarball(tar_path, [("a.md", b"alpha")], apply=True)
    ar._archive_into_tarball(tar_path, [("b.md", b"bravo")], apply=True)
    with tarfile.open(tar_path, "r:gz") as tf:
        names = set(tf.getnames())
        assert names == {"a.md", "b.md"}
        assert tf.extractfile("a.md").read() == b"alpha"
        assert tf.extractfile("b.md").read() == b"bravo"


def test_dry_run_writes_nothing(tmp_path):
    tar_path = str(tmp_path / "reports-2026-06.tar.gz")
    ar._archive_into_tarball(tar_path, [("a.md", b"alpha")], apply=False)
    assert not os.path.exists(tar_path)
