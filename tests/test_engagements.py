"""Tests for agents/engagements.py's real, deterministic engagement-status
logic — no LLM, no network. Verifies the per-platform honesty rule: a
defillama-hack lead's status is derived strictly from
attack_response_state.json (never fabricated), and static seed-platform
leads are always "tracked_only" since VAPE has no real submission path
for any of them.
"""
from agents import engagements as eng


def _opp(name, platform, prize=1_000_000, fit=80, date_unix=1752364800):
    # id encodes {raw_name}-{date_unix} for defillama-hack, matching
    # agents/scout.py's fetch_defillama_hacks() id scheme.
    opp_id = f"{platform}:{name}-{date_unix}" if platform == "defillama-hack" else f"{platform}:{name}"
    return {"platform": platform, "id": opp_id, "name": name, "prizeUsd": prize,
            "fitScore": fit, "url": f"https://example.com/{name}"}


def test_below_fit_threshold_excluded():
    opps = [_opp("Tiny Lead", "defillama-hack", fit=10)]
    result = eng.build_engagements(opps, {})
    assert result == []


def test_defillama_hack_not_yet_attempted_when_state_empty():
    opps = [_opp("Some Hack", "defillama-hack")]
    result = eng.build_engagements(opps, {})
    assert result[0]["engagement"]["status"] == "not_yet_attempted"


def test_defillama_hack_investigated_when_resolved_true():
    opps = [_opp("Kelp", "defillama-hack", date_unix=1776470400)]
    state = {"2026-04-18:Kelp": {"resolved": True, "address": "0x" + "aa" * 20,
                                  "verdict": "REJECT", "report": "intel/investigations/x.md",
                                  "chain": "1", "checked_at": "2026-07-13T00:00:00Z"}}
    result = eng.build_engagements(opps, state)
    e = result[0]["engagement"]
    assert e["status"] == "investigated"
    assert e["address"] == "0x" + "aa" * 20
    assert e["verdict"] == "REJECT"
    assert e["chain"] == "1"


def test_defillama_hack_no_target_found_when_resolved_false():
    opps = [_opp("Kelp", "defillama-hack", date_unix=1776470400)]
    state = {"2026-04-18:Kelp": {"resolved": False, "checked_at": "2026-07-13T00:00:00Z"}}
    result = eng.build_engagements(opps, state)
    assert result[0]["engagement"]["status"] == "no_target_found"


def test_static_seed_platform_always_tracked_only_never_fabricated():
    for platform in ("immunefi", "cantina", "sherlock", "hackerone", "hackenproof",
                      "agentarena", "code4rena"):
        opps = [_opp("Some Contest", platform)]
        result = eng.build_engagements(opps, {"anything": {"resolved": True}})
        assert result[0]["engagement"]["status"] == "tracked_only"
        assert "no_key" not in result[0]["engagement"]  # never a fabricated key/action


def test_incident_state_key_matches_security_sweep_scheme():
    # Must exactly match attempt_incident_forensics()'s f"{h['date']}:{h['name']}".
    opp = _opp("Kelp", "defillama-hack", date_unix=1776470400)
    assert eng._incident_state_key(opp) == "2026-04-18:Kelp"


def test_results_sorted_by_fit_score_descending():
    opps = [_opp("Low", "defillama-hack", fit=55), _opp("High", "defillama-hack", fit=95)]
    result = eng.build_engagements(opps, {})
    assert [r["lead"] for r in result] == ["High", "Low"]


def test_render_status_md_omits_empty_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(eng, "INTEL_DIR", str(tmp_path))
    engagements = eng.build_engagements([_opp("Kelp", "defillama-hack")], {})
    text = eng._render_status_md(engagements)
    assert "Not yet attempted this cycle" in text
    assert "Real investigations launched" not in text
    assert "Tracked for visibility only" not in text


def test_log_only_appends_on_real_status_change(tmp_path, monkeypatch):
    monkeypatch.setattr(eng, "INTEL_DIR", str(tmp_path))
    monkeypatch.setattr(eng, "LOG_PATH", str(tmp_path / "engagement-log.jsonl"))
    opps = [_opp("Kelp", "defillama-hack")]
    engagements = eng.build_engagements(opps, {})

    state = {}
    n1 = eng._append_log_on_change(engagements, state)
    assert n1 == 1  # first time seeing this lead

    n2 = eng._append_log_on_change(engagements, state)
    assert n2 == 0  # unchanged status, no new line

    with open(str(tmp_path / "engagement-log.jsonl")) as f:
        assert len(f.readlines()) == 1
