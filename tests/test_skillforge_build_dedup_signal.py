"""Tests for agents/skillforge_build.py's ALREADY BUILT signal — real gap
confirmed 2026-07-27: propose() had no way to know it had already proposed
and merged the identical tool ("Arbitrum Transaction Tracer for
Defillama-Hack Incidents", PR #293) before proposing it again the very next
day (PR #316), since the same underlying tool-registry/bounty-radar signal
hadn't changed. Hermetic: reads a temp build-requests/ dir, no network/LLM
call.
"""
import json

from agents import skillforge_build as sb


def test_already_built_titles_deslugifies_directory_names(tmp_path, monkeypatch):
    build_requests = tmp_path / "build-requests"
    build_requests.mkdir()
    (build_requests / "skillforge-arbitrum-transaction-tracer-for-defillam-20260726").mkdir()
    (build_requests / "skillforge-defillama-tvl-and-price-data-scraper-20260721").mkdir()
    monkeypatch.setattr(sb, "BUILD_REQUESTS_DIR", str(build_requests))

    titles = sb._already_built_titles()
    assert "arbitrum transaction tracer for defillam" in titles
    assert "defillama tvl and price data scraper" in titles


def test_already_built_titles_ignores_non_skillforge_dirs(tmp_path, monkeypatch):
    build_requests = tmp_path / "build-requests"
    build_requests.mkdir()
    (build_requests / "some-other-dir").mkdir()
    monkeypatch.setattr(sb, "BUILD_REQUESTS_DIR", str(build_requests))
    assert sb._already_built_titles() == []


def test_already_built_titles_missing_dir_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "BUILD_REQUESTS_DIR", str(tmp_path / "nope"))
    assert sb._already_built_titles() == []


def test_gather_signals_includes_already_built_when_other_signal_present(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "REGISTRY_PATH", str(tmp_path / "nonexistent.json"))
    monkeypatch.setattr(sb, "search_memory", None)
    build_requests = tmp_path / "build-requests"
    build_requests.mkdir()
    (build_requests / "skillforge-arbitrum-transaction-tracer-for-defillam-20260726").mkdir()
    monkeypatch.setattr(sb, "BUILD_REQUESTS_DIR", str(build_requests))
    radar_dir = tmp_path / "intel" / "bounty-radar"
    radar_dir.mkdir(parents=True)
    (radar_dir / "opportunities.json").write_text(json.dumps(
        [{"name": "X", "platform": "y", "fitScore": 99, "prizeUsd": 5, "desc": "z"}]))
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))

    signals = sb.gather_signals()
    assert "ALREADY BUILT" in signals
    assert "arbitrum transaction tracer for defillam" in signals
    assert "TOP BOUNTY-RADAR OPPORTUNITIES" in signals


def test_gather_signals_skips_cycle_when_only_already_built_present(tmp_path, monkeypatch):
    """Already-built history alone is not a justification to spend a real
    LLM call — an otherwise-empty cycle must still skip."""
    monkeypatch.setattr(sb, "REGISTRY_PATH", str(tmp_path / "nonexistent.json"))
    monkeypatch.setattr(sb, "search_memory", None)
    build_requests = tmp_path / "build-requests"
    build_requests.mkdir()
    (build_requests / "skillforge-arbitrum-transaction-tracer-for-defillam-20260726").mkdir()
    monkeypatch.setattr(sb, "BUILD_REQUESTS_DIR", str(build_requests))
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))

    assert sb.gather_signals() == ""
