#!/usr/bin/env python3
"""
VAPE fine-tune dataset builder — turns VAPE's own real investigation history
into a chat-format instruction-tuning corpus, so a small open-weight model can
be taught to reason about on-chain risk *the way VAPE already does*.

Why this is a real dataset and not a synthetic one: every example is a real,
already-published investigation from intel/investigations/. The INPUT is the
observable recon VAPE actually gathered (DexScreener market data, GoPlus token
security flags, on-chain presence, contract verification, hack-feed
correlation). The OUTPUT is the verdict VAPE actually reached — and critically,
that verdict + score + rationale come from investigate.py's DETERMINISTIC
score() function, not from an LLM. So this teaches a model to imitate VAPE's
grounded reasoning, not to re-distill some other model's guesses.

This does NOT replace score(). Per this repo's design law (rule-based first,
LLM only when reasoning is required), the deterministic scorer stays the
source of truth. A model fine-tuned on this corpus is a better "fast" tier —
one that writes and reasons like VAPE given real recon — and a candidate the
existing promptfoo/deepteam harness can grade against the frontier tier before
any real traffic is routed to it.

Output (data/finetune/):
  vape_investigations.train.jsonl   OpenAI-style chat messages, ~90%
  vape_investigations.val.jsonl     held-out ~10% (deterministic split)
  DATASET_CARD.md                   provenance, format, stats, honest limits

The split is deterministic (hash of the target address), so re-running yields
byte-identical files — reproducible corpora, same as every other real-data
artifact in this repo.

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
OUT_DIR = os.path.join(ROOT, "data", "finetune")

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
    text = open(path, encoding="utf-8", errors="ignore").read()

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


def _is_val(target):
    """Deterministic ~10% holdout keyed by target address, so re-runs are
    stable and no address ever straddles train/val."""
    h = int(hashlib.sha256(target.encode()).hexdigest(), 16)
    return (h % 100) < int(VAL_FRACTION * 100)


def collect():
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
        examples.append(rec)
    return examples


def _verdict_counts(examples):
    c = {}
    for e in examples:
        c[e["verdict"]] = c.get(e["verdict"], 0) + 1
    return c


def build(write):
    examples = collect()
    train = [e for e in examples if not _is_val(e["target"])]
    val = [e for e in examples if _is_val(e["target"])]

    print(f"parsed {len(examples)} unique investigation example(s)")
    print(f"  verdict mix: {_verdict_counts(examples)}")
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

    _dump("vape_investigations.train.jsonl", train)
    _dump("vape_investigations.val.jsonl", val)
    _write_card(examples, train, val)
    print(f"wrote {OUT_DIR}/vape_investigations.{{train,val}}.jsonl + DATASET_CARD.md")


def _write_card(examples, train, val):
    counts = _verdict_counts(examples)
    card = f"""# VAPE Investigations — fine-tune dataset card

**What:** a chat-format instruction-tuning corpus built from VAPE's own real,
published on-chain investigations (`intel/investigations/investigation-*.md`),
by [`scripts/build_finetune_dataset.py`](../../scripts/build_finetune_dataset.py).

**Each example:**
- **system** — VAPE's investigator framing (real recon only; risk is the
  default posture; absence of red flags is not safety).
- **user** — the observable recon VAPE actually gathered: DexScreener market
  data, GoPlus token-security flags, on-chain presence, contract verification,
  hack-feed correlation. Verbatim, never paraphrased.
- **assistant** — the verdict VAPE actually reached (PROCEED / CAUTION /
  REJECT), its safety score, and the rationale.

**Why the labels are trustworthy:** the verdict, score, and rationale come from
`agents/investigate.py::score()` — a DETERMINISTIC, rule-based function, not an
LLM. This corpus therefore teaches a model to imitate VAPE's grounded reasoning,
not to re-distill another model's output.

## Stats
- Unique examples: **{len(examples)}**
- Verdict mix: {counts}
- Split (deterministic, hashed on target address): **{len(train)} train / {len(val)} val**

## Intended use
Fine-tune a small open-weight instruct model (e.g. Llama-3.1-8B) with LoRA to
serve as a better "fast" tier — one that reasons and writes like VAPE given
real recon. It does **not** replace `score()`; the deterministic scorer stays
the source of truth (this repo's design law). A fine-tuned candidate should be
graded against the frontier tier with the existing `skillforge/tools/ai-redteam`
(promptfoo/deepteam) harness before any real traffic is routed to it.

## Honest limitations
- **Small.** This is a seed corpus that grows for free as VAPE keeps
  investigating — not a finished training set. Re-run this script as the
  investigation ledger grows.
- **On-chain / keyless recon only.** No third-party audit data, no private
  feeds — the model inherits exactly VAPE's real observability, no more.
- **Base-focused.** Reflects the chains VAPE actually operates on.
- **Not a pretraining corpus.** Suitable for LoRA/instruction-tuning, not
  training a model from scratch.

## Provenance
Regenerated deterministically from `intel/investigations/`. Every row traces to
a real, committed investigation report in this repo — nothing here is synthetic.
"""
    with open(os.path.join(OUT_DIR, "DATASET_CARD.md"), "w", encoding="utf-8") as f:
        f.write(card)


def main():
    ap = argparse.ArgumentParser(description="Build VAPE's investigation fine-tune dataset.")
    ap.add_argument("--stats", action="store_true", help="Print counts only; write nothing.")
    args = ap.parse_args()
    build(write=not args.stats)


if __name__ == "__main__":
    main()
