"""Tests for agents/bounty_ops.py (Task #197) — the classified,
checklist-tracked Bounty Ops system built on top of agents/scout.py's
track/vapeFit fix. Hermetic: no real LLM calls, no real filesystem writes
outside tmp_path.
"""
from unittest import mock

from agents import bounty_ops as bo


def _bounty(name="SmarDex Smart Contracts", platform="hackenproof", fit_score=66, prize=500_000):
    return {"id": f"{platform}:{name}", "name": name, "platform": platform, "url": "https://example.com/x",
            "prizeUsd": prize, "track": "bounty", "vapeFit": True,
            "vapeFitReason": "Solidity/EVM — matches agents/deep_dive_audit.py",
            "bountyFitScore": fit_score, "tags": ["contract", "solidity"]}


def test_select_candidates_excludes_non_fit_and_incidents():
    opps = [
        _bounty("Fit One", fit_score=80),
        {"id": "x", "name": "Not Fit", "platform": "hackerone", "track": "bounty", "vapeFit": False,
         "bountyFitScore": 0},
        {"id": "y", "name": "An Incident", "platform": "defillama-hack", "track": "incident", "fitScore": 95},
    ]
    selected = bo.select_candidates(opps)
    assert [o["name"] for o in selected] == ["Fit One"]


def test_select_candidates_respects_threshold_and_limit():
    opps = [_bounty(f"Prog {i}", fit_score=30 + i) for i in range(20)]
    selected = bo.select_candidates(opps, limit=3)
    assert len(selected) == 3
    # highest fit first
    assert selected[0]["bountyFitScore"] >= selected[1]["bountyFitScore"] >= selected[2]["bountyFitScore"]
    for o in selected:
        assert o["bountyFitScore"] >= bo.BOUNTY_FIT_THRESHOLD


def test_select_candidates_dedupes_by_id():
    dup = _bounty("Same", fit_score=90)
    opps = [dup, dup.copy()]
    selected = bo.select_candidates(opps)
    assert len(selected) == 1


def test_slug_is_filesystem_safe():
    assert bo._slug("SmarDex Smart Contracts") == "smardex-smart-contracts"
    assert bo._slug("1inch Smart Contract!") == "1inch-smart-contract"


def test_parse_checklist_text_handles_dash_and_numbered_lines():
    text = "- First item\n- Second item\n1. Third item\n\nSome stray line ignored"
    items = bo._parse_checklist_text(text)
    assert items == ["First item", "Second item", "Third item"]


def test_generate_checklist_returns_empty_on_llm_unavailable():
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("[llm unavailable: no keys]", None)):
        items = bo.generate_checklist(_bounty())
    assert items == []


def test_generate_checklist_returns_empty_on_exception():
    with mock.patch("agents.llm.ask_oci_grok_safe", side_effect=Exception("boom")):
        items = bo.generate_checklist(_bounty())
    assert items == []


def test_generate_checklist_parses_real_response():
    with mock.patch("agents.llm.ask_oci_grok_safe", return_value=("- Do X\n- Do Y\n- Do Z", "xai_1")):
        items = bo.generate_checklist(_bounty())
    assert items == ["Do X", "Do Y", "Do Z"]


def test_merge_checklist_items_preserves_done_state():
    existing = [{"item": "Do X", "done": True}, {"item": "Do Y", "done": False}]
    merged, added = bo._merge_checklist_items(existing, ["Do X", "Do Y", "Do Z"])
    assert added == 1
    by_text = {i["item"]: i["done"] for i in merged}
    assert by_text["Do X"] is True   # never reset
    assert by_text["Do Y"] is False
    assert by_text["Do Z"] is False  # newly appended


def test_build_entry_new_candidate_tracks_and_generates_checklist():
    with mock.patch.object(bo, "generate_checklist", return_value=["Step 1", "Step 2"]), \
         mock.patch.object(bo, "find_vape_report", return_value=(None, None)):
        entry, changed = bo.build_entry(_bounty(), existing=None)
    assert changed is True
    assert len(entry["checklist"]) == 2
    assert entry["progress"][0]["event"].startswith("Started tracking")


def test_build_entry_existing_candidate_preserves_done_and_skips_llm_when_fresh():
    import time
    existing = {
        "id": "hackenproof:SmarDex Smart Contracts", "checklist": [{"item": "Step 1", "done": True}],
        "progress": [{"ts": "t0", "event": "Started tracking as a real Bounty Op (fit 66)."}],
        "checklistGeneratedAt": time.time(), "vapeReportUrl": None,
    }
    with mock.patch.object(bo, "generate_checklist") as gen, \
         mock.patch.object(bo, "find_vape_report", return_value=(None, None)):
        entry, changed = bo.build_entry(_bounty(), existing=existing)
    gen.assert_not_called()  # fresh checklist, no LLM spend this run
    assert entry["checklist"][0]["done"] is True  # preserved
    assert changed is False


def test_build_entry_links_vape_report_when_found():
    with mock.patch.object(bo, "generate_checklist", return_value=[]), \
         mock.patch.object(bo, "find_vape_report", return_value=("intel/audits/poc-reports/audit-smardex-2026.md", "audit")):
        entry, changed = bo.build_entry(_bounty(), existing=None)
    assert entry["vapeReportUrl"] == "intel/audits/poc-reports/audit-smardex-2026.md"
    assert changed is True
    assert any("Linked VAPE's own real audit report" in p["event"] for p in entry["progress"])


def test_find_vape_report_matches_by_token_overlap(tmp_path, monkeypatch):
    poc_dir = tmp_path / "intel" / "audits" / "poc-reports"
    poc_dir.mkdir(parents=True)
    (poc_dir / "audit-smardex-smart-contracts-2026-07-19.md").write_text("# report")
    monkeypatch.setattr(bo, "_REPO_ROOT", str(tmp_path))
    path, kind = bo.find_vape_report("SmarDex Smart Contracts")
    assert path == "intel/audits/poc-reports/audit-smardex-smart-contracts-2026-07-19.md"
    assert kind == "audit"


def test_find_vape_report_no_match_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(bo, "_REPO_ROOT", str(tmp_path))
    path, kind = bo.find_vape_report("Totally Unrelated Program")
    assert path is None
    assert kind is None


def test_run_writes_index_and_entry_files(tmp_path, monkeypatch):
    opps_path = tmp_path / "opportunities.json"
    import json
    json.dump([_bounty("Tracked Program", fit_score=70)], open(opps_path, "w"))
    bounty_ops_dir = tmp_path / "bounty-ops"

    monkeypatch.setattr(bo.scout, "OPPORTUNITIES_PATH", str(opps_path))
    monkeypatch.setattr(bo, "BOUNTY_OPS_DIR", str(bounty_ops_dir))
    monkeypatch.setattr(bo, "INDEX_PATH", str(bounty_ops_dir / "INDEX.md"))

    with mock.patch.object(bo, "generate_checklist", return_value=["Do a thing"]), \
         mock.patch.object(bo, "find_vape_report", return_value=(None, None)):
        result = bo.run(limit=5)

    assert result["new"] == 1
    assert (bounty_ops_dir / "tracked-program.json").exists()
    index_text = (bounty_ops_dir / "INDEX.md").read_text()
    assert "Tracked Program" in index_text
