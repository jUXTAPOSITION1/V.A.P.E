"""Tests for agents/skillforge_build.py's bounty-radar signal — grounds
Grok's tool proposals in real $ opportunities (agents/scout.py's archive),
not only the tool registry's own gaps. Hermetic: reads a temp
opportunities.json, no network/LLM call.
"""
import json

from agents import skillforge_build as sb


def test_bounty_radar_signal_ranks_by_fit_and_formats(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))
    radar_dir = tmp_path / "intel" / "bounty-radar"
    radar_dir.mkdir(parents=True)
    opps = [
        {"name": "Low Fit", "platform": "hackenproof", "fitScore": 10, "prizeUsd": 1000, "desc": "minor"},
        {"name": "High Fit Bridge Hack", "platform": "defillama-hack", "fitScore": 95,
         "prizeUsd": 2_000_000, "desc": "bridge exploit needing cross-chain trace"},
    ]
    (radar_dir / "opportunities.json").write_text(json.dumps(opps))

    result = sb._bounty_radar_signal()
    assert len(result) == 2
    assert result[0].startswith("High Fit Bridge Hack")
    assert "fit 95" in result[0]
    assert "$2,000,000" in result[0]
    assert "bridge exploit needing cross-chain trace" in result[0]


def test_bounty_radar_signal_respects_max_items(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))
    radar_dir = tmp_path / "intel" / "bounty-radar"
    radar_dir.mkdir(parents=True)
    opps = [{"name": f"Opp {i}", "platform": "x", "fitScore": i, "prizeUsd": 1, "desc": ""} for i in range(20)]
    (radar_dir / "opportunities.json").write_text(json.dumps(opps))

    result = sb._bounty_radar_signal(max_items=3)
    assert len(result) == 3
    assert result[0].startswith("Opp 19")  # highest fitScore first


def test_bounty_radar_signal_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))
    assert sb._bounty_radar_signal() == []


def test_bounty_radar_signal_non_list_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))
    radar_dir = tmp_path / "intel" / "bounty-radar"
    radar_dir.mkdir(parents=True)
    (radar_dir / "opportunities.json").write_text(json.dumps({"not": "a list"}))
    assert sb._bounty_radar_signal() == []


def test_gather_signals_includes_bounty_radar_header(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "_REPO_ROOT", str(tmp_path))
    monkeypatch.setattr(sb, "REGISTRY_PATH", str(tmp_path / "nonexistent.json"))
    monkeypatch.setattr(sb, "search_memory", None)
    radar_dir = tmp_path / "intel" / "bounty-radar"
    radar_dir.mkdir(parents=True)
    (radar_dir / "opportunities.json").write_text(json.dumps(
        [{"name": "X", "platform": "y", "fitScore": 99, "prizeUsd": 5, "desc": "z"}]))

    signals = sb.gather_signals()
    assert "TOP BOUNTY-RADAR OPPORTUNITIES" in signals
    assert "X (y, fit 99" in signals
