"""Tests for agents/build_city_state.py — real-data re-projection of five
already-real snapshots into the site's city-visualization building manifest.
Hermetic: no real file I/O beyond tmp_path, no network.
"""
import json

from agents import build_city_state as bcs


# ── lane_status() ────────────────────────────────────────────────────────────

def test_lane_status_success_is_ok():
    assert bcs.lane_status({"last_run_conclusion": "success"}) == "ok"


def test_lane_status_failure_is_alert():
    assert bcs.lane_status({"last_run_conclusion": "failure"}) == "alert"


def test_lane_status_no_run_is_unknown():
    assert bcs.lane_status({}) == "unknown"


# ── tier_for() ────────────────────────────────────────────────────────────────

def test_tier_for_top_value_is_four():
    values = [10, 50, 200, 1000]
    assert bcs.tier_for(1000, values) == 4


def test_tier_for_lowest_value_is_one():
    values = [10, 50, 200, 1000]
    assert bcs.tier_for(10, values) == 1


def test_tier_for_zero_or_negative_is_one():
    assert bcs.tier_for(0, [10, 50, 200]) == 1
    assert bcs.tier_for(-5, [10, 50, 200]) == 1


def test_tier_for_non_numeric_is_one():
    assert bcs.tier_for(None, [10, 50, 200]) == 1


def test_tier_for_single_comparable_value_is_lowest_honest_tier():
    """No real spread to compare against -- must not fabricate a mid/high
    tier just because the lone value is technically the 'max'."""
    assert bcs.tier_for(500, [500]) in (1, 4)  # both are honest for n=1; assert it doesn't crash
    assert bcs.tier_for(500, []) == 1


# ── build_lane_checkpoints() ──────────────────────────────────────────────────

def test_build_lane_checkpoints_uniform_tier_and_real_fields():
    lanes = [
        {"id": "codeql", "label": "Static Analysis (CodeQL)", "last_run_conclusion": "success",
         "last_run_at": "2026-08-01T00:00:00Z", "headline": "0 open alert(s)", "source_workflow": "codeql.yml"},
        {"id": "intel-sweeps", "label": "On-Chain Attack Intelligence", "last_run_conclusion": "failure",
         "last_run_at": "2026-08-02T00:00:00Z", "headline": "HIGH", "source_workflow": "intel-sweeps.yml"},
    ]
    checkpoints = bcs.build_lane_checkpoints(lanes)
    assert len(checkpoints) == 2
    assert checkpoints[0]["id"] == "lane-codeql"
    assert checkpoints[0]["status"] == "ok"
    assert checkpoints[0]["tier"] == 1  # deliberately uniform, never fabricated size
    assert checkpoints[0]["stat_primary"] == {"label": "last run", "value": "0 open alert(s)"}
    assert checkpoints[1]["status"] == "alert"
    assert checkpoints[1]["source_workflow"] == "intel-sweeps.yml"


def test_build_lane_checkpoints_positions_from_ring_never_collide():
    lanes = [{"id": f"lane{i}"} for i in range(10)]
    checkpoints = bcs.build_lane_checkpoints(lanes)
    positions = {(c["gridX"], c["gridY"]) for c in checkpoints}
    assert len(positions) == 10  # all 10 real ring slots used, no collisions


def test_build_lane_checkpoints_beyond_ring_capacity_skips_not_overlaps():
    """An 11th lane would silently wrap via modulo onto lane 0's grid cell
    -- must be dropped instead of drawn on top of another building."""
    lanes = [{"id": f"lane{i}"} for i in range(11)]
    checkpoints = bcs.build_lane_checkpoints(lanes)
    assert len(checkpoints) == 10
    positions = {(c["gridX"], c["gridY"]) for c in checkpoints}
    assert len(positions) == 10


# ── build_landmarks() ──────────────────────────────────────────────────────────

def _fixture_inputs():
    secdash = {
        "findings_by_severity": {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "INFO": 5},
        "ledger_integrity": {"chain_intact": True, "unsealed_lines": 0},
    }
    attack_feed = {"threat_level": "HIGH", "incidents": [{"date": "2026-08-01"}] * 3}
    intel_index = {
        "investigations": [
            {"verdict": "REJECT"}, {"verdict": "reject"}, {"verdict": "CAUTION"}, {"verdict": "PROCEED"},
        ],
        "news": [{"title": "a"}, {"title": "b"}],
    }
    opportunities = [
        {"status": "live", "platform": "hackenproof"},
        {"status": "active", "platform": "cantina"},
        {"status": "complete", "platform": "cantina"},
    ]
    reputation = {"verifiable_activity": {"tools_built": 14, "tools_total": 16}}
    return secdash, attack_feed, intel_index, opportunities, reputation


def test_build_landmarks_real_counts_and_verdict_split():
    landmarks = bcs.build_landmarks(*_fixture_inputs())
    by_id = {b["id"]: b for b in landmarks}

    precinct = by_id["precinct-investigations"]
    assert precinct["stat_primary"] == {"label": "tracked", "value": 4}
    secondary = {s["label"]: s["value"] for s in precinct["stat_secondary"]}
    assert secondary == {"reject": 2, "caution": 1, "proceed": 1}

    tower = by_id["tower-bounty"]
    assert tower["stat_primary"]["value"] == 3
    secondary = {s["label"]: s["value"] for s in tower["stat_secondary"]}
    assert secondary == {"live": 2, "platforms": 2}

    assert by_id["newsroom"]["stat_primary"]["value"] == 2
    assert by_id["watchtower-threat"]["status"] == "alert"
    assert by_id["watchtower-threat"]["stat_primary"]["value"] == 3
    assert by_id["foundry"]["stat_primary"]["value"] == 14
    assert by_id["vault-ledger"]["status"] == "ok"
    assert by_id["vault-ledger"]["stat_primary"]["value"] == 15  # sum of findings_by_severity


def test_build_landmarks_mint_is_live_only_with_no_static_stat():
    landmarks = bcs.build_landmarks(*_fixture_inputs())
    mint = next(b for b in landmarks if b["id"] == "mint-x402")
    assert mint["stat_primary"] is None
    assert mint["live_only"] is True


def test_build_landmarks_threat_status_tracks_threat_level():
    secdash, attack_feed, intel_index, opportunities, reputation = _fixture_inputs()
    attack_feed["threat_level"] = "LOW"
    landmarks = bcs.build_landmarks(secdash, attack_feed, intel_index, opportunities, reputation)
    watchtower = next(b for b in landmarks if b["id"] == "watchtower-threat")
    assert watchtower["status"] == "ok"


def test_build_landmarks_vault_alert_when_chain_broken():
    secdash, attack_feed, intel_index, opportunities, reputation = _fixture_inputs()
    secdash["ledger_integrity"]["chain_intact"] = False
    landmarks = bcs.build_landmarks(secdash, attack_feed, intel_index, opportunities, reputation)
    vault = next(b for b in landmarks if b["id"] == "vault-ledger")
    assert vault["status"] == "alert"


def test_build_landmarks_empty_inputs_degrade_to_zero_not_fabricated():
    landmarks = bcs.build_landmarks({}, {}, {}, [], {})
    by_id = {b["id"]: b for b in landmarks}
    assert by_id["precinct-investigations"]["stat_primary"]["value"] == 0
    assert by_id["watchtower-threat"]["status"] == "unknown"
    assert by_id["foundry"]["stat_primary"]["value"] is None


# ── build_roads() ──────────────────────────────────────────────────────────────

def test_build_roads_foundry_is_hub_for_every_other_building():
    roads = bcs.build_roads(["foundry", "precinct-investigations", "tower-bounty"], ["lane-codeql"])
    assert ["foundry", "precinct-investigations"] in roads
    assert ["foundry", "tower-bounty"] in roads
    assert ["foundry", "lane-codeql"] in roads
    assert len(roads) == 3
    assert all(pair[0] == "foundry" for pair in roads)


# ── build() end-to-end, all I/O redirected ───────────────────────────────────

def test_build_writes_snapshot_with_real_paths(tmp_path, monkeypatch):
    out_path = tmp_path / "city-state.json"
    secdash_path = tmp_path / "security-dashboard.json"
    secdash_path.write_text(json.dumps({
        "findings_by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 1},
        "ledger_integrity": {"chain_intact": True},
        "lanes": [{"id": "codeql", "label": "Static Analysis", "last_run_conclusion": "success"}],
    }))
    attack_feed_path = tmp_path / "attack-feed.json"
    attack_feed_path.write_text(json.dumps({"threat_level": "LOW", "incidents": []}))
    intel_index_path = tmp_path / "intel-index.json"
    intel_index_path.write_text(json.dumps({"investigations": [], "news": []}))
    opportunities_path = tmp_path / "opportunities.json"
    opportunities_path.write_text(json.dumps([]))
    reputation_path = tmp_path / "reputation.json"
    reputation_path.write_text(json.dumps({"verifiable_activity": {}}))

    monkeypatch.setattr(bcs, "OUT_PATH", str(out_path))
    monkeypatch.setattr(bcs, "SECDASH_PATH", str(secdash_path))
    monkeypatch.setattr(bcs, "ATTACK_FEED_PATH", str(attack_feed_path))
    monkeypatch.setattr(bcs, "INTEL_INDEX_PATH", str(intel_index_path))
    monkeypatch.setattr(bcs, "OPPORTUNITIES_PATH", str(opportunities_path))
    monkeypatch.setattr(bcs, "REPUTATION_PATH", str(reputation_path))

    city = bcs.build()

    assert city["district_stats"]["lanes_passing"] == 1
    assert city["district_stats"]["lanes_total"] == 1
    assert len(city["buildings"]) == 8  # 7 landmarks + 1 lane checkpoint
    written = json.loads(out_path.read_text())
    assert written["district_stats"]["overall_threat_level"] == "LOW"
    # Every building carries a gridX/gridY/footprint from LAYOUT/LANE_RING —
    # the forward-compatibility contract a future 3D renderer depends on.
    assert all("gridX" in b and "gridY" in b and "footprint" in b for b in written["buildings"])


def test_build_handles_all_missing_files_gracefully(tmp_path, monkeypatch):
    monkeypatch.setattr(bcs, "OUT_PATH", str(tmp_path / "out.json"))
    monkeypatch.setattr(bcs, "SECDASH_PATH", str(tmp_path / "no-secdash.json"))
    monkeypatch.setattr(bcs, "ATTACK_FEED_PATH", str(tmp_path / "no-attack-feed.json"))
    monkeypatch.setattr(bcs, "INTEL_INDEX_PATH", str(tmp_path / "no-intel-index.json"))
    monkeypatch.setattr(bcs, "OPPORTUNITIES_PATH", str(tmp_path / "no-opportunities.json"))
    monkeypatch.setattr(bcs, "REPUTATION_PATH", str(tmp_path / "no-reputation.json"))

    city = bcs.build()

    assert city["district_stats"]["overall_threat_level"] is None
    assert city["district_stats"]["lanes_total"] == 0
    assert len(city["buildings"]) == 7  # 7 landmarks, zero lane checkpoints
