#!/usr/bin/env python3
"""
VAPE fine-tune dataset builder — turns VAPE's own real operating history into
a chat-format instruction-tuning corpus, so a small open-weight model can be
taught to reason and act *the way VAPE already does*.

Why this is a real dataset and not a synthetic one: every example traces to a
real, already-published/committed VAPE artifact. Three sources, each with its
own honesty story:

  investigations   intel/investigations/investigation-*.md — INPUT is the
                   observable recon VAPE actually gathered (DexScreener,
                   GoPlus, on-chain presence, contract verification,
                   hack-feed correlation). OUTPUT is the verdict VAPE
                   actually reached, and that verdict+score+rationale come
                   from investigate.py's DETERMINISTIC score() function, not
                   an LLM. The strongest, most trustworthy signal here.

  sweeps           intel/reports/{security,base,virtuals,sentiment,macro}-
                   *.md — same discipline, applied across every domain VAPE
                   covers, not just token investigations. INPUT is the real
                   data tables each sweep pulled (incident feed, TVL, token
                   market data, Fear&Greed); OUTPUT is ONLY the deterministic
                   verdict heading + its immediate rule-based explanation
                   (e.g. "Computed deterministically from...") — the LLM-
                   written narrative sections further down each report
                   (Ecosystem/Key Drivers/Action Items/Web Signals/etc.) are
                   deliberately EXCLUDED from training, since those are
                   another model's prose, not VAPE's own grounded reasoning,
                   and folding them in would silently violate this file's
                   whole reason for existing.

  lessons          skillforge/memory/lessons.jsonl — VAPE's own logged
                   operational history (self-improve builds, PR review
                   outcomes, expert-assessment disagreements). Honesty note:
                   unlike the two sources above, this one is a MIX — some
                   entries are deterministic outcomes (a build shipped, a PR
                   merged/rejected), others are an LLM's own prior commentary
                   (e.g. an expert-assessment disagreement). Included anyway
                   because the user explicitly wants VAPE to learn from its
                   own operating history, not just re-derive verdicts — but
                   the dataset card says so plainly rather than presenting it
                   as equally rock-solid ground truth.

  (findings.jsonl was deliberately NOT used as a fourth source: ~70% of its
  rows are investigate.py duplicates already covered by the investigations
  source, and the rest are terse one-line summaries the sweep-report parser
  above already captures more richly from the real report tables.)

  external         data/finetune/external_corpus.jsonl (optional — only
                   present after running scripts/build_external_corpus.py,
                   which does real network I/O this offline script never
                   does itself). Real third-party security ground truth VAPE
                   didn't produce: NVD CVE disclosures (label = the CVE's own
                   official CVSS severity) and Code4rena audit-contest
                   findings (label = the contest's own judged High/Medium
                   risk category). Same rule as everywhere else in this file:
                   only rows with a real, independently-verified label are
                   included — see build_external_corpus.py's own docstring
                   for exactly which sources qualified and which didn't.

This does NOT replace score() or any sweep's compute_*_score(). Per this
repo's design law (rule-based first, LLM only when reasoning is required),
the deterministic scorers stay the source of truth. A model fine-tuned on
this corpus is a better "fast" tier — one that writes and reasons like VAPE
given real recon — and a candidate the existing promptfoo/deepteam harness
(skillforge/tools/ai-redteam/, see training/eval_candidate.py) can grade
against the frontier tier before any real traffic is routed to it.

Output (data/finetune/):
  vape_finetune.train.jsonl   OpenAI-style chat messages, ~90%
  vape_finetune.val.jsonl     held-out ~10% (deterministic split)
  DATASET_CARD.md             provenance, format, per-source stats, honest limits

The split is deterministic (hash of a stable per-example key — target address
for investigations, report path for sweeps, lesson id for lessons), so
re-running yields byte-identical files — reproducible corpora, same as every
other real-data artifact in this repo.

Usage:
  python scripts/build_finetune_dataset.py            # build train/val + card
  python scripts/build_finetune_dataset.py --stats    # counts only, write nothing
"""
import argparse
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INVEST_GLOB = os.path.join(ROOT, "intel", "investigations", "investigation-*.md")
REPORTS_DIR = os.path.join(ROOT, "intel", "reports")
LESSONS_PATH = os.path.join(ROOT, "skillforge", "memory", "lessons.jsonl")
OUT_DIR = os.path.join(ROOT, "data", "finetune")
EXTERNAL_PATH = os.path.join(OUT_DIR, "external_corpus.jsonl")

VAL_FRACTION = 0.10  # ~1-in-10 held out for evaluation

# The system prompt the fine-tuned model is trained under — deliberately the
# same framing VAPE's real report pipeline uses: real recon only, risk is the
# default posture, the verdict must be justified by the observable evidence.
SYSTEM_PROMPT = (
    "You are VAPE, an autonomous on-chain security investigator for Base and the "
    "Virtuals ecosystem. Given real, keyless recon on a token (DexScreener market "
    "data, GoPlus token-security flags, on-chain presence, contract verification, "
    "and hack-feed correlation), produce a risk verdict. Risk is the default "
    "posture for an anonymous or young token — the ABSENCE of red flags is not "
    "evidence of safety. Output a verdict (PROCEED / CAUTION / REJECT), a safety "
    "score out of 100, and a rationale grounded strictly in the observable "
    "evidence provided. Never invent data that was not given."
)

# Input recon sections (kept verbatim) vs. the output verdict block. The
# heading text matches investigate.py::write_report()'s exact output. Two
# report-format generations exist in the ledger — an older plain one and a
# newer badge-header one with extra sections (Positive Signals, Public Web
# Signals) and the score embedded in the verdict line — both are handled.
RECON_HEADINGS = [
    "Market & Liquidity",
    "Token Security",
    "On-chain Presence",
    "Contract Verification",
    "Threat Correlation",
    "Public Web Signals",
]

# ── sweeps (intel/reports/) ──────────────────────────────────────────────────
SWEEP_SYSTEM_PROMPT = (
    "You are VAPE, an autonomous on-chain intelligence analyst covering Base, "
    "the Virtuals ecosystem, and broader crypto markets. Given real, keyless "
    "data (on-chain, DeFiLlama, DexScreener, Fear & Greed), produce the "
    "deterministic verdict/score/trend this data implies, and state which "
    "factors are driving it. Ground every claim strictly in the data provided "
    "— never invent a number, an incident, or a trend that was not given."
)

# (report_type, glob_prefix, verdict_heading_regex) — the regex must match
# ONLY the one heading each sweep script emits for its own deterministic
# score/trend/level, per that script's own write_report()/run() output.
SWEEP_CONFIGS = [
    ("security", "security-*.md", re.compile(r"^##\s+THREAT LEVEL:")),
    ("base", "base-*.md", re.compile(r"^##\s+BASE HEALTH SCORE:")),
    ("virtuals", "virtuals-*.md", re.compile(r"^##\s+PROTOCOL HEALTH:")),
    ("macro", "macro-*.md", re.compile(r"^##\s+MACRO TREND:")),
    ("sentiment", "sentiment-*.md", re.compile(r"^##\s+SENTIMENT SCORE:")),
]

# Heading substrings (case-insensitive) that mark the start of an LLM-written
# narrative section in a sweep report — everything from the first match
# onward is excluded from the INPUT data tables, since it's synthesis, not
# recon. Deliberately broad/over-inclusive: missing a real data heading here
# just means one fewer input table gets used, which is a far safer failure
# mode than accidentally training on another model's prose.
NARRATIVE_HEADING_MARKERS = [
    "ecosystem", "action items", "key drivers", "micro opportunities",
    "summary verdict", "top narratives", "narrative shifts", "web signals",
    "sources", "vape's own", "vape impact",
]


def _is_narrative_heading(heading):
    h = heading.lower()
    return any(marker in h for marker in NARRATIVE_HEADING_MARKERS)


def parse_sweep_report(path, report_type):
    """Extract one training pair from a sweep report, or None if it doesn't
    contain the one deterministic verdict heading this sweep type emits.

    INPUT: every '## ' section BEFORE the verdict heading and, after it,
    every section up to (not including) the first narrative-looking heading
    — i.e. the real data tables only.
    OUTPUT: the verdict heading line + its immediate body (the deterministic
    "Computed deterministically from..." / "Real Fear & Greed index..."
    explanation each sweep writes right under its own score) — nothing past
    the next '---' or heading.
    """
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    _, _, verdict_regex = next(c for c in SWEEP_CONFIGS if c[0] == report_type)
    lines = text.splitlines()
    verdict_idx = next((i for i, line in enumerate(lines) if verdict_regex.match(line)), None)
    if verdict_idx is None:
        return None  # this report generation/run didn't emit the expected heading

    verdict_heading = lines[verdict_idx].lstrip("#").strip()
    body = []
    for line in lines[verdict_idx + 1:]:
        if line.strip() == "---" or re.match(r"^##\s+", line):
            break
        body.append(line)
    verdict_body = "\n".join(body).strip()
    if not verdict_body:
        return None  # no deterministic explanation captured — nothing to learn from

    sections = _split_sections(text)
    input_parts = []
    for heading, sec_body in sections.items():
        if heading == verdict_heading:
            continue
        if _is_narrative_heading(heading):
            break
        if sec_body:
            input_parts.append(f"## {heading}\n{sec_body}")
    if not input_parts:
        # Expected for "sentiment" specifically, not a bug: that report format
        # has no separate real-data table distinct from the deterministic
        # score body itself (just the Fear&Greed reading + prior value), so
        # it never contributes examples here — nothing dishonest to fall back
        # to (the alternative would be an input==output trivial echo).
        return None

    return {
        "key": os.path.basename(path),
        "messages": [
            {"role": "system", "content": SWEEP_SYSTEM_PROMPT},
            {"role": "user", "content": f"Sweep type: {report_type}\n\n" + "\n\n".join(input_parts)},
            {"role": "assistant", "content": f"{verdict_heading}\n\n{verdict_body}"},
        ],
    }


def collect_sweeps():
    """Parse every sweep report of every configured type into a training
    example. No dedup needed — each report file is already a unique cycle."""
    examples = []
    for report_type, glob_suffix, _ in SWEEP_CONFIGS:
        for fp in sorted(glob.glob(os.path.join(REPORTS_DIR, glob_suffix))):
            rec = parse_sweep_report(fp, report_type)
            if rec:
                examples.append(rec)
    return examples


# ── lessons (skillforge/memory/lessons.jsonl) ────────────────────────────────
LESSON_SYSTEM_PROMPT = (
    "You are VAPE, reflecting on your own operating history. Given a real "
    "situation from your own record (a build, a review outcome, a prior "
    "assessment), state what you learned or decided — grounded only in the "
    "facts given, never inventing context that wasn't provided."
)


def parse_lesson(line):
    try:
        d = json.loads(line)
    except Exception:
        return None
    title, content = d.get("title"), d.get("content")
    if not title or not content:
        return None
    meta = d.get("metadata") or {}
    meta_bits = [f"{k}: {v}" for k, v in meta.items() if v is not None]
    user = title + ("\n\n" + "\n".join(meta_bits) if meta_bits else "")
    return {
        "key": d.get("id") or title,
        "messages": [
            {"role": "system", "content": LESSON_SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": content},
        ],
    }


def collect_lessons():
    if not os.path.exists(LESSONS_PATH):
        return []
    examples = []
    with open(LESSONS_PATH, encoding="utf-8", errors="ignore") as f:
        for line in f:
            rec = parse_lesson(line)
            if rec:
                examples.append(rec)
    return examples


def _split_sections(text):
    """Return {heading_prefix: body} for each '## Heading' block."""
    sections = {}
    cur, buf = None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)", line)
        if m:
            if cur is not None:
                sections[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        sections[cur] = "\n".join(buf).strip()
    return sections


def _field(text, label):
    m = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", text)
    return m.group(1).strip() if m else None


def parse_investigation(path):
    """Extract a training pair from one investigation report, or None if the
    report is missing the fields that make it a valid, learnable example."""
    with open(path, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    target = _field(text, "Target")
    chain = _field(text, "Chain")
    verdict_raw = _field(text, "Verdict") or ""
    vm = re.search(r"(PROCEED|CAUTION|REJECT)", verdict_raw, re.I)
    # Score: the older format has a dedicated "**Safety Score:** NN/100" field;
    # the newer one embeds it in the verdict line ("CAUTION (68/100)"). Try the
    # field, then fall back to the verdict line — same fallback build_intel_index
    # uses, so both report generations parse.
    score_raw = _field(text, "Safety Score") or ""
    sm = re.search(r"(\d{1,3})\s*/\s*100", score_raw) or re.search(r"\((\d{1,3})\s*/\s*100\)", verdict_raw)
    if not (target and vm and sm):
        return None  # not a scoreable investigation — skip, never fabricate

    verdict = vm.group(1).upper()
    scoren = int(sm.group(1))
    sections = _split_sections(text)

    # INPUT: the observable recon, verbatim, in a stable order.
    recon_parts = [f"Target: {target}", f"Chain: {chain or 'unknown'}", ""]
    have_any = False
    for want in RECON_HEADINGS:
        for head, body in sections.items():
            if head.startswith(want) and body:
                recon_parts.append(f"## {head}\n{body}")
                have_any = True
                break
    if not have_any:
        return None  # no recon body at all — nothing to learn from

    # OUTPUT: the verdict block VAPE actually produced — verdict, score, the
    # risk-factor rationale, and (newer format) the positive legitimacy
    # signals. The positives are load-bearing for VAPE's reasoning: the score
    # cap logic turns on how many were found, so the model must learn to
    # surface them, not just enumerate red flags.
    rationale = positives = ""
    for head, body in sections.items():
        if head.startswith("Verdict Rationale") and body:
            rationale = body
        elif head.startswith("Positive Signals") and body:
            positives = body
    out_parts = [f"Verdict: {verdict}", f"Safety Score: {scoren}/100"]
    if rationale:
        out_parts.append(f"\nRationale:\n{rationale}")
    if positives:
        out_parts.append(f"\nPositive signals:\n{positives}")

    return {
        "target": target.strip("`").lower(),
        "verdict": verdict,
        "score": scoren,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "\n".join(recon_parts).strip()},
            {"role": "assistant", "content": "\n".join(out_parts).strip()},
        ],
    }


def _is_val(key):
    """Deterministic ~10% holdout keyed by a stable per-example string (target
    address / report filename / lesson id), so re-runs are stable and no
    example ever straddles train/val."""
    h = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return (h % 100) < int(VAL_FRACTION * 100)


def collect_investigations():
    """Parse every investigation report into a training example, deduplicating
    by (target, verdict, score) so a heavily re-investigated address doesn't
    dominate the corpus. Returns the list of unique examples."""
    seen, examples = set(), []
    for fp in sorted(glob.glob(INVEST_GLOB)):
        rec = parse_investigation(fp)
        if not rec:
            continue
        # Dedup by (target, verdict, score) — the ledger re-investigates the
        # same address over time; keep one canonical example per verdict state
        # so a heavily-re-checked token doesn't dominate the corpus.
        key = (rec["target"], rec["verdict"], rec["score"])
        if key in seen:
            continue
        seen.add(key)
        rec["source"] = "investigation"
        rec["key"] = rec["target"]
        examples.append(rec)
    return examples


def collect_external():
    """Optional fourth source: data/finetune/external_corpus.jsonl, produced
    by scripts/build_external_corpus.py's real network fetches (NVD CVE +
    Code4rena). Returns [] if that script has never been run — this stays a
    real gap in the dataset card's stats, never silently faked."""
    if not os.path.exists(EXTERNAL_PATH):
        return []
    examples = []
    with open(EXTERNAL_PATH, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not row.get("messages") or not row.get("source_id"):
                continue
            examples.append({"key": row["source_id"], "messages": row["messages"]})
    return examples


def collect_all():
    """All four sources, each example tagged with its source category and a
    stable split key. See module docstring for why findings.jsonl is excluded."""
    investigations = collect_investigations()
    sweeps = collect_sweeps()
    for e in sweeps:
        e["source"] = "sweep"
    lessons = collect_lessons()
    for e in lessons:
        e["source"] = "lesson"
    external = collect_external()
    for e in external:
        e["source"] = "external"
    return investigations + sweeps + lessons + external


def _source_counts(examples):
    c = {}
    for e in examples:
        c[e["source"]] = c.get(e["source"], 0) + 1
    return c


def _verdict_counts(examples):
    c = {}
    for e in examples:
        if e["source"] != "investigation":
            continue
        c[e["verdict"]] = c.get(e["verdict"], 0) + 1
    return c


def build(write):
    """Collect examples from every source, split train/val deterministically,
    and (when write) emit the JSONL files + dataset card. write=False prints
    stats only."""
    examples = collect_all()
    train = [e for e in examples if not _is_val(e["key"])]
    val = [e for e in examples if _is_val(e["key"])]

    print(f"parsed {len(examples)} example(s) — {_source_counts(examples)}")
    print(f"  investigation verdict mix: {_verdict_counts(examples)}")
    print(f"  train: {len(train)}  val: {len(val)}")
    if not write:
        return

    os.makedirs(OUT_DIR, exist_ok=True)

    def _dump(name, rows):
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps({"messages": r["messages"]}, ensure_ascii=False) + "\n")
        return path

    _dump("vape_finetune.train.jsonl", train)
    _dump("vape_finetune.val.jsonl", val)
    _write_card(examples, train, val)
    print(f"wrote {OUT_DIR}/vape_finetune.{{train,val}}.jsonl + DATASET_CARD.md")


def _write_card(examples, train, val):
    src_counts = _source_counts(examples)
    verdict_counts = _verdict_counts(examples)
    card = f"""# VAPE — fine-tune dataset card

**What:** a chat-format instruction-tuning corpus built from VAPE's own real,
already-committed operating history, by
[`scripts/build_finetune_dataset.py`](../../scripts/build_finetune_dataset.py).
Three sources, each with its own honesty story — see the module docstring for
the full rationale:

- **investigation** ({src_counts.get('investigation', 0)} examples) —
  `intel/investigations/investigation-*.md`. INPUT is the real recon VAPE
  gathered (DexScreener, GoPlus, on-chain presence, contract verification,
  hack-feed correlation); OUTPUT is the verdict/score/rationale
  `agents/investigate.py::score()` actually produced — a DETERMINISTIC,
  rule-based function, not an LLM. The strongest signal in this corpus.
- **sweep** ({src_counts.get('sweep', 0)} examples) —
  `intel/reports/{{security,base,virtuals,sentiment,macro}}-*.md`. Same
  discipline across every domain VAPE covers. OUTPUT is ONLY each report's
  deterministic verdict heading + its immediate rule-based explanation — the
  LLM-written narrative sections further down each report are deliberately
  excluded from training.
- **lesson** ({src_counts.get('lesson', 0)} examples) —
  `skillforge/memory/lessons.jsonl`, VAPE's own logged operational history
  (self-improve builds, PR review outcomes, expert-assessment disagreements).
  Honesty note: this source is a MIX of deterministic outcomes and prior LLM
  commentary — included because the user wants VAPE to learn from its own
  operating history, not because every row here is as rock-solid as the two
  sources above.
- **external** ({src_counts.get('external', 0)} examples) —
  `data/finetune/external_corpus.jsonl`, produced separately by
  `scripts/build_external_corpus.py` (real network fetches: NVD CVE API +
  Code4rena audit-contest findings). OUTPUT is a severity label that comes
  from the CVE's own official CVSS metric or the contest's own judged risk
  category — never re-derived. This is the first THIRD-PARTY source in the
  corpus (everything else is VAPE's own operating history); see that
  script's docstring for exactly which external sources qualified (verified
  real structure) and which didn't (SWC Registry, Sherlock — deferred, not
  silently dropped).

**Why most of the labels are trustworthy:** investigation and sweep outputs
come from this repo's own deterministic scoring functions, never an LLM. This
corpus teaches a model to imitate VAPE's grounded reasoning, not to re-distill
another model's guesses — with the lesson source's mixed provenance called
out plainly rather than hidden.

## Stats
- Total examples: **{len(examples)}** — {src_counts}
- Investigation verdict mix: {verdict_counts}
- Split (deterministic, hashed per-example key): **{len(train)} train / {len(val)} val**

## Intended use
Fine-tune a small-to-mid open-weight instruct model (LoRA/QLoRA — verify the
current Gemma lineup on Hugging Face before picking a checkpoint, don't trust
a specific model name baked into old docs) to serve as a better "fast" tier —
one that reasons and writes like VAPE given real recon across every domain it
covers. It does **not** replace any `compute_*_score()`/`score()` function;
the deterministic scorers stay the source of truth (this repo's design law).
A fine-tuned candidate should be graded against the frontier tier with the
existing `skillforge/tools/ai-redteam` (promptfoo/deepteam) harness — see
`training/eval_candidate.py` — before any real traffic is routed to it.

## Honest limitations
- **Small.** This is a seed corpus that grows for free as VAPE keeps
  operating — not a finished training set. Re-run this script as the
  investigation ledger, sweep reports, and lessons log all grow.
- **On-chain / keyless recon only** for investigation and sweep sources — no
  private feeds. The external source adds real third-party audit/CVE data,
  but only if `scripts/build_external_corpus.py` has been run separately
  (it needs live internet access this script never uses itself).
- **Base-focused.** Reflects the chains VAPE actually operates on.
- **Lesson source is mixed-provenance** — see above; don't treat it as an
  equally rigorous ground truth as investigation/sweep.
- **Not a pretraining corpus.** Suitable for LoRA/instruction-tuning, not
  training a model from scratch.

## Provenance
Regenerated deterministically from `intel/investigations/`, `intel/reports/`,
and `skillforge/memory/lessons.jsonl`. Every row traces to a real, committed
artifact in this repo — nothing here is synthetic.
"""
    with open(os.path.join(OUT_DIR, "DATASET_CARD.md"), "w", encoding="utf-8") as f:
        f.write(card)


def main():
    ap = argparse.ArgumentParser(description="Build VAPE's fine-tune dataset.")
    ap.add_argument("--stats", action="store_true", help="Print counts only; write nothing.")
    args = ap.parse_args()
    build(write=not args.stats)


if __name__ == "__main__":
    main()
