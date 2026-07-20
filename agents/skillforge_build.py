"""
VAPE SKILLFORGE Build — the self-directed half of "VAPE can build things."

agents/builder.py can already generate real multi-file tools/apps
(generate_project()), and agents/build_request.py wires that to a human
filing a labeled GitHub issue. This module is the other half: VAPE deciding
FOR ITSELF what's worth building, grounded in its own accumulated real
signal — tool-registry gaps (broken/needs_key), recent real investigation
findings, AI-redteam findings, and self-improvement lessons already sitting
in Memory — instead of only ever reacting to a human's ask.

Two real LLM calls per cycle (agents/llm.py's multi-provider layer, same one
agents/builder.py and agents/run.py already use):
  1. PROPOSE — given the real signals gathered below, name exactly one
     concrete, buildable tool/skill idea scoped to VAPE's specialization
     areas, justified by a specific signal (never invented). May propose
     nothing if nothing in the real data justifies a new build this cycle.
  2. BUILD — agents/builder.py's generate_project() implements it.

Same safety boundary as build_request.py: generated files land in an
isolated build-requests/skillforge-<slug>-<date>/ directory via a PR, never
applied directly to production files — a human decides whether/how/where to
integrate it. Builder's own security validation is the first gate; PR
review is the second.

Runs 2x/day (see .github/workflows/skillforge-build.yml) — slower than the
hourly/daily reactive pipelines since this is VAPE inventing its own work
rather than fixing a known bug, and most cycles are a no-op report rather
than a PR (see gather_signals()/propose() below) so this cadence just means
checking more often, not forcing two PRs a day.

CLI:
  python -m agents.skillforge_build
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.builder import Builder, validate_security  # noqa: E402
from agents._build_pr import open_build_pr  # noqa: E402

try:
    from agents.llm import ask_oci_grok_safe as llm_ask, available as llm_available, FRONTIER_ORDER
except Exception:
    llm_ask = None
    llm_available = lambda: []  # noqa: E731
    FRONTIER_ORDER = None

try:
    from skillforge.memory.retriever import search_memory, append_to_memory
except Exception:
    search_memory = None
    append_to_memory = None

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(_REPO_ROOT, "reports")
REGISTRY_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "tools-registry.json")


def _now_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _tool_gaps():
    """Real broken/needs_key entries from the tool registry — the same
    signal agents/run.py surfaces in bounty-cycle reports, gathered here
    independently since this module has no other dependency on run.py."""
    try:
        with open(REGISTRY_PATH) as f:
            reg = json.load(f)
    except Exception:
        return []
    gaps = []
    for tier, tools in reg.get("tiers", {}).items():
        for t in tools:
            status = t.get("status")
            name = t.get("name", "?")
            if status == "broken":
                gaps.append(f"{name} ({tier}) is BROKEN: {t.get('purpose', '')}")
            elif status == "needs_key":
                gaps.append(f"{name} ({tier}) blocked on missing {t.get('requires_key', '?')}: {t.get('purpose', '')}")
    return gaps


def _bounty_radar_signal(max_items=8):
    """Real top-fit opportunities from SCOUT's bounty-radar archive
    (agents/scout.py, intel/bounty-radar/opportunities.json) — grounds tool
    proposals in actual $ opportunities VAPE could pursue right now, not
    only its own registry gaps. Returns [] if the archive is missing/empty;
    never fabricates an opportunity."""
    path = os.path.join(_REPO_ROOT, "intel", "bounty-radar", "opportunities.json")
    try:
        with open(path) as f:
            opps = json.load(f)
    except Exception:
        return []
    if not isinstance(opps, list):
        return []
    ranked = sorted(opps, key=lambda o: o.get("fitScore", 0), reverse=True)[:max_items]
    return [f"{o.get('name', '?')} ({o.get('platform', '?')}, fit {o.get('fitScore', 0)}, "
            f"${o.get('prizeUsd', 0):,.0f}): {o.get('desc', '')}" for o in ranked]


def _memory_signal(query, category, max_results=6, min_confidence=0.6):
    if not search_memory:
        return []
    try:
        return search_memory(query=query, category=category, max_results=max_results, min_confidence=min_confidence)
    except Exception:
        return []


def gather_signals():
    """Assemble everything real this cycle's proposal can be grounded in.
    Returns "" when there's genuinely nothing to ground a proposal in —
    callers must treat that as "skip this cycle," never fabricate signal."""
    parts = []

    gaps = _tool_gaps()
    if gaps:
        parts.append("=== TOOL REGISTRY GAPS (real, skillforge/memory/tools-registry.json) ===\n"
                      + "\n".join(f"- {g}" for g in gaps))

    bounty = _bounty_radar_signal()
    if bounty:
        parts.append("=== TOP BOUNTY-RADAR OPPORTUNITIES (real, agents/scout.py, "
                      "intel/bounty-radar/opportunities.json) ===\n"
                      + "\n".join(f"- {b}" for b in bounty))

    findings = _memory_signal("investigation reject caution rug honeypot", "finding")
    if findings:
        parts.append("=== RECENT INVESTIGATION FINDINGS (real, agents/investigate.py) ===\n"
                      + "\n".join(f"- {f.get('title', '')}: {(f.get('content') or '')[:200]}" for f in findings))

    redteam = _memory_signal("prompt injection redteam jailbreak", "finding")
    if redteam:
        parts.append("=== RECENT AI-REDTEAM FINDINGS (real, agents/redteam.py + skillforge/tools/ai-redteam) ===\n"
                      + "\n".join(f"- {f.get('title', '')}: {(f.get('content') or '')[:200]}" for f in redteam))

    lessons = _memory_signal("lesson pattern accuracy drift", "lesson")
    if lessons:
        parts.append("=== RECENT LESSONS (real, agents/self_improve.py + agents/review_ledger.py) ===\n"
                      + "\n".join(f"- {l.get('title', '')}: {(l.get('content') or '')[:200]}" for l in lessons))

    # Previously every signal here was purely internal (registry/memory) —
    # one bounded web search gives the proposal step real outside awareness
    # of what's newly available to build on or adopt, rather than only ever
    # reasoning over VAPE's own prior findings.
    try:
        from agents import intel_common as ic
        research = ic.web_search_snippets(
            "new open-source smart contract security tool OR on-chain forensics technique 2026",
            max_results=6,
        )
        if research.get("results"):
            parts.append("=== WEB RESEARCH — new tools/techniques (" + str(research.get("provider")) + ") ===\n"
                          + "\n".join(f"- {r['title']}: {r['snippet']}" for r in research["results"]))
    except Exception as e:
        print(f"[SkillforgeBuild] web research signal skipped: {e}")

    return "\n\n".join(parts)


PROPOSE_SYSTEM = """You are VAPE's SKILLFORGE proposal engine — deciding what VAPE should build
next FOR ITSELF, grounded ONLY in the real signals given to you below.

VAPE's specialization areas (stay strictly inside these): Base/EVM on-chain investigation
and forensics, smart-contract security (bug bounty hunting, static/dynamic analysis),
autonomous agent tooling, and AI-agent security (prompt injection, red-teaming). This
repo's real stack: Python stdlib-first for agents/, Hono/TypeScript for worker/, vanilla
no-bundler JS for docs/assets/ — match whichever area the proposal targets.

Rules:
- Propose EXACTLY ONE concrete, buildable tool/skill/mini-app — not a vague idea.
- It MUST be justified by a SPECIFIC signal in the data below — quote or closely
  reference it. If nothing below genuinely justifies a new build, say so.
- A TOP BOUNTY-RADAR OPPORTUNITY is a high-priority justification category: if a real,
  high-fit opportunity below would need a capability VAPE doesn't have yet (a specific
  chain's tracing, a technique-specific detector, a program's required audit format),
  proposing exactly that capability is the strongest kind of build — it's tied to real
  dollars, not just self-maintenance. Prefer it over a generic gap when both are present.
- Scope it to something implementable in one pass: a script, a CLI tool, a detector, a
  small analysis module, a playbook-backed utility — not a multi-week project.
- Never invent capability gaps, findings, patterns, or opportunities that aren't in the
  data given.
- You have live web/X search available directly — use it if a signal below names a specific
  tool/technique/program you'd want to verify is current before proposing a build around it.
  The pre-fetched web research included below is supplementary, not a substitute.
- No disclaimers, no hedging — a real decision or an honest "nothing justified."

Output format (exactly, first line always one of these two):
BUILD: <one-line title>
JUSTIFICATION: <which real signal above motivates this, quoted/referenced — go into as much
  depth as the signal supports; this is your real research/analysis of why it matters, not
  a one-liner>
SPEC: <what it does, inputs/outputs, how it fits VAPE's real stack, and how you'd approach
  building it — as much detail as genuinely helps the build step that reads this next, not
  capped at a fixed sentence count>

or, if nothing is justified:
BUILD: NONE
"""


def propose(signals):
    if not llm_ask or not llm_available():
        return None
    try:
        response, _ = llm_ask(
            system=PROPOSE_SYSTEM,
            user=f"=== REAL SIGNALS THIS CYCLE ===\n{signals}\n\n=== YOUR TASK ===\nPropose exactly one build, or BUILD: NONE.",
            tier="frontier",
            max_tokens=1600,
            temperature=0.5,
            provider_order=FRONTIER_ORDER,
            search=True,
        )
    except Exception as e:
        print(f"[SkillforgeBuild] propose LLM call failed: {e}")
        return None

    first_line = (response or "").strip().splitlines()[0] if response else ""
    if not first_line.upper().startswith("BUILD:"):
        print("[SkillforgeBuild] proposal didn't start with BUILD: — treating as no proposal")
        return None
    title = first_line.split(":", 1)[1].strip()
    if title.upper() == "NONE":
        return None

    justification = ""
    spec = ""
    m = re.search(r"JUSTIFICATION:\s*(.+?)(?:\nSPEC:|\Z)", response, re.DOTALL)
    if m:
        justification = m.group(1).strip()
    m = re.search(r"SPEC:\s*(.+)", response, re.DOTALL)
    if m:
        spec = m.group(1).strip()
    if not spec:
        print("[SkillforgeBuild] proposal missing SPEC — treating as incomplete, skipping")
        return None
    return {"title": title, "justification": justification, "spec": spec}


def build_and_open_pr(proposal):
    builder = Builder()
    if not builder.llm_ready:
        print("[SkillforgeBuild] no LLM provider available for build step — skipping")
        return None, {}

    task = (
        f"{proposal['title']}\n\n{proposal['spec']}\n\n"
        f"Why this is worth building now: {proposal['justification']}\n\n"
        "This is VAPE's own self-directed build (not a human request) — build exactly "
        "what's specified above, scoped to VAPE's real stack and specialization areas."
    )
    files, metadata = builder.generate_project(task=task, review=True, tier="deep",
                                                provider_order=FRONTIER_ORDER)
    if not files:
        return None, {}

    combined = "\n\n".join(files.values())
    _, warnings = validate_security(combined, task)

    slug = re.sub(r"[^a-z0-9]+", "-", proposal["title"].lower()).strip("-")[:40]
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    branch = f"vape-skillforge-{slug}-{_now_stamp()}"
    out_dir_rel = os.path.join("build-requests", f"skillforge-{slug}-{date}")

    readme = (
        f"# VAPE self-directed build — {proposal['title']}\n\n"
        f"**Justification:** {proposal['justification']}\n\n"
        f"**Spec:** {proposal['spec']}\n\n"
        f"**Security review:** {'clean' if not warnings else '; '.join(warnings)}\n\n"
        "This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation "
        "signals (see the PR description) — not applied automatically. A human reviews "
        "this PR and decides whether/how/where to integrate it.\n\n"
        "## Files\n" + "\n".join(f"- `{p}`" for p in files)
    )
    body = (
        f"**VAPE proposed this build itself** — grounded in real signals, not a human request.\n\n"
        f"**Justification:** {proposal['justification']}\n\n"
        f"**Spec:** {proposal['spec']}\n\n"
        f"**Security review:** {'clean' if not warnings else ', '.join(warnings)}\n\n"
        f"Files land under `{out_dir_rel}/` for review — nothing was applied to the "
        f"existing codebase automatically.\n\n## Files\n" + "\n".join(f"- `{p}`" for p in files)
    )
    pr_url = open_build_pr(branch, out_dir_rel, f"VAPE self-build: {proposal['title']}", body, readme, files)
    return pr_url, files


def _log_lesson(proposal, files, pr_url):
    if append_to_memory is None or proposal is None:
        return
    outcome = "opened a real PR" if pr_url else ("generated files but PR creation failed/skipped" if files else "generated nothing this cycle")
    try:
        append_to_memory(
            category="lesson",
            title=f"skillforge_build: {proposal['title'][:80]} — {outcome}",
            content=f"Justification: {proposal['justification']}\nFiles: {list(files.keys())}\nOutcome: {outcome}"
                    + (f"\nPR: {pr_url}" if pr_url else ""),
            source="agents/skillforge_build.py",
            tags=["skillforge-build", "builder", "self-directed"],
            confidence=0.7,
            metadata={"title": proposal["title"], "pr_url": pr_url, "files": list(files.keys())},
        )
    except Exception as e:
        print(f"[SkillforgeBuild] could not log lesson: {e}")


def _log_build_entry(proposal, files, pr_url):
    """Appends a real build_log entry (skillforge/memory/BUILD_LEDGER.md —
    the site's "Development Ledger") whenever this cycle actually generated
    real files and opened a real PR. Same gap as self_improve.py had: this
    pipeline runs real cycles and opens real PRs, but without this call the
    ledger never heard about any of it. Skipped on a no-signal/no-proposal/
    no-files cycle — a build_log entry documents a real pattern, not an
    empty cycle."""
    if not (files and pr_url):
        return
    try:
        from agents.build_ledger import log_build
        log_build(
            title=f"skillforge_build: {proposal['title'][:80]}",
            content=f"Justification: {proposal['justification']}\n\n"
                    f"Self-directed build, grounded in real tool-registry/Memory signals "
                    f"(not a human request) — built via agents.builder.Builder's "
                    f"generate_project(), security-validated, opened for review.\n"
                    f"PR: {pr_url}",
            source="agents/skillforge_build.py",
            tags=["skillforge-build", "builder", "self-directed", "auto"],
            confidence=0.7,
            files=list(files.keys()),
        )
    except Exception as e:
        print(f"[SkillforgeBuild] could not log build_log entry: {e}")


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_path = os.path.join(REPORTS_DIR, f"skillforge_build_{_now_stamp()}.md")

    signals = gather_signals()
    if not signals:
        with open(report_path, "w") as f:
            f.write("# VAPE SKILLFORGE Build — no signal this cycle\n\n"
                     "No tool-registry gaps, investigation findings, redteam findings, or "
                     "lessons available to ground a proposal in — skipping rather than "
                     "fabricating a build.\n")
        print("[SkillforgeBuild] no real signal this cycle — skipping.")
        return

    proposal = propose(signals)
    if not proposal:
        with open(report_path, "w") as f:
            f.write("# VAPE SKILLFORGE Build — no proposal this cycle\n\n"
                     "Real signal was available, but the proposal engine did not find "
                     "anything genuinely worth building from it this cycle.\n\n"
                     f"## Signals reviewed\n```\n{signals[:3000]}\n```\n")
        print("[SkillforgeBuild] no proposal this cycle.")
        return

    print(f"[SkillforgeBuild] proposing: {proposal['title']}")
    pr_url, files = build_and_open_pr(proposal)
    _log_lesson(proposal, files, pr_url)
    _log_build_entry(proposal, files, pr_url)

    report = (
        f"# VAPE SKILLFORGE Build — {proposal['title']}\n\n"
        f"**Justification:** {proposal['justification']}\n\n"
        f"**Spec:** {proposal['spec']}\n\n"
        "## Files generated\n"
        + ("\n".join(f"- `{p}`" for p in files) if files else "None — Builder produced no usable FILE blocks this cycle.")
        + "\n\n"
        + (f"PR opened: {pr_url}\n" if pr_url else "No PR opened (see log for why).\n")
    )
    with open(report_path, "w") as f:
        f.write(report)
    print(f"[SkillforgeBuild] cycle complete. Report: {os.path.relpath(report_path, _REPO_ROOT)}")


if __name__ == "__main__":
    main()
