#!/usr/bin/env python3
"""
Converts VAPE's fine-tune corpus (data/finetune/vape_finetune.{train,val}.jsonl
— OpenAI-style {"messages": [{"role": "system"|"user"|"assistant", ...}]})
into Vertex AI's supervised-tuning schema for Gemini models:

    {"systemInstruction": {"role": "system", "parts": [{"text": "..."}]},
     "contents": [{"role": "user", "parts": [{"text": "..."}]},
                  {"role": "model", "parts": [{"text": "..."}]}]}

Same real data, same train/val split, same honesty guarantees as the source
file (see scripts/build_finetune_dataset.py) — this is a pure reshape, no new
content and no dropped/added examples. Re-run this after every
build_finetune_dataset.py refresh so the Vertex-format copy never drifts from
the source-of-truth corpus.

Vertex's `contents` array uses "model" (not "assistant") for the model turn —
verify this schema is still current against the "Learn more" link on the
Vertex AI "Create a tuned model" page before a real tuning run; Google has
changed tuning data-format details before and my knowledge may be stale.

Usage:
    python scripts/convert_dataset_vertex.py
    # writes data/finetune/vertex/vape_finetune.{train,val}.vertex.jsonl

Then upload to GCS before creating the tuning job:
    gsutil cp data/finetune/vertex/vape_finetune.train.vertex.jsonl gs://<your-bucket>/vape/
    gsutil cp data/finetune/vertex/vape_finetune.val.vertex.jsonl   gs://<your-bucket>/vape/
"""
import json
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
SRC_DIR = os.path.join(_REPO_ROOT, "data", "finetune")
OUT_DIR = os.path.join(SRC_DIR, "vertex")

_ROLE_MAP = {"user": "user", "assistant": "model"}


def convert_row(row):
    """One OpenAI-style {"messages": [...]} row -> one Vertex tuning row.
    Raises ValueError on a shape this converter doesn't recognize, rather
    than silently emitting a malformed/partial row — a bad conversion here
    would train Gemini on wrong data with no way to notice."""
    messages = row.get("messages")
    if not messages:
        raise ValueError(f"row has no 'messages': {row!r}")

    system_text = None
    contents = []
    for msg in messages:
        role, content = msg.get("role"), msg.get("content")
        if role == "system":
            if system_text is not None:
                raise ValueError("more than one system message in a row")
            system_text = content
        elif role in _ROLE_MAP:
            contents.append({"role": _ROLE_MAP[role], "parts": [{"text": content}]})
        else:
            raise ValueError(f"unrecognized message role: {role!r}")

    if len(contents) != 2 or contents[0]["role"] != "user" or contents[1]["role"] != "model":
        raise ValueError(f"expected exactly one user turn then one model turn, got: {contents!r}")

    out = {"contents": contents}
    if system_text:
        out["systemInstruction"] = {"role": "system", "parts": [{"text": system_text}]}
    return out


def convert_file(src_path, dst_path):
    n_in, n_out = 0, 0
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(src_path, encoding="utf-8") as fin, open(dst_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            n_in += 1
            row = json.loads(line)
            converted = convert_row(row)
            fout.write(json.dumps(converted, ensure_ascii=False) + "\n")
            n_out += 1
    return n_in, n_out


def main():
    pairs = [
        (os.path.join(SRC_DIR, "vape_finetune.train.jsonl"),
         os.path.join(OUT_DIR, "vape_finetune.train.vertex.jsonl")),
        (os.path.join(SRC_DIR, "vape_finetune.val.jsonl"),
         os.path.join(OUT_DIR, "vape_finetune.val.vertex.jsonl")),
    ]
    total_in = 0
    for src, dst in pairs:
        if not os.path.exists(src):
            print(f"[convert_dataset_vertex] missing {os.path.relpath(src, _REPO_ROOT)} "
                  f"— run scripts/build_finetune_dataset.py first", file=sys.stderr)
            sys.exit(1)
        n_in, n_out = convert_file(src, dst)
        assert n_in == n_out  # pure reshape — every row must survive
        total_in += n_in
        print(f"[convert_dataset_vertex] {os.path.relpath(src, _REPO_ROOT)} "
              f"-> {os.path.relpath(dst, _REPO_ROOT)} ({n_out} rows)")
    print(f"[convert_dataset_vertex] {total_in} total rows converted, 0 dropped")


if __name__ == "__main__":
    main()
