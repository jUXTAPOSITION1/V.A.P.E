"""Tests for agents/scout.py's bounty-vs-incident classification fix (Task
#196): historical DeFiLlama hack incidents used to share one incident-
oriented fitScore with real live bounty programs, so huge historical dollar
amounts (and even post-incident "recovery bounty" negotiation offers)
drowned out real, gettable smart-contract review programs on the site's
Bounty Command Center. These tests cover the pure classification/scoring
functions and the non-destructive migration/liveness-recheck logic — no
real network calls (liveness recheck is mocked).
"""
from unittest import mock

from agents import scout


def test_classify_track_defillama_is_incident():
    assert scout._classify_track({"platform": "defillama-hack"}) == "incident"


def test_classify_track_everything_else_is_bounty():
    assert scout._classify_track({"platform": "hackenproof"}) == "bounty"
    assert scout._classify_track({"platform": "immunefi"}) == "bounty"


def test_vape_fit_solidity_program_is_fit():
    fit, reason = scout._vape_fit({"name": "SmarDex Smart Contracts", "tags": ["contract", "solidity", "ethereum"]})
    assert fit is True
    assert "deep_dive_audit" in reason


def test_vape_fit_move_program_is_fit():
    fit, reason = scout._vape_fit({"name": "Sui Protocol", "tags": ["git_repo", "move", "rust"]})
    assert fit is True
    assert "external_audit" in reason


def test_vape_fit_web_mobile_only_is_not_fit():
    fit, reason = scout._vape_fit({"name": "Phemex Web and Mobile", "tags": ["web", "mobile", "android", "ios"]})
    assert fit is False
    assert "no smart-contract" in reason


def test_vape_fit_recovery_bounty_is_disqualified_even_with_contract_tag():
    # The exact real-world case that motivated this fix: a huge post-incident
    # "bounty" that isn't a code-review engagement at all.
    fit, reason = scout._vape_fit({
        "name": "Bitmart Post-Incident Forensics Bounty Hunt",
        "tags": ["bugbounty", "contract", "solidity"],
    })
    assert fit is False
    assert "recovery" in reason


def test_bounty_fit_score_zero_when_not_vape_fit_regardless_of_prize():
    score = scout._bounty_fit_score(58_000_000, ["bugbounty"], vape_fit=False)
    assert score == 0


def test_bounty_fit_score_positive_when_fit():
    score = scout._bounty_fit_score(500_000, ["contract", "solidity", "base"], vape_fit=True)
    assert score > 0


def test_bounty_fit_score_does_not_scale_unboundedly_with_prize():
    # A $58M recovery bounty (if it somehow were fit) shouldn't massively
    # outscore a $250k real program the way the incident formula would.
    small = scout._bounty_fit_score(250_000, ["contract", "solidity", "ethereum"], vape_fit=True)
    huge = scout._bounty_fit_score(58_000_000, ["contract", "solidity", "ethereum"], vape_fit=True)
    assert huge - small < 20


def test_bounty_fit_score_penalizes_repeated_liveness_failures():
    fresh = scout._bounty_fit_score(500_000, ["contract", "solidity"], True, {"ok": True, "consecutiveFailures": 0})
    stale = scout._bounty_fit_score(500_000, ["contract", "solidity"], True, {"ok": False, "consecutiveFailures": 3})
    assert stale < fresh


def test_migrate_entry_backfills_incident_track():
    opp = {"platform": "defillama-hack", "name": "X", "prizeUsd": 1000}
    changed = scout._migrate_entry(opp)
    assert changed is True
    assert opp["track"] == "incident"
    assert "vapeFit" not in opp  # only bounty-track entries get vapeFit


def test_migrate_entry_backfills_bounty_track_fields():
    opp = {"platform": "hackenproof", "name": "SmarDex Smart Contracts",
           "tags": ["contract", "solidity"], "prizeUsd": 500_000}
    changed = scout._migrate_entry(opp)
    assert changed is True
    assert opp["track"] == "bounty"
    assert opp["vapeFit"] is True
    assert opp["bountyFitScore"] > 0


def test_migrate_entry_is_idempotent_and_never_overwrites_existing_fields():
    opp = {"platform": "hackenproof", "name": "X", "tags": ["solidity"], "prizeUsd": 1,
           "track": "bounty", "vapeFit": False, "vapeFitReason": "manually curated", "bountyFitScore": 42}
    changed = scout._migrate_entry(opp)
    assert changed is False
    assert opp["vapeFit"] is False  # untouched even though tags would otherwise say True
    assert opp["vapeFitReason"] == "manually curated"
    assert opp["bountyFitScore"] == 42


def test_recheck_liveness_marks_ok_on_200():
    opp = {"track": "bounty", "url": "https://example.com/program", "vapeFit": True,
           "tags": ["solidity"], "prizeUsd": 1000}
    resp = mock.MagicMock()
    resp.status = 200
    resp.__enter__ = mock.Mock(return_value=resp)
    resp.__exit__ = mock.Mock(return_value=False)
    with mock.patch("urllib.request.urlopen", return_value=resp):
        checked = scout._recheck_liveness([opp])
    assert checked == 1
    assert opp["liveCheck"]["ok"] is True
    assert opp["liveCheck"]["consecutiveFailures"] == 0


def test_recheck_liveness_counts_consecutive_failures_without_killing_on_first():
    opp = {"track": "bounty", "url": "https://example.com/gone", "vapeFit": True,
           "tags": ["solidity"], "prizeUsd": 1000, "liveCheck": {"consecutiveFailures": 1}}
    with mock.patch("urllib.request.urlopen", side_effect=Exception("timeout")):
        scout._recheck_liveness([opp])
    assert opp["liveCheck"]["ok"] is False
    assert opp["liveCheck"]["consecutiveFailures"] == 2


def test_recheck_liveness_respects_cap():
    opps = [{"track": "bounty", "url": f"https://example.com/{i}", "vapeFit": True,
             "tags": ["solidity"], "prizeUsd": 1000} for i in range(5)]
    with mock.patch("urllib.request.urlopen", side_effect=Exception("down")):
        checked = scout._recheck_liveness(opps, cap=2)
    assert checked == 2


def test_recheck_liveness_skips_recently_checked_entries():
    import time
    opp = {"track": "bounty", "url": "https://example.com/fresh", "vapeFit": True,
           "tags": ["solidity"], "prizeUsd": 1000,
           "liveCheck": {"checkedAt": time.time(), "ok": True, "consecutiveFailures": 0}}
    with mock.patch("urllib.request.urlopen") as m:
        checked = scout._recheck_liveness([opp])
    assert checked == 0
    m.assert_not_called()


def test_write_digest_separates_bounty_and_incident_tracks(tmp_path, monkeypatch):
    monkeypatch.setattr(scout, "INTEL_DIR", str(tmp_path))
    with mock.patch.object(scout, "_strategic_briefing", return_value=""):
        entries = [
            {"track": "incident", "platform": "defillama-hack", "name": "BigHack (exploit $50,000,000)",
             "prizeUsd": 50_000_000, "fitScore": 90, "url": "https://defillama.com/hacks", "status": "incident"},
            {"track": "bounty", "platform": "hackenproof", "name": "SmarDex Smart Contracts",
             "prizeUsd": 500_000, "vapeFit": True, "vapeFitReason": "Solidity/EVM — matches agents/deep_dive_audit.py",
             "bountyFitScore": 75, "url": "https://hackenproof.com/programs/smardex", "status": "live"},
        ]
        path = scout._write_digest(entries, 0, 2, [])
    text = open(path).read()
    assert "Bounty Ops (VAPE-fit, live)" in text
    assert "Historical Incident Leads" in text
    assert "SmarDex Smart Contracts" in text
    assert "BigHack" in text
    # The bounty table appears before the incident table (VAPE's actual capability first)
    assert text.index("Bounty Ops") < text.index("Historical Incident Leads")
