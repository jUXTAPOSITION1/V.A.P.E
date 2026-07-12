# VAPE Investigations — fine-tune dataset card

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
- Unique examples: **42**
- Verdict mix: {'CAUTION': 9, 'PROCEED': 16, 'REJECT': 17}
- Split (deterministic, hashed on target address): **38 train / 4 val**

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
