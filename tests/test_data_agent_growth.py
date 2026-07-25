"""Tests for agents/data_agent.py's CDP-only growing-minimum pacing
mechanism (_growth_epoch, _daily_target_combined, _daily_targets, _due_now,
_State.count_today) — see the module docstring's "Rate limits, CDP-pinned
instance" section for the full design. Hermetic: every test points
GROWTH_EPOCH_PATH at a tmp_path, never the real shared repo file.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from agents import data_agent


@pytest.fixture(autouse=True)
def _isolated_growth_epoch(tmp_path, monkeypatch):
    monkeypatch.setattr(data_agent, "GROWTH_EPOCH_PATH", str(tmp_path / "growth_epoch.json"))


def _fresh_state(tmp_path, name="growth_test"):
    state = data_agent._State(name)
    state.quota_path = str(tmp_path / f"{name}_quota.json")
    state.ledger_path = str(tmp_path / f"{name}_ledger.jsonl")
    return state


# ── _growth_epoch ─────────────────────────────────────────────────────────

def test_growth_epoch_creates_file_on_first_call():
    epoch = data_agent._growth_epoch()
    assert epoch == datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with open(data_agent.GROWTH_EPOCH_PATH) as f:
        assert json.load(f)["epoch"] == epoch


def test_growth_epoch_reads_back_a_persisted_date():
    with open(data_agent.GROWTH_EPOCH_PATH, "w") as f:
        json.dump({"epoch": "2026-01-01"}, f)
    assert data_agent._growth_epoch() == "2026-01-01"


def test_growth_epoch_falls_back_to_today_on_corrupted_file():
    with open(data_agent.GROWTH_EPOCH_PATH, "w") as f:
        f.write("not json")
    assert data_agent._growth_epoch() == datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── _daily_target_combined / _daily_targets ──────────────────────────────

def test_daily_target_combined_is_base_on_day_one():
    assert data_agent._daily_target_combined() == data_agent.GROWTH_BASE_DAILY


def test_daily_target_combined_compounds_by_day_index():
    epoch = (datetime.now(timezone.utc).date() - timedelta(days=5)).isoformat()
    with open(data_agent.GROWTH_EPOCH_PATH, "w") as f:
        json.dump({"epoch": epoch}, f)
    expected = data_agent.GROWTH_BASE_DAILY * (1.01 ** 5)
    assert data_agent._daily_target_combined() == pytest.approx(expected)


def test_daily_targets_split_sums_to_ceil_of_combined():
    main, catalog = data_agent._daily_targets()
    import math
    assert main + catalog == math.ceil(data_agent._daily_target_combined())
    assert main >= catalog  # main gets the ceiling half


# ── _due_now ──────────────────────────────────────────────────────────────

def test_due_now_true_on_fresh_state(tmp_path):
    state = _fresh_state(tmp_path)
    due, remaining = data_agent._due_now(state, 100)
    assert due is True
    assert remaining == 100


def test_due_now_false_once_target_met(tmp_path):
    state = _fresh_state(tmp_path)
    state.record_hires(100)
    due, remaining = data_agent._due_now(state, 100)
    assert due is False
    assert remaining == 0


def test_due_now_false_immediately_after_a_hire_with_target_remaining(tmp_path):
    state = _fresh_state(tmp_path)
    state.mark_attempt()
    state.record_hires(1)
    due, remaining = data_agent._due_now(state, 100)
    assert due is False
    assert remaining == 99


def test_due_now_true_again_after_absolute_floor_elapses(tmp_path):
    state = _fresh_state(tmp_path)
    stale_ts = (datetime.now(timezone.utc)
                - timedelta(seconds=data_agent.ABSOLUTE_MIN_INTERVAL_SECONDS + 5)).isoformat().replace("+00:00", "Z")
    with open(state.quota_path, "w") as f:
        json.dump({"date": state._today(), "count": 1, "last_ts": stale_ts}, f)
    # A huge remaining/target ratio forces needed_interval down to the
    # absolute floor regardless of time-of-day, so this is deterministic.
    due, remaining = data_agent._due_now(state, 10_000_000)
    assert due is True
    assert remaining == 9_999_999


# ── _State.count_today ───────────────────────────────────────────────────

def test_count_today_zero_on_fresh_state(tmp_path):
    assert _fresh_state(tmp_path).count_today() == 0


def test_count_today_resets_on_a_new_day(tmp_path):
    state = _fresh_state(tmp_path)
    with open(state.quota_path, "w") as f:
        json.dump({"date": "2000-01-01", "count": 42}, f)
    assert state.count_today() == 0


def test_count_today_reflects_recorded_hires(tmp_path):
    state = _fresh_state(tmp_path)
    state.record_hires(3)
    assert state.count_today() == 3
