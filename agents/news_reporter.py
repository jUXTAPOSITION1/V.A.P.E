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

Real substance, not just a headline: before drafting, write_story() scrapes
the actual body text of the source article (and, if that fails, the top
corroborating search hits) via agents/news_common.py::scrape_article_text()
-- see that function's docstring for the real bug this fixes. Every early
report written before this was drafted from nothing but a bare headline,
which is why so many degraded into "thin sourcing, cannot verify" filler
regardless of how the prompt was worded; the model was telling the truth
about the material it actually had. Candidates from the native-RSS discovery
lane (news_common.py's NATIVE_RSS_FEEDS) also carry the outlet's own feed
summary as `candidate["snippet"]`, included in the grounding as real,
authoritative material in its own right -- not just a fallback for when a
live scrape fails.

Two model calls per story, mirroring how a real newsroom splits reporting
from editing: write_story() drafts under a reporter byline, then
_editorial_pass() reviews that draft against the same sourced material with
a second, independent call before it ships — catching unsupported claims
the drafting prompt's own instructions missed, not just restating them.

Images, in priority order (explicit direction, 2026-07-28 -- revised same
day to drop the real-photo tier entirely: republishing another outlet's own
photo of a story it broke is a real copyright exposure VAPE shouldn't carry,
regardless of technical feasibility):
  1. AI-generated, described by a fresh, story-specific prompt
     (_image_prompt(), grounded in the real headline/dek/body, not a
     generic template) and tried against two independent models in order:
     Google's Gemini image model first (agents/llm.py::ask_gemini_image(),
     a free attempt -- VAPE's own Vertex AI project, no separate per-image
     billing beyond what's provisioned there once enabled), then xAI's Grok
     Image (agents/llm.py::ask_xai_image()) as the model that actually works
     today, since Gemini's free tier can't yet serve this specific model
     (confirmed real HTTP 429 "quota exceeded ... limit: 0" from a live
     dispatch).
  2. VAPE's own brand mark as the always-available fallback if both AI
     models are unavailable or fail this cycle -- no source-photo tier.
Every AI-generated image gets VAPE Wire's V-mark + wordmark stamped on via
brand_image() before publication; the logo-only fallback (tier 2) is
already 100% branded and skips that step. Every report records which tier
it actually got via the Image source field.

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

FALLBACK_IMAGE = "assets/logo-v-256.png"  # VAPE's own brand mark -- used only when no AI image or source photo is available


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


def _image_prompt(headline, dek, body, topic_label):
    """One vivid, narrative text-to-image prompt for this specific story --
    not a generic per-topic template. Follows Google Cloud's own "Ultimate
    prompting guide for Nano Banana" formula (Subject + Action + Location/
    context + Composition + Style, full descriptive sentences rather than a
    keyword list) and asks for real photojournalism/editorial-illustration
    style grounded in the story's actual subject matter -- a coin macro shot,
    a trading floor, a courthouse, a data center, whatever the story is
    actually about -- never a fabricated likeness of a real named person
    (defamation/deepfake risk) and never any rendered text or logos (VAPE's
    own wordmark gets stamped on separately by brand_image(); a third
    party's brand/trademark has no business appearing in VAPE's own
    illustration). Returns a plain-text prompt string, or None if the LLM
    call fails -- callers must treat that as "skip AI generation this
    story," never invent a placeholder prompt."""
    instructions = (
        "Write ONE image-generation prompt for the photo that should accompany this news story. "
        "Follow this exact structure as flowing descriptive sentences (not a keyword list): what the "
        "photo actually shows (a concrete, real-world subject grounded in the story below -- e.g. a "
        "close-up of physical coins/currency, a trading floor, server racks, a courthouse exterior, a "
        "city skyline, hands at a keyboard -- never an abstract 'crypto' cliche unless the story truly "
        "has no more concrete subject), what's happening in the frame, where it's set, how it's "
        "composed (shot type, angle), and a photographic/editorial-illustration style (lighting, lens, "
        "color grading). Do NOT include any text, words, numbers, logos, or brand marks anywhere in "
        "the image -- describe a clean photographic scene only. Do NOT depict any specific named real "
        "person's likeness. Output ONLY the prompt itself, one paragraph, no preamble, no quotation "
        "marks, no commentary.\n\n"
        f"HEADLINE: {headline}\nDEK: {dek}\nBEAT: {topic_label}\n\nSTORY BODY:\n{body[:1500]}"
    )
    prompt = ic.grok_analysis(
        "photo editor at VAPE Wire choosing today's lead image",
        f"{headline}\n{dek}", instructions=instructions, max_tokens=300, temperature=0.7,
    )
    if _is_llm_unavailable(prompt) or not prompt.strip():
        return None
    return prompt.strip()


def _generate_ai_image(headline, dek, body, topic_label, slug):
    """Tier 1 of the image chain (see module docstring): one fresh prompt,
    grounded in this specific story, tried against two independent image
    models in order -- Google's Gemini image model first (ask_gemini_image()
    -- VAPE's own Vertex AI project, no separate per-image billing beyond
    what's already provisioned there once enabled), then xAI's Grok Image
    (ask_xai_image()) as a working fallback while Gemini's free tier can't
    yet serve this specific model (confirmed real HTTP 429 "quota exceeded
    ... limit: 0" from a live dispatch). Returns the branded site-relative
    path on success, or None if the prompt step fails or both models do --
    callers fall through to the real-photo tier exactly as if this
    function didn't exist."""
    prompt = _image_prompt(headline, dek, body, topic_label)
    if not prompt:
        return None
    image_bytes = llm.ask_gemini_image(prompt)
    if image_bytes:
        return nc.brand_image(image_bytes, slug)
    image_url = llm.ask_xai_image(prompt)
    if image_url:
        return nc.brand_image(image_url, slug)
    return None


def write_story(candidate):
    corroboration = ic.web_search_snippets(candidate["title"], max_results=5)

    # Real substance for the model to actually report on -- see module
    # docstring's "Real substance, not just a headline" note. The primary
    # source article first; if that scrape comes up empty (paywall, JS-
    # rendered page, dead link), fall through to the top 2 corroborating
    # hits so the story still has real body text behind it rather than
    # just a headline + search snippets.
    article_text = nc.scrape_article_text(candidate["url"])
    if not article_text:
        for r in corroboration.get("results", [])[:2]:
            article_text = nc.scrape_article_text(r["url"])
            if article_text:
                break

    # "Only report on what we can source" (explicit direction, 2026-07-28):
    # a bare headline with no scraped body, no outlet-provided summary, and
    # no corroborating search hit is not enough real material to write an
    # actual story from -- every such story before this gate degraded into
    # the same "thin sourcing, cannot verify anything" filler regardless of
    # how the drafting prompt was worded (the model was telling the truth
    # about what little it had). Skip it here, before ever spending an LLM
    # call, rather than publish a report with nothing in it. Callers must
    # treat None as "no report written this candidate" and move on to the
    # next one -- see run()'s retry loop.
    has_substance = bool(article_text) or bool((candidate.get("snippet") or "").strip()) \
        or bool(corroboration.get("results"))
    if not has_substance:
        return None

    topic_label = nc.TOPIC_LABELS.get(candidate.get("topic"), candidate.get("topic") or "General")
    grounding = (
        f"ORIGINAL HEADLINE: {candidate['title']}\n"
        f"SOURCE: {candidate.get('source') or 'unknown'}\n"
        f"SOURCE URL: {candidate['url']}\n"
        f"PUBLISHED: {candidate.get('published') or 'unknown'}\n"
        f"BEAT: {topic_label}\n\n"
        # The outlet's own feed summary (native RSS lane -- see
        # news_common.py's NATIVE_RSS_FEEDS) is real, authoritative material
        # in its own right, not just a fallback for when scraping fails --
        # included whenever present regardless of scrape outcome.
        + (f"Source outlet's own summary:\n{candidate['snippet']}\n\n" if candidate.get("snippet") else "")
        + (f"Scraped article body:\n{article_text}\n\n" if article_text else
           "No article body could be scraped this cycle -- only the headline and any web search "
           "results below are real, verified material.\n\n")
        + f"Corroborating web search results:\n"
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

    slug = nc.slugify(headline)
    ai_image = _generate_ai_image(headline, dek, body, topic_label, slug)
    if ai_image:
        image, image_source = ai_image, "AI-generated — VAPE Wire branded"
    else:
        image, image_source = FALLBACK_IMAGE, "VAPE brand mark (no AI image available this cycle)"

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
    path = nc.write_news_report(slug, report_md)
    ic.log_sweep_memory("agents/news_reporter.py", topic_label, dek or headline, path,
                         tags=["news-intel", topic_label.lower()])
    return path


def run():
    n = int(os.getenv("NEWS_REPORTER_PICKS", "1"))
    state = nc.load_state()
    written = []
    attempts = 0
    # Bounded retry so an unusually thin feed (several headlines in a row
    # with no scrapable body, no outlet summary, and no corroboration --
    # see write_story()'s "only report on what we can source" gate) can't
    # burn an unbounded amount of this cycle's scrape/LLM budget chasing a
    # full n stories that may not exist.
    max_attempts = max(n * 3, 3)
    while len(written) < n and attempts < max_attempts:
        candidates = _pick_candidates(state, 1)
        if not candidates:
            break
        c = candidates[0]
        attempts += 1
        try:
            path = write_story(c)
        except Exception as e:
            print(f"[news_reporter] failed on '{c['title'][:60]}': {e}")
            nc.mark_reported(state, c["url"])
            continue
        # Marked reported either way (wrote a real story, or genuinely had
        # nothing sourceable) -- a headline that can't be scraped now won't
        # magically become scrapable next cycle, so retrying it forever
        # would just waste budget indefinitely.
        nc.mark_reported(state, c["url"])
        if path:
            written.append(path)
            print(f"[news_reporter] wrote {os.path.relpath(path, nc.ROOT)}")
        else:
            print(f"[news_reporter] skipped '{c['title'][:60]}' -- no sourceable substance this cycle")
    if not written and attempts == 0:
        print("[news_reporter] no unreported headlines available this cycle")
    nc.save_state(state)
    return written


if __name__ == "__main__":
    run()
