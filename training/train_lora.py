#!/usr/bin/env python3
"""
VAPE model training — QLoRA fine-tune of a Gemma checkpoint on VAPE's own
real operating-history corpus (data/finetune/vape_finetune.{train,val}.jsonl,
built by scripts/build_finetune_dataset.py).

Deliberately plain `transformers` + `peft` + `bitsandbytes`, not `trl`'s
SFTTrainer — that API has shifted across versions historically and this repo
would rather depend on `transformers.Trainer`, which has been stable for
years, than risk the script breaking on whatever trl version happens to be
current when this actually runs. If Unsloth is available and still supports
Gemma at execution time, it's a legitimate faster/lighter alternative for
this exact job (single-GPU LoRA on a budget) — worth trying, but not
depended on here for the same version-drift reason.

Runs on the self-hosted GitHub Actions runner (the GPU box) via
.github/workflows/train-vape-model.yml.

Verify the base model id against Hugging Face's Gemma org page before
running — do not assume the --base-model default below is still the
current/best Gemma checkpoint; it's a placeholder for "a mid-size (~4B-12B
class) instruct checkpoint", not a hardcoded recommendation past today.

Usage:
  python training/train_lora.py \
      --base-model google/gemma-3-4b-it \
      --train-file data/finetune/vape_finetune.train.jsonl \
      --val-file data/finetune/vape_finetune.val.jsonl \
      --output-dir training/out/vape-gemma-lora \
      --epochs 3

Requires HF_TOKEN in the environment if the chosen checkpoint is gated
(accept its license on huggingface.co first) — see training/setup_runner.sh.
"""
import argparse
import json
import os
import sys


def _load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_example(tokenizer, messages, max_seq_len):
    """Tokenize one chat example with the assistant turn as the ONLY part
    that contributes to the loss — the system+user portion is present (the
    model must condition on it) but masked to -100 in labels, otherwise the
    model would also be trained to "predict" its own real input data, which
    teaches nothing and wastes capacity."""
    prompt_messages = messages[:-1]
    assert messages[-1]["role"] == "assistant", "last message must be the assistant turn"

    prompt_text = tokenizer.apply_chat_template(
        prompt_messages, tokenize=False, add_generation_prompt=True)
    full_text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=False)

    prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
    full = tokenizer(full_text, add_special_tokens=False, truncation=True,
                      max_length=max_seq_len)
    input_ids = full["input_ids"]
    attention_mask = full["attention_mask"]

    labels = list(input_ids)
    mask_len = min(len(prompt_ids), len(labels))
    for i in range(mask_len):
        labels[i] = -100

    return {"input_ids": input_ids, "attention_mask": attention_mask, "labels": labels}


def main():
    ap = argparse.ArgumentParser(description="QLoRA fine-tune a Gemma checkpoint on VAPE's real corpus.")
    ap.add_argument("--base-model", default="google/gemma-3-4b-it",
                     help="HF model id — VERIFY this is still the right Gemma checkpoint before running.")
    ap.add_argument("--train-file", default="data/finetune/vape_finetune.train.jsonl")
    ap.add_argument("--val-file", default="data/finetune/vape_finetune.val.jsonl")
    ap.add_argument("--output-dir", default="training/out/vape-gemma-lora")
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--lora-dropout", type=float, default=0.05)
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--batch-size", type=int, default=1,
                     help="Per-device batch size — keep small on a single budget GPU; use --grad-accum to raise the effective batch size instead.")
    ap.add_argument("--grad-accum", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--no-4bit", action="store_true",
                     help="Disable 4-bit QLoRA quantization (full/half-precision LoRA instead) — only if VRAM allows.")
    ap.add_argument("--merge", action="store_true",
                     help="After training, also save a merged full-precision model (needed for GGUF export) alongside the adapter.")
    args = ap.parse_args()

    # Imported here, not at module top, so --help works even before these
    # (large, GPU-box-only) dependencies are installed.
    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
        DataCollatorForSeq2Seq, Trainer, TrainingArguments,
    )
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if not torch.cuda.is_available():
        print("::error::No CUDA GPU visible. This script needs the GPU box's self-hosted "
              "runner, not the default GitHub-hosted runner — check the workflow's "
              "runs-on label.", file=sys.stderr)
        sys.exit(1)

    hf_token = os.environ.get("HF_TOKEN")

    train_rows = _load_jsonl(args.train_file)
    val_rows = _load_jsonl(args.val_file) if os.path.exists(args.val_file) else []
    print(f"[train_lora] real dataset: {len(train_rows)} train, {len(val_rows)} val "
          f"(from {args.train_file} / {args.val_file})")
    if not train_rows:
        print("::error::Empty training set — run scripts/build_finetune_dataset.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"[train_lora] loading base model {args.base_model} "
          f"({'4-bit QLoRA' if not args.no_4bit else 'no quantization'})")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, token=hf_token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = None
    if not args.no_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=quant_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )
    if quant_config is not None:
        model = prepare_model_for_kbit_training(model)
    model.gradient_checkpointing_enable()

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        # Standard attention+MLP projection targets for Gemma-family models
        # (Llama-style naming) — if the chosen checkpoint uses different
        # module names, peft raises a clear error naming what it found
        # instead of silently no-op'ing, so this is safe to leave as a
        # sensible default rather than something that fails quietly.
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("[train_lora] tokenizing real examples (assistant-only loss masking)...")
    train_ds = Dataset.from_list([
        build_example(tokenizer, r["messages"], args.max_seq_len) for r in train_rows
    ])
    val_ds = Dataset.from_list([
        build_example(tokenizer, r["messages"], args.max_seq_len) for r in val_rows
    ]) if val_rows else None

    collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True, label_pad_token_id=-100)

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        bf16=True,
        logging_steps=5,
        save_strategy="epoch",
        eval_strategy="epoch" if val_ds is not None else "no",
        save_total_limit=2,
        report_to="none",  # no wandb/tensorboard dependency required
        gradient_checkpointing=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
    )

    print("[train_lora] starting training...")
    result = trainer.train()
    print(f"[train_lora] final train loss: {result.training_loss:.4f}")
    if val_ds is not None:
        metrics = trainer.evaluate()
        print(f"[train_lora] final eval metrics: {metrics}")

    adapter_dir = os.path.join(args.output_dir, "adapter")
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    print(f"[train_lora] saved LoRA adapter to {adapter_dir}")

    if args.merge:
        print("[train_lora] merging adapter into base weights for GGUF export...")
        merged = model.merge_and_unload()
        merged_dir = os.path.join(args.output_dir, "merged")
        merged.save_pretrained(merged_dir)
        tokenizer.save_pretrained(merged_dir)
        print(f"[train_lora] saved merged full model to {merged_dir}")


if __name__ == "__main__":
    main()
