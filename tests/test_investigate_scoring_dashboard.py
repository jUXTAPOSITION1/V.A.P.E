"""Tests for agents/investigate.py::_compute_category_scores() and the
"Scoring Dashboard" report section — replaces the old flat "Executive
Summary" table (100 minus whichever of score()'s flags happened to
keyword-bucket into that name) with real per-category weights, a one-line
rationale each, and color-graded badges. Still presentation-layer
instrumentation, not a second scoring engine: score()'s own number/verdict
stays the one authoritative source of truth throughout.
"""
from agents import investigate as inv
from tests.conftest import clean_dex


def test_category_weights_sum_to_one():
    assert round(sum(w for _, w in inv._CATEGORY_WEIGHTS), 6) == 1.0


def test_compute_category_scores_covers_all_six_categories_with_no_input():
    cats = inv._compute_category_scores([], [])
    assert set(cats) == {name for name, _ in inv._CATEGORY_WEIGHTS}
    for name, cat in cats.items():
        assert 0 <= cat["score"] <= 100
        assert cat["rationale"]


def test_security_penalty_nets_against_its_own_category_only():
    cats = inv._compute_category_scores(["[-60] HONEYPOT detected"], [])
    assert cats["Contract Security & Controls"]["score"] == 40
    assert cats["Liquidity Health & Lock Quality"]["score"] == 100


def test_liquidity_and_holder_penalties_land_in_distinct_categories():
    cats = inv._compute_category_scores(
        ["[-25] Very low liquidity $1,000", "[-15] Top 10 holders control 80% of supply"], [])
    assert cats["Liquidity Health & Lock Quality"]["score"] == 75
    assert cats["Holder Distribution & Concentration"]["score"] == 85


def test_category_scores_clamped_at_zero_not_negative():
    cats = inv._compute_category_scores(["[-60] HONEYPOT detected", "[-60] Something else honeypot-y"], [])
    assert cats["Contract Security & Controls"]["score"] == 0


def test_global_cap_line_is_not_parsed_as_a_category_weight():
    """The "[capped at N] ..." line must never be treated as a per-category
    +/- delta (it isn't attributable to one category) — but it DOES now clamp
    every category's ceiling to N, so no category can display above a cap that
    already fired on the overall score/verdict. Real bug this pins (confirmed
    against a live report): before this clamp, an overall CAUTION capped down
    from 100 could still show Narrative/Transparency at a flat 100, exactly
    the "Critic Self-Audit sees no inconsistency, but Narrative and numerical
    score clearly diverge" complaint the report's own Expert Assessment
    flagged."""
    cats = inv._compute_category_scores(["[capped at 55] Only 0 positive legitimacy signal(s) found"], [])
    for name, cat in cats.items():
        if name == "Narrative Strength & Social Proof":
            continue  # baseline 20 is already below the 55 cap -- nothing to clamp
        assert cat["score"] == 55, f"{name} should be clamped to the cap, got {cat['score']}"
        assert "Capped at 55" in cat["rationale"]


def test_confidence_gap_cap_line_also_clamps_categories():
    """The confidence-gap cap (_apply_confidence_gap_cap()) uses the exact
    same "[capped at N] ..." convention as the legitimacy cap, so it must be
    clamped here identically with zero extra wiring."""
    reasons = ["[+10] Some positive signal",
               "[capped at 69] Unresolved gap at only 30% confidence: X — a real residual-risk ceiling"]
    cats = inv._compute_category_scores(reasons, [])
    for name, cat in cats.items():
        assert cat["score"] <= 69, f"{name} exceeded the confidence-gap cap: {cat['score']}"


def test_tightest_of_multiple_cap_lines_wins():
    reasons = ["[capped at 89] some gap", "[capped at 55] Only 0 positive legitimacy signal(s) found"]
    cats = inv._compute_category_scores(reasons, [])
    for name, cat in cats.items():
        if name == "Narrative Strength & Social Proof":
            continue
        assert cat["score"] == 55


def test_narrative_category_starts_low_with_no_social_signal_at_all():
    cats = inv._compute_category_scores([], [], dex={}, project_narrative=None)
    assert cats["Narrative Strength & Social Proof"]["score"] < 50


def test_narrative_category_rewards_real_declared_presence_and_verified_narrative():
    dex = clean_dex(websites=[{"url": "https://example.com"}],
                     socials=[{"type": "twitter", "url": "https://x.com/example"},
                              {"type": "telegram", "url": "https://t.me/example"}])
    narrative = {"text": "Real grounded narrative.", "address_identity_verified": True}
    cats = inv._compute_category_scores([], [], dex=dex, project_narrative=narrative)
    assert cats["Narrative Strength & Social Proof"]["score"] > 80


def test_narrative_category_partial_credit_when_identity_unverified():
    dex = clean_dex()
    narrative_verified = {"text": "Real narrative.", "address_identity_verified": True}
    narrative_unverified = {"text": "Real narrative.", "address_identity_verified": False}
    verified = inv._compute_category_scores([], [], dex=dex, project_narrative=narrative_verified)
    unverified = inv._compute_category_scores([], [], dex=dex, project_narrative=narrative_unverified)
    assert unverified["Narrative Strength & Social Proof"]["score"] < verified["Narrative Strength & Social Proof"]["score"]


def test_write_report_renders_scoring_dashboard_with_weighted_categories(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "INVEST_DIR", str(tmp_path))
    gp, onchain, verif = {}, {"is_contract": True}, {}
    dex = clean_dex(symbol="TOKEN")
    path, _sym, _emoji = inv.write_report(
        "0x" + "aa" * 20, "8453", gp, dex, onchain, verif, [], 40, "REJECT",
        ["[-60] HONEYPOT detected"], [],
    )
    content = open(path).read()
    assert "## Scoring Dashboard" in content
    assert "## Executive Summary" not in content
    assert "**Overall: 40/100 — REJECT**" in content
    assert "| Contract Security & Controls | 25% |" in content
    assert "img.shields.io/badge" in content  # color-graded per-category badge
    assert "authoritative verdict" in content
