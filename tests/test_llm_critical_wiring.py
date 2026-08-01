"""Pins which of VAPE's LLM call sites route through agents.llm.FRONTIER_ORDER
(Grok 4.1 Fast first) versus the default free chain — the operating split
requested: Grok primary for reports/investigations/the $50 x402 audit/intel/
Builder/SKILLFORGE; Groq/Gemini for everything else.

Source-scan based (reads the file text) rather than executing each module,
since several of these live inside real GitHub Actions workflows this
sandbox can't fully exercise (deepteam/deepeval aren't installed here) —
same pattern already used for offering-name parity in
tests/test_acp_defillama.py. A future refactor that drops the
provider_order kwarg from any of these calls will fail this test loudly.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Every file with a "critical" LLM call, and the exact snippet that must be
# present — proof the call site actually passes the frontier/Grok-first
# order, not just that the file imports it.
_CRITICAL_CALL_SITES = {
    "agents/redteam.py": "provider_order=FRONTIER_ORDER",
    "agents/self_improve.py": "provider_order=FRONTIER_ORDER",
    "agents/build_request.py": "provider_order=FRONTIER_ORDER",
    "agents/skillforge_build.py": "provider_order=FRONTIER_ORDER",
    "skillforge/synthesize.py": "provider_order=FRONTIER_ORDER",
    "skillforge/tools/ai-redteam/campaign_vape.py": "provider_order=FRONTIER_ORDER",
}


def test_every_named_critical_call_site_uses_frontier_order():
    missing = []
    for rel_path, needle in _CRITICAL_CALL_SITES.items():
        text = (ROOT / rel_path).read_text()
        if needle not in text:
            missing.append(rel_path)
    assert not missing, f"critical call site(s) missing provider_order=FRONTIER_ORDER: {missing}"


# The 5 sweeps below no longer call agents.llm.ask_oci_grok_safe() directly
# with their own provider_order=llm.FRONTIER_ORDER kwarg (2026-08-01) —
# they route through agents.research_engine.synthesize(), which hardcodes
# provider_order=FRONTIER_ORDER internally and unconditionally, not
# caller-overridable. Pin both halves of that indirection: each sweep
# actually calls synthesize(), and synthesize() itself still uses
# FRONTIER_ORDER — so a future refactor that drops FRONTIER_ORDER from
# research_engine.py fails this test for all 5 sweeps at once, same as
# before the migration.
_SWEEPS_ROUTED_THROUGH_RESEARCH_ENGINE = [
    "agents/base_sweep.py", "agents/security_sweep.py", "agents/virtuals_sweep.py",
    "agents/sentiment_sweep.py", "agents/macro_sweep.py",
]


def test_sweeps_route_through_research_engine_synthesize_with_frontier_order():
    missing = [p for p in _SWEEPS_ROUTED_THROUGH_RESEARCH_ENGINE
               if "research_engine.synthesize(" not in (ROOT / p).read_text()]
    assert not missing, f"sweep(s) no longer routed through research_engine.synthesize(): {missing}"
    engine_text = (ROOT / "agents/research_engine.py").read_text()
    assert "provider_order=FRONTIER_ORDER" in engine_text


def test_deep_dive_and_dossier_use_ask_frontier_with_no_local_override():
    """The $50 x402 job and investigations' AI quick review call
    ask_oci_grok_frontier() (OCI Grok 4.3 primary, same 'no local override'
    contract ask_frontier() had) — they must keep calling it BARE (no
    provider_order kwarg of their own), so they pick up FRONTIER_ORDER's
    Grok-first composition automatically rather than freezing to an old one."""
    dd = (ROOT / "agents/deep_dive_audit.py").read_text()
    assert "ask_oci_grok_frontier(FRONTIER_SYSTEM, prompt" in dd
    assert "ask_oci_grok_frontier(FRONTIER_SYSTEM, prompt, max_tokens=3000, temperature=0.3, provider_order" not in dd

    acp = (ROOT / "agents/acp_fulfill.py").read_text()
    assert "ask_oci_grok_frontier(_AI_QUICK_REVIEW_SYSTEM, user" in acp
    assert "provider_order" not in acp.split("ask_oci_grok_frontier(_AI_QUICK_REVIEW_SYSTEM")[1].split(")")[0]


def test_redteam_judge_matches_run_py_production_provider_order():
    """agents/redteam.py's whole purpose is testing agents/run.py's REAL
    production report pipeline — if run.py's actual call ever stops using
    FRONTIER_ORDER while redteam.py keeps using it (or vice versa), the test
    silently stops testing production. Pin both together."""
    run_py = (ROOT / "agents/run.py").read_text()
    redteam_py = (ROOT / "agents/redteam.py").read_text()
    assert "provider_order=_FRONTIER_ORDER" in run_py
    assert "provider_order=FRONTIER_ORDER" in redteam_py


def test_adversarial_simulator_and_judge_both_use_oci_grok_primary():
    """By explicit direction (2026-07-19), both the deepteam attack
    simulator and the judge use OCI Grok 4.3 first (use_oci_grok=True),
    falling back through FRONTIER_ORDER — a stronger simulator writes more
    sophisticated attacks, a more realistic adversary, not just a stronger
    judge. This intentionally supersedes the earlier weak-simulator/
    strong-judge asymmetry."""
    text = (ROOT / "skillforge/tools/ai-redteam/campaign_vape.py").read_text()
    sim_line = next(l for l in text.splitlines() if "sim = VapeLLM" in l)
    assert "provider_order=FRONTIER_ORDER" in sim_line
    assert "use_oci_grok=True" in sim_line
    judge_line = next(l for l in text.splitlines() if "judge = VapeLLM" in l)
    assert "provider_order=FRONTIER_ORDER" in judge_line
    assert "use_oci_grok=True" in judge_line
