"""
VAPE Reporter — writes VAPE's own investigative news reports from the
headlines agents/news_scan.py already discovered (data/news-feed.json).

Same design rule as every other sweep in this repo (see
agents/intel_common.py's docstring): real, already-fetched data first, one
bounded web search per story for corroboration, then the LLM's job is
narrative synthesis only — it is told explicitly never to invent a fact,
source, or quote beyond what it was given or finds itself. Routed through
agents/intel_common.py::grok_analysis(), VAPE's strongest available model
(OCI-hosted Grok 4.3, falling back to the Vertex-tuned candidate, then the
free frontier chain) — the same "top research agent" route every other
report on this site uses, not a separate/cheaper model.

Two model calls per story, mirroring how a real newsroom splits reporting
from editing: write_story() drafts under a reporter byline, then
_editorial_pass() reviews that draft against the same sourced material with
a second, independent call before it ships — catching unsupported claims
the drafting prompt's own instructions missed, not just restating them.

Picks NEWS_REPORTER_PICKS stories per run (env, default 1) — run cadence
(the calling workflow) controls daily volume, not this script.

Usage: python agents/news_reporter.py
"""
import os
import re
import sys
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents import news_common as nc  # noqa: E402
from agents import intel_common as ic  # noqa: E402

FALLBACK_IMAGE = "assets/logo-v-256.png"  # VAPE's own brand mark -- used only when no real source image is found; never a fabricated stock photo


def _load_ticker():
    try:
        with open(nc.FEED_PATH) as f:
            return json.load(f).get("headlines", [])
    except Exception:
        return []


def _pick_candidates(state, n):
    """First N not-yet-reported headlines off the ticker (already sorted
    newest-first by news_scan.py), preferring topic diversity when there's
    a real choice available."""
    unreported = [h for h in _load_ticker() if not nc.is_reported(state, h["url"])]
    picked, used_topics = [], set()
    for h in unreported:
        if len(picked) >= n:
            break
        if h.get("topic") in used_topics and len(picked) < len(unreported):
            continue
        picked.append(h)
        used_topics.add(h.get("topic"))
    if len(picked) < n:
        for h in unreported:
            if h not in picked and len(picked) < n:
                picked.append(h)
    return picked


def _parse_llm_output(text, fallback_title):
    headline, dek, body = fallback_title, "", text
    m = re.match(r"\s*HEADLINE:\s*(.+?)\n\s*DEK:\s*(.+?)\n-{3,}\n(.*)", text, re.S | re.I)
    if m:
        headline, dek, body = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return headline, dek, body


def _is_llm_unavailable(text):
    return (text or "").strip().startswith("_Analyst narrative unavailable")


def _editorial_pass(grounding, draft_body):
    """A second, independent model call acting as VAPE Wire's copy desk —
    checks the drafted story against the same sourced material the reporter
    was given and either tightens it or flags what it can't stand behind.
    Real value, not theater: a separate pass genuinely catches claims that
    slipped past the drafting prompt's own instructions, the same reason a
    real newsroom doesn't let a reporter self-publish. If the editor call
    itself is unavailable this cycle, the draft ships as-is rather than
    being replaced by a failure message — never worse than skipping this
    step entirely."""
    instructions = (
        "You are VAPE Wire's copy editor and fact-checker, reviewing a draft a staff reporter just "
        "filed. Check every factual claim, figure, and quote in the draft below against the sourced "
        "material — if a claim isn't actually supported by it, cut it or soften it to what the "
        "material actually shows; do not add new claims of your own. Tighten prose only where it "
        "genuinely improves clarity — this is a fact-check and light edit, not a rewrite from "
        "scratch, and the reporter's voice and structure should survive intact. Keep all existing "
        "inline source links. Output ONLY the corrected report body in markdown — no preamble, no "
        "editor's notes, no commentary about what you changed.\n\n"
        f"DRAFT TO REVIEW:\n{draft_body}"
    )
    edited = ic.grok_analysis(
        "copy editor and fact-checker at VAPE Wire",
        grounding, instructions=instructions, max_tokens=2200, temperature=0.3,
    )
    if _is_llm_unavailable(edited) or not edited.strip():
        return draft_body, False
    return edited.strip(), True


def write_story(candidate):
    corroboration = ic.web_search_snippets(candidate["title"], max_results=5)

    image = candidate.get("image") or nc.extract_og_image(candidate["url"])
    if not image:
        for r in corroboration.get("results", []):
            image = nc.extract_og_image(r["url"])
            if image:
                break

    topic_label = nc.TOPIC_LABELS.get(candidate.get("topic"), candidate.get("topic") or "General")
    grounding = (
        f"ORIGINAL HEADLINE: {candidate['title']}\n"
        f"SOURCE: {candidate.get('source') or 'unknown'}\n"
        f"SOURCE URL: {candidate['url']}\n"
        f"PUBLISHED: {candidate.get('published') or 'unknown'}\n"
        f"BEAT: {topic_label}\n\n"
        f"Corroborating web search results:\n"
        + "\n".join(f"- [{r['title']}]({r['url']}) — {r['snippet']}" for r in corroboration.get("results", []))
    )
    instructions = (
        "You are filing this story for VAPE Wire, VAPE's own news desk — a real, standing news "
        "operation, not a summary tool. Write with the authority and confidence of a staff reporter "
        "at a top-tier outlet, not a disclaimer-laden assistant: no hedging like 'as an AI' or 'I "
        "cannot verify' language — state plainly what the sourced material shows and what it "
        "doesn't. Write an in-depth, genuinely investigative report — the kind of reporting worthy "
        "of leading a major outlet's front page: dig into WHY this is happening, who is affected, "
        "what the second-order consequences are, and what a sharp reader should watch for next. Do "
        "not just restate the headline. Cite your sources inline with markdown links as you use "
        "them (the original story and anything from your own search). If your search corroborates "
        "or complicates the original story, say so explicitly. The one hard rule that never bends "
        "even under this house style: never invent a quote, figure, or fact not in the material "
        "above or in a real source you found — authority of voice, not invention, is the standard. "
        "Respond in EXACTLY this format (no extra commentary before or after):\n\n"
        "HEADLINE: <your own sharp, factually accurate headline for this story, not just a copy of the original>\n"
        "DEK: <one punchy sentence summarizing the stakes, plain text, no markdown>\n"
        "---\n"
        "<the full report in markdown, using ## subheadings, at least 400 words if the material "
        "genuinely supports it>"
    )
    raw = ic.grok_analysis(
        "staff reporter at VAPE Wire, writing under the byline 'VAPE Reporter'",
        grounding, instructions=instructions, max_tokens=2200, temperature=0.6,
    )
    headline, dek, body = _parse_llm_output(raw, candidate["title"])
    body, fact_checked = _editorial_pass(grounding, body)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    source_lines = [f"- [{candidate['title']}]({candidate['url']}) — {candidate.get('source') or 'source'}"]
    for r in corroboration.get("results", []):
        source_lines.append(f"- [{r['title']}]({r['url']}) — {r.get('snippet', '')[:120]}")

    report_md = f"""# {headline}

**Agency:** VAPE Wire
**Byline:** VAPE Reporter
**Date:** {stamp}
**Topic:** {topic_label}
**Dek:** {dek}
**Image:** {image or FALLBACK_IMAGE}
**Fact-checked:** {"Yes — copy desk review completed" if fact_checked else "Draft not independently reviewed this cycle (copy desk unavailable)"}

---

{body}

---

## Sources

{chr(10).join(source_lines)}

---

*VAPE Wire — {topic_label} desk. Reported and edited by VAPE's autonomous newsroom (agents/news_reporter.py).*
"""
    path = nc.write_news_report(nc.slugify(headline), report_md)
    ic.log_sweep_memory("agents/news_reporter.py", topic_label, dek or headline, path,
                         tags=["news-intel", topic_label.lower()])
    return path


def run():
    n = int(os.getenv("NEWS_REPORTER_PICKS", "1"))
    state = nc.load_state()
    candidates = _pick_candidates(state, n)
    if not candidates:
        print("[news_reporter] no unreported headlines available this cycle")
        return []
    written = []
    for c in candidates:
        try:
            path = write_story(c)
            nc.mark_reported(state, c["url"])
            written.append(path)
            print(f"[news_reporter] wrote {os.path.relpath(path, nc.ROOT)}")
        except Exception as e:
            print(f"[news_reporter] failed on '{c['title'][:60]}': {e}")
    nc.save_state(state)
    return written


if __name__ == "__main__":
    run()
