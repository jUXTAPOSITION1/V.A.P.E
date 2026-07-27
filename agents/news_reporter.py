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

Images, in priority order: (1) a real photo the discovered story already
carried (CoinGecko's own thumbnail), (2) a real photo scraped from the
source article's or a corroborating source's og:image, (3) only if neither
exists, a genuine AI-generated illustration via agents/llm.py::generate_image()
(xAI Grok Image — real cost, capped, see that function's docstring), (4)
VAPE's own brand mark as the final, always-available fallback. Every report
records which tier it actually got via the Image source field — an AI
illustration is never presented as a real photo.

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
from agents import llm  # noqa: E402

FALLBACK_IMAGE = "assets/logo-v-256.png"  # VAPE's own brand mark -- used only when no real photo AND no generated image are available

# Which of the two illustration styles fits each beat best (per user
# direction: vary style by story rather than picking one house look).
# "editorial" = photojournalistic/serious-wire-service; "abstract" =
# clean geometric/chart/network motifs -- see STYLE_PROMPTS below.
ABSTRACT_STYLE_TOPICS = {"crypto-markets", "macro", "stocks"}
STYLE_PROMPTS = {
    "editorial": ("photojournalistic editorial illustration, serious financial-news wire-service "
                  "style, cinematic lighting, realistic"),
    "abstract": ("abstract data-driven illustration, clean geometric shapes, network and chart "
                 "motifs, financial-news color palette"),
}


def _image_prompt(headline, dek, topic_key, topic_label):
    style = "abstract" if topic_key in ABSTRACT_STYLE_TOPICS else "editorial"
    return (
        f"{STYLE_PROMPTS[style]}. No text, no logos, no watermarks, no legible letters anywhere "
        f"in the image. Editorial image for a news story about: {headline}. "
        f"Context: {dek or topic_label}."
    )


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

    real_image = candidate.get("image") or nc.extract_og_image(candidate["url"])
    if not real_image:
        for r in corroboration.get("results", []):
            real_image = nc.extract_og_image(r["url"])
            if real_image:
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

    image, image_source = real_image, "Source photo"
    if not image:
        generated = llm.generate_image(_image_prompt(headline, dek, candidate.get("topic"), topic_label))
        if generated:
            image, image_source = generated, "AI-generated illustration (xAI Grok Image)"
    if not image:
        image, image_source = FALLBACK_IMAGE, "VAPE brand mark (no photo or illustration available this cycle)"
    else:
        # Every real/generated image gets VAPE Wire's own V-mark + wordmark
        # stamped on before publication -- see brand_image()'s docstring.
        # The already-100%-branded logo fallback above skips this step.
        branded = nc.brand_image(image, nc.slugify(headline))
        if branded:
            image, image_source = branded, f"{image_source} — VAPE Wire branded"

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
**Image:** {image}
**Image source:** {image_source}
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
