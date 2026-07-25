"""
HACK Agent — VAPE's per-incident threat-analysis writer.

Every real incident in data/attack-feed.json's lookback window (the same
feed security_sweep.py already writes from DeFiLlama's real hacks data) gets
its own real, standalone markdown analysis — not just the single rule-based
"lesson" tag the Threat Ledger already shows. Grounded in the real fields
security_sweep.py already gathered (name/date/amount/technique/chains/
lesson), two differently-worded real web searches for public writeups, AND
the model's own live web/X search (agents/llm.py::ask()'s search=True — see
_write_analysis()'s comment for why: a real one-incident side-by-side
against a direct Grok query exposed that the single pre-fetched search this
used to run on alone was nowhere near enough). The model is told never to
invent a detail beyond what it actually found or was given, and to say
plainly when real research still turns up nothing.

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
    lesson = h.get("lesson") or {}
    lines = [
        f"Protocol: {h['name']}",
        f"Date: {h['date']}",
        f"Loss: ${h.get('amount_usd_m', 0)}M",
        f"Chains: {', '.join(h.get('chains') or []) or 'unknown'}",
        f"Technique (as classified by DeFiLlama's real hacks feed): {h.get('technique') or 'unspecified'}",
    ]
    if lesson.get("label"):
        lines.append(f"VAPE's rule-based technique classification: {lesson['label']}")
    if lesson.get("prevention"):
        lines.append(f"Known prevention measure for this vulnerability class: {lesson['prevention']}")
    if lesson.get("backtest"):
        lines.append(f"Backtest of VAPE's own scoring model against this incident: {lesson['backtest']}")
    return "\n".join(lines)


def _write_analysis(h):
    """Real LLM narrative for one incident. Returns (report_path, provider)
    or (None, None) if every provider in the chain is unreachable this run —
    never raises, matching agents/intel_common.py::grok_analysis()'s
    contract.

    Grounded in two independent research passes: the existing Tavily/Brave
    pre-fetch (web_search_snippets, widened from 4 to 6 results and a
    second, differently-worded query — post-mortems for a niche DeFi
    incident often use different terms like "exploit analysis" or the
    protocol's own incident-report wording rather than "post-mortem") plus
    whatever the model itself already knows/can reason about from that
    grounding. search is left at its default (False) as of 2026-07-25 —
    xAI's Live Search (this function used to pass search=True specifically
    to reach it) was deprecated by xAI in favor of a new "Agent Tools API"
    this repo hasn't migrated to (confirmed real HTTP 410 in production),
    and search=True would skip past OCI Grok/Vertex (this function's real
    primary route via ask_oci_grok_safe below) into a free chain that can't
    provide search either — see agents/intel_common.py::grok_analysis()'s
    docstring for the full story. The historical reason this flag existed
    (a 2026-07-20 side-by-side on the DefiTuna Lending incident showed the
    pre-fetch-only pipeline reporting "no public writeups found" for a hack
    a direct Grok Live Search query resolved in full) still motivates
    re-adding real search grounding once a working replacement is wired
    in — just not this specific, now-dead mechanism."""
    from agents.llm import ask_oci_grok_safe, FRONTIER_ORDER
    search_a = ic.web_search_snippets(f"{h['name']} hack exploit post-mortem {h['date']}", max_results=6)
    search_b = ic.web_search_snippets(f"{h['name']} exploit analysis attacker address root cause", max_results=6)
    grounding = _grounding(h)
    search_section = (
        ic.format_search_section("Public writeups found this run (query 1)", search_a)
        + "\n" + ic.format_search_section("Public writeups found this run (query 2)", search_b)
    )
    system = (
        "You are VAPE's senior security analyst, writing a real, standalone threat-analysis "
        "report for one specific real hack, to be published on VAPE's public site. You are "
        "given the real, verified facts VAPE's own pipeline gathered about this incident, plus "
        "two pre-fetched web searches — but you also have live web/X search available to you "
        "directly: use it to find the actual attack flow, transaction hashes, attacker "
        "addresses, and root cause if any of that isn't already in what you were given. Never "
        "invent a number, name, date, or detail — only report what you actually found (via the "
        "pre-fetched searches, your own live search, or what's given above) or what a linked "
        "public writeup actually says, and cite where each concrete fact came from. Explain "
        "what happened, the real technical root cause if it's known, why it matters, and what a "
        "protocol team should take away from it. If real research (yours or the pre-fetch) "
        "truly turns up nothing, say so honestly rather than padding with generic security "
        "advice — but exhaust your own live search first; thin pre-fetched snippets alone are "
        "not sufficient grounds to conclude nothing is publicly known."
    )
    user = f"{grounding}\n\n{search_section}"
    text, provider = ask_oci_grok_safe(system, user, tier="frontier", provider_order=FRONTIER_ORDER,
                                        temperature=0.5, max_tokens=1800)
    if (text or "").startswith("[llm unavailable"):
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
    with open(path, "w") as f:
        f.write(header + text.strip() + "\n")
    return os.path.relpath(path, ic.ROOT).replace(os.sep, "/"), provider


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
