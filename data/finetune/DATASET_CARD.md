# VAPE — fine-tune dataset card

**What:** a chat-format instruction-tuning corpus built from VAPE's own real,
already-committed operating history, by
[`scripts/build_finetune_dataset.py`](../../scripts/build_finetune_dataset.py).
Three sources, each with its own honesty story — see the module docstring for
the full rationale:

- **investigation** (111 examples) —
  `intel/investigations/investigation-*.md`. INPUT is the real recon VAPE
  gathered (DexScreener, GoPlus, on-chain presence, contract verification,
  hack-feed correlation); OUTPUT is the verdict/score/rationale
  `agents/investigate.py::score()` actually produced — a DETERMINISTIC,
  rule-based function, not an LLM. The strongest signal in this corpus.
- **sweep** (140 examples) —
  `intel/reports/{security,base,virtuals,sentiment,macro}-*.md`. Same
  discipline across every domain VAPE covers. OUTPUT is ONLY each report's
  deterministic verdict heading + its immediate rule-based explanation — the
  LLM-written narrative sections further down each report are deliberately
  excluded from training.
- **lesson** (23 examples) —
  `skillforge/memory/lessons.jsonl`, VAPE's own logged operational history
  (self-improve builds, PR review outcomes, expert-assessment disagreements).
  Honesty note: this source is a MIX of deterministic outcomes and prior LLM
  commentary — included because the user wants VAPE to learn from its own
  operating history, not because every row here is as rock-solid as the two
  sources above.

**Why most of the labels are trustworthy:** investigation and sweep outputs
come from this repo's own deterministic scoring functions, never an LLM. This
corpus teaches a model to imitate VAPE's grounded reasoning, not to re-distill
another model's guesses — with the lesson source's mixed provenance called
out plainly rather than hidden.

## Stats
- Total examples: **274** — {'investigation': 111, 'sweep': 140, 'lesson': 23}
- Investigation verdict mix: {'CAUTION': 27, 'PROCEED': 36, 'REJECT': 48}
- Split (deterministic, hashed per-example key): **240 train / 34 val**

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
  third-party audit data, no private feeds.
- **Base-focused.** Reflects the chains VAPE actually operates on.
- **Lesson source is mixed-provenance** — see above; don't treat it as an
  equally rigorous ground truth as investigation/sweep.
- **Not a pretraining corpus.** Suitable for LoRA/instruction-tuning, not
  training a model from scratch.

## Provenance
Regenerated deterministically from `intel/investigations/`, `intel/reports/`,
and `skillforge/memory/lessons.jsonl`. Every row traces to a real, committed
artifact in this repo — nothing here is synthetic.
