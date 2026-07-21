"""Hermetic tests for scripts/acp-monitor/virtuals_evaluator.py's deterministic
parts — rate-gating, Virtuals-only candidate filtering/dedup, and ACP command
construction. Every `acp` CLI call and network fetch is mocked/monkeypatched;
this never shells out to a real `acp` binary or hits a real network, since
neither exists in a hermetic test environment (the real CLI only runs on the
persistent ACP host — see the module's own docstring)."""
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(ROOT, "scripts", "acp-monitor", "virtuals_evaluator.py")

spec = importlib.util.spec_from_file_location("virtuals_evaluator", MODULE_PATH)
ve = importlib.util.module_from_spec(spec)
sys.modules["virtuals_evaluator"] = ve
spec.loader.exec_module(ve)


def _isolate_state_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(ve, "STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setattr(ve, "SEEN_PATH", str(tmp_path / "seen.json"))
    monkeypatch.setattr(ve, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(ve, "CATALOG_PATH", str(tmp_path / "catalog.md"))
    monkeypatch.setattr(ve, "LESSONS_PATH", str(tmp_path / "lessons.jsonl"))


# --------------------------------------------------------------- rate gating

def test_seconds_since_last_attempt_none_when_no_record(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    assert ve.seconds_since_last_attempt() is None


def test_remaining_today_is_full_cap_on_a_new_day(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    assert ve.remaining_today() == ve.DAILY_CAP


def test_mark_attempt_then_seconds_since_last_attempt_is_near_zero(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    ve.mark_attempt()
    assert ve.seconds_since_last_attempt() < 5


def test_record_job_increments_count_and_remaining_decreases(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    ve.record_job()
    ve.record_job()
    assert ve.remaining_today() == ve.DAILY_CAP - 2


def test_run_skips_when_interval_not_up(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    ve.mark_attempt()
    result = ve.run()
    assert result["hired"] is False
    assert "interval" in result["note"]


def test_run_skips_when_daily_cap_reached(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    state = {"date": ve._today(), "count": ve.DAILY_CAP}
    ve._save_json(ve.STATE_PATH, state)
    result = ve.run()
    assert result["hired"] is False
    assert "daily cap" in result["note"]


# ---------------------------------------------------------- candidate sourcing

def _fake_trending_response(tokens):
    class R:
        status_code = 200

        def json(self):
            return {"tokens": tokens}
    return R()


def test_fresh_virtuals_candidate_filters_to_isVirtuals_only(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    tokens = [
        {"isVirtuals": False, "token": {"address": "0xAAA", "symbol": "NOTV"}},
        {"isVirtuals": True, "token": {"address": "0xBBB", "symbol": "VIRT1", "name": "Virtuals One"}},
    ]

    class fake_requests:
        @staticmethod
        def get(url, timeout=15):
            return _fake_trending_response(tokens)

    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    result = ve.fresh_virtuals_candidate()
    assert result == ("0xBBB", "VIRT1", "Virtuals One")


def test_fresh_virtuals_candidate_skips_recently_seen(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    ve._mark_seen("0xBBB")
    tokens = [
        {"isVirtuals": True, "token": {"address": "0xBBB", "symbol": "VIRT1"}},
        {"isVirtuals": True, "token": {"address": "0xCCC", "symbol": "VIRT2", "name": "Virtuals Two"}},
    ]

    class fake_requests:
        @staticmethod
        def get(url, timeout=15):
            return _fake_trending_response(tokens)

    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    result = ve.fresh_virtuals_candidate()
    assert result == ("0xCCC", "VIRT2", "Virtuals Two")


def test_fresh_virtuals_candidate_none_when_all_recently_seen(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    ve._mark_seen("0xBBB")
    tokens = [{"isVirtuals": True, "token": {"address": "0xBBB", "symbol": "VIRT1"}}]

    class fake_requests:
        @staticmethod
        def get(url, timeout=15):
            return _fake_trending_response(tokens)

    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    assert ve.fresh_virtuals_candidate() is None


def test_fresh_virtuals_candidate_none_on_fetch_failure(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)

    class fake_requests:
        @staticmethod
        def get(url, timeout=15):
            raise RuntimeError("network down")

    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    assert ve.fresh_virtuals_candidate() is None


# -------------------------------------------------------------------- ACP IO

def test_ACP_dry_run_never_shells_out(monkeypatch):
    monkeypatch.setattr(ve, "DRY", True)
    ok, parsed, out, err = ve._ACP(["client", "create-job", "--provider", "vape"])
    assert ok is True
    assert parsed["dryRun"] is True
    assert parsed["cmd"] == ["client", "create-job", "--provider", "vape"]


def test_ACP_wraps_subprocess_failure_without_raising(monkeypatch):
    monkeypatch.setattr(ve, "DRY", False)

    def fake_run(*a, **kw):
        raise FileNotFoundError("acp binary not found")

    monkeypatch.setattr(ve.subprocess, "run", fake_run)
    ok, parsed, out, err = ve._ACP(["job", "status", "--job-id", "1"])
    assert ok is False
    assert parsed is None
    assert "acp binary not found" in err


def test_ACP_parses_json_stdout_on_success(monkeypatch):
    monkeypatch.setattr(ve, "DRY", False)

    class FakeProc:
        returncode = 0
        stdout = json.dumps({"jobId": "42"})
        stderr = ""

    monkeypatch.setattr(ve.subprocess, "run", lambda *a, **kw: FakeProc())
    ok, parsed, out, err = ve._ACP(["client", "create-job"])
    assert ok is True
    assert parsed == {"jobId": "42"}


def test_extract_job_id_checks_known_keys():
    assert ve._extract_job_id({"jobId": "1"}) == "1"
    assert ve._extract_job_id({"job_id": "2"}) == "2"
    assert ve._extract_job_id({"id": "3"}) == "3"
    assert ve._extract_job_id({"onChainJobId": "4"}) == "4"
    assert ve._extract_job_id({"nothing": "here"}) is None
    assert ve._extract_job_id("not-a-dict") is None


def test_job_is_submitted_recognizes_phase_and_deliverable():
    assert ve._job_is_submitted({"phase": "submitted"}) is True
    assert ve._job_is_submitted({"status": "completed"}) is True
    assert ve._job_is_submitted({"deliverable": {"verdict": "LOW"}}) is True
    assert ve._job_is_submitted({"phase": "funded"}) is False
    assert ve._job_is_submitted("not-a-dict") is False


def test_resolve_vape_agent_id_falls_back_on_browse_failure(monkeypatch):
    monkeypatch.setattr(ve, "_ACP", lambda *a, **kw: (False, None, "", "browse timed out"))
    assert ve.resolve_vape_agent_id() == "vape"


def test_resolve_vape_agent_id_extracts_id_from_matching_agent(monkeypatch):
    monkeypatch.setattr(ve, "_ACP", lambda *a, **kw: (
        True, [{"name": "VAPE", "id": "agent-123"}, {"name": "other", "id": "agent-999"}], "", ""))
    assert ve.resolve_vape_agent_id() == "agent-123"


# ---------------------------------------------------------------- full run()

def test_run_creates_funds_and_records_a_real_job(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(ve, "fresh_virtuals_candidate", lambda: ("0xBBB", "VIRT1", "Virtuals One"))
    monkeypatch.setattr(ve, "resolve_vape_agent_id", lambda: "vape")
    monkeypatch.setattr(ve, "create_job", lambda provider_id, offering, requirement: (True, {"jobId": "77"}, "{}", ""))
    monkeypatch.setattr(ve, "fund_job", lambda job_id, amount: (True, {"status": "funded"}, "{}", ""))
    monkeypatch.setattr(ve, "job_status", lambda job_id: (True, {"phase": "funded"}, "{}", ""))
    monkeypatch.setattr(ve, "time", type("T", (), {"sleep": staticmethod(lambda s: None)}))

    result = ve.run()
    assert result["hired"] is True
    assert result["job"] == "77"
    assert result["submitted"] is False
    assert ve.remaining_today() == ve.DAILY_CAP - 1


def test_run_skips_when_no_fresh_candidate(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(ve, "fresh_virtuals_candidate", lambda: None)
    result = ve.run()
    assert result["hired"] is False
    assert "candidate" in result["note"]
    # A candidate-sourcing miss should NOT consume the interval gate — there
    # was no real ACP action attempted.
    assert ve.seconds_since_last_attempt() is None


def test_run_still_counts_job_when_fund_succeeds_but_create_job_id_missing_is_a_noop(tmp_path, monkeypatch):
    _isolate_state_paths(tmp_path, monkeypatch)
    monkeypatch.setattr(ve, "fresh_virtuals_candidate", lambda: ("0xBBB", "VIRT1", "Virtuals One"))
    monkeypatch.setattr(ve, "resolve_vape_agent_id", lambda: "vape")
    monkeypatch.setattr(ve, "create_job", lambda provider_id, offering, requirement: (True, {"noJobIdField": True}, "{}", ""))
    result = ve.run()
    assert result["hired"] is False
    assert ve.remaining_today() == ve.DAILY_CAP  # no job was ever funded
