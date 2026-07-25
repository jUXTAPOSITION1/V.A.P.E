"""Tests for agents/x402_directory_register.py's duplicate-listing-avoidance
logic (2026-07-25): register_402index() must skip any offering already
recorded in STATE_PATH, since 402index.io's /register endpoint has
undocumented dedup behavior and re-sending an already-listed offering risks
creating a duplicate. Hermetic: _post (the real network call) and
STATE_PATH are always mocked/redirected to a tmp file, no real network call.
"""
import json
from unittest import mock

from agents import x402_directory_register as reg


def _fake_post_ok(url, payload, **kwargs):
    return 201, {"id": "fake", "status": "pending review"}


def test_all_offerings_count_matches_worker_routes():
    names = [n for n, _meta, _prefix in reg._all_offerings()]
    assert len(names) == len(set(names)), "no duplicate offering names across tiers"
    assert "exploit_check" in names
    assert "dossier_check" in names
    assert "bounty_deep_dive" in names
    assert "token_intel" in names


def test_load_state_defaults_to_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "nope.json"))
    state = reg._load_state()
    assert state == {"registered_402index": []}


def test_save_then_load_state_roundtrip(tmp_path, monkeypatch):
    path = str(tmp_path / "state.json")
    monkeypatch.setattr(reg, "STATE_PATH", path)
    reg._save_state({"registered_402index": ["exploit_check"]})
    assert reg._load_state()["registered_402index"] == ["exploit_check"]


def test_register_402index_skips_already_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    reg._save_state({"registered_402index": ["exploit_check", "token_safety_check"]})
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok) as m_post, \
         mock.patch.object(reg, "time") as m_time:
        results = reg.register_402index(only={"exploit_check", "dossier_check"})
    # Only dossier_check should actually be POSTed — exploit_check is
    # already-registered and skipped even though it's in `only`.
    posted_names = [c.args[1]["name"] for c in m_post.call_args_list]
    assert posted_names == ["VAPE dossier_check"]
    assert len(results) == 1
    assert results[0]["offering"] == "dossier_check"
    assert results[0]["ok"] is True


def test_register_402index_force_all_resends_everything_in_only(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    reg._save_state({"registered_402index": ["exploit_check"]})
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok) as m_post, \
         mock.patch.object(reg, "time"):
        results = reg.register_402index(only={"exploit_check"}, force_all=True)
    assert len(results) == 1
    assert m_post.call_count == 1


def test_register_402index_records_new_successes_in_state(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(reg, "STATE_PATH", str(state_path))
    reg._save_state({"registered_402index": ["exploit_check"]})
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok), \
         mock.patch.object(reg, "time"):
        reg.register_402index(only={"dossier_check", "tx_decode"})
    saved = json.loads(state_path.read_text())
    assert set(saved["registered_402index"]) == {"exploit_check", "dossier_check", "tx_decode"}


def test_register_402index_does_not_record_failed_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    with mock.patch.object(reg, "_post", return_value=(500, {"error": "boom"})), \
         mock.patch.object(reg, "time"):
        results = reg.register_402index(only={"dossier_check"})
    assert results[0]["ok"] is False
    assert reg._load_state()["registered_402index"] == []
