"""
HACK Agent — VAPE's per-incident threat-analysis writer.

Every real incident in data/attack-feed.json's lookback window (the same
feed security_sweep.py already writes from DeFiLlama's real hacks data) gets
its own real, standalone markdown analysis — not just the single rule-based
"lesson" tag the Threat Ledger already shows. Grounded in the real fields
security_sweep.py already gathered (name/date/amount/technique/chains/
lesson) plus agents/research_engine.py's layered research pipeline: diverse
LLM-planned search queries (with a deterministic fallback so a query round
never comes up empty), rule-based source-credibility triage, robots-safe
deep extraction of the top sources, and a strict-grounding synthesis that
produces an explicit gaps/confidence assessment alongside the narrative.

This replaced an earlier version that ran exactly two hardcoded search
phrasings and handed the LLM whatever those two searches returned, with no
fallback strategy and no record of what was searched — a real, live
consequence is documented in intel/threat-analysis/2026-05-25-bitmor.md,
where both hardcoded queries returned nothing and the resulting report has
no root cause, no timeline, and generic advice ungrounded in anything
specific to that incident. See agents/research_engine.py's own docstring
for the full design.

Written by OCI-hosted Grok 4.3 first (agents/llm.py::ask_oci_grok() —
VAPE's newest, most capable currently-wired reasoning model), falling back
through FRONTIER_ORDER exactly like every other analyst call in this repo
(agents/intel_common.py::grok_analysis()) if OCI isn't configured or errors.
Never blocks: an unreachable LLM chain just means that incident is retried
next run, not a crash.

Idempotent via its own state file (skillforge/memory/threat_analysis_state.
json), same pattern as security_sweep.py's attack_response/attack_lesson
state files — each incident only gets a real analysis written once. Every
run re-patches each incident's `analysis_report` path back onto data/
attack-feed.json (which security_sweep.py's own schedule regenerates fresh
every cycle and has no knowledge of this field) so docs/assets/attackfeed.js
can render a real per-incident link, not just the feed-wide `source_report`
link that already exists.

Every incident gets a write-up — not just high-severity ones — by explicit
direction; a $0-loss incident just gets an honestly short one instead of
padding. MAX_ANALYSES_PER_RUN caps a single run's LLM spend/runtime; a large
backlog (e.g. a first-ever run against the full 8-week feed) catches up over
a few scheduled cycles rather than firing dozens of calls at once.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import intel_common as ic
from agents.security_sweep import ATTACK_FEED_PATH

STATE_PATH = os.path.join(ic.ROOT, "skillforge", "memory", "threat_analysis_state.json")
ANALYSIS_DIR = os.path.join(ic.ROOT, "intel", "threat-analysis")
MAX_ANALYSES_PER_RUN = 15


def _incident_id(h):
    return f"{h['date']}:{h['name']}"


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "incident"


def _load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _grounding(h):
    """Real, verified known-facts dict — the fields security_sweep.py
    already gathered for this incident, nothing invented — fed into
    research_engine.layered_research()/synthesize() as known_facts."""
    facts = {
        "protocol": h["name"],
        "date": h["date"],
        "loss_usd_m": h.get("amount_usd_m", 0),
        "chains": ", ".join(h.get("chains") or []) or "unknown",
        "technique": h.get("technique") or "unspecified",
    }
    lesson = h.get("lesson") or {}
    if lesson.get("label"):
        facts["technique_classification_vape"] = lesson["label"]
    if lesson.get("prevention"):
        facts["known_prevention_measure"] = lesson["prevention"]
    if lesson.get("backtest"):
        facts["vape_scoring_backtest"] = lesson["backtest"]
    return facts


_SECTION_INSTRUCTIONS = (
    "Structure your narrative using these exact Markdown headings, in this order: "
    "## Known Facts, ## Timeline, ## Root Cause, ## Impact, ## Response & Mitigation. "
    "Only fill in what the research actually supports — if a section genuinely has nothing "
    "to add, say so briefly under that heading rather than omitting it."
)


def _write_analysis(h):
    """Real threat-analysis narrative for one incident, via
    agents.research_engine's layered research pipeline. Returns
    (report_path, provider) or (None, None) if synthesis is unavailable
    this run — never raises, matching research_engine.synthesize()'s
    contract."""
    from agents import research_engine

    topic = f"{h['name']} hack exploit"
    known_facts = _grounding(h)
    result = research_engine.layered_research(topic, task_type="threat_analysis", known_facts=known_facts)
    synth = research_engine.synthesize(result, role="security analyst", extra_instructions=_SECTION_INSTRUCTIONS)
    text = (synth.get("narrative") or "").strip()
    if not text or text.startswith("_Synthesis unavailable"):
        return None, None

    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    path = os.path.join(ANALYSIS_DIR, f"{h['date']}-{_slug(h['name'])}.md")
    header = (
        f"# {h['name']} — Threat Analysis\n\n"
        f"**Date:** {h['date']}  \n"
        f"**Loss:** ${h.get('amount_usd_m', 0)}M  \n"
        f"**Chains:** {', '.join(h.get('chains') or []) or 'unknown'}  \n"
        f"**Analysis by:** VAPE  \n"
        f"**Generated:** {ic.now_iso()}\n\n---\n\n"
    )
    gaps_section = research_engine.render_gaps_section(synth.get("gaps") or [])
    methodology = research_engine.render_methodology_log(result)
    body = f"{text}\n\n{gaps_section}\n{methodology}"
    with open(path, "w") as f:
        f.write(header + body)

    review = research_engine.review_output(header + body, task_type="threat_analysis")
    if not review["ok"]:
        research_engine.log_review_finding(topic, "threat_analysis", review["issues"])

    return os.path.relpath(path, ic.ROOT).replace(os.sep, "/"), synth.get("provider")


def run():
    try:
        with open(ATTACK_FEED_PATH) as f:
            feed = json.load(f)
    except Exception as e:
        print(f"[hack_agent] no attack feed yet ({e}) — nothing to analyze this run")
        return {"analyzed": 0, "patched": 0}

    incidents = feed.get("incidents") or []
    state = _load_state()
    analyzed = 0
    patched = 0

    for h in incidents:
        incident_id = _incident_id(h)
        entry = state.get(incident_id)
        if entry and entry.get("report") and os.path.exists(os.path.join(ic.ROOT, entry["report"])):
            h["analysis_report"] = entry["report"]
            patched += 1
            continue
        if analyzed >= MAX_ANALYSES_PER_RUN:
            continue  # a large backlog catches up over subsequent scheduled runs
        report, provider = _write_analysis(h)
        if not report:
            continue
        state[incident_id] = {"report": report, "provider": provider, "written_at": ic.now_iso()}
        h["analysis_report"] = report
        analyzed += 1

    _save_state(state)
    with open(ATTACK_FEED_PATH, "w") as f:
        json.dump(feed, f, indent=2)
    print(f"[hack_agent] {analyzed} new analysis(es) written, {patched} existing patched back onto the feed")
    return {"analyzed": analyzed, "patched": patched}


if __name__ == "__main__":
    run()
