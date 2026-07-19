#!/usr/bin/env python3
"""
Builds skillforge/memory/repo_digest.md — a deep, real grounding document for
VAPE's Vertex-tuned candidate specifically (see agents/llm.py's
_call_vertex_tuned(), the only caller of this digest). Every stateless
generateContent call otherwise starts cold with zero awareness of the
current repo; this gives it real architecture docs + a real module-by-module
map instead.

Deterministic, offline, no LLM involved in generating the digest itself —
same discipline as scripts/build_finetune_dataset.py: every line traces to
an actually-committed file, nothing summarized or invented. Four real
sections:

  1. Full text of README.md + every docs/*.md file (the canonical,
     human-maintained architecture description) — included verbatim, not
     re-summarized, so nothing gets lost or distorted in translation.
  2. A real directory tree (bounded depth, noise directories excluded).
  3. Every Python module's own docstring (agents/, skillforge/ minus
     memory/, scripts/, training/), extracted via the `ast` module — never
     re-written, byte-for-byte what the file's own author wrote.
  4. Every worker/src/**/*.ts file's leading comment block, extracted with a
     plain heuristic (no TS parser dependency) — best-effort; a file with no
     leading comment is listed with a "(no header comment)" note rather than
     skipped silently.

Regenerate any time the repo changes meaningfully: `python
scripts/build_repo_digest.py`. Nothing here is time-sensitive or
network-dependent, so this is safe to run in any environment, including this
sandbox.
"""
import ast
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(ROOT, "skillforge", "memory", "repo_digest.md")

DOCS_FILES = ["README.md"] + sorted(
    f"docs/{f}" for f in os.listdir(os.path.join(ROOT, "docs")) if f.endswith(".md")
)

PY_SCAN_DIRS = ["agents", "scripts", "training"]
# skillforge/ itself, but not its memory/ (data files, not code) or its
# vendored tool wrappers under tools/*/node_modules-equivalents.
SKILLFORGE_EXTRA_DIRS = ["skillforge", "skillforge/tools"]

TS_SCAN_DIR = "worker/src"

EXCLUDE_DIR_NAMES = {"__pycache__", "node_modules", "proposals", ".git"}


def _iter_py_files():
    seen = set()
    for base in PY_SCAN_DIRS:
        base_path = os.path.join(ROOT, base)
        if not os.path.isdir(base_path):
            continue
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]
            for f in files:
                if f.endswith(".py"):
                    full = os.path.join(root, f)
                    if full not in seen:
                        seen.add(full)
                        yield full
    for base in SKILLFORGE_EXTRA_DIRS:
        base_path = os.path.join(ROOT, base)
        if not os.path.isdir(base_path):
            continue
        for root, dirs, files in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]
            if base == "skillforge" and os.path.relpath(root, ROOT).startswith("skillforge/memory"):
                continue
            for f in files:
                if f.endswith(".py"):
                    full = os.path.join(root, f)
                    if full not in seen:
                        seen.add(full)
                        yield full


def _module_docstring(path):
    """Real docstring via ast — never a re-written summary. Returns None for
    a file with no module-level docstring (reported as such by the caller,
    not silently dropped)."""
    try:
        with open(path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=path)
        return ast.get_docstring(tree)
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def _ts_leading_comment(path):
    """Best-effort leading comment block for a .ts file — no TS parser
    dependency, just the contiguous run of //-lines or a /* */ block at the
    very top of the file (after a possible shebang/blank lines)."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except (UnicodeDecodeError, OSError):
        return None
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith("/*"):
        block = []
        while i < len(lines):
            block.append(lines[i])
            if "*/" in lines[i]:
                break
            i += 1
        return "".join(block).strip()
    if i < len(lines) and lines[i].lstrip().startswith("//"):
        block = []
        while i < len(lines) and lines[i].lstrip().startswith("//"):
            block.append(lines[i].strip())
            i += 1
        return "\n".join(block)
    return None


def _real_dir_tree(max_depth=2):
    lines = []
    for root, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(root, ROOT)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIR_NAMES and not d.startswith("."))
        if depth >= max_depth:
            dirs[:] = []
        if depth > max_depth:
            continue
        indent = "  " * depth
        label = "." if rel == "." else os.path.basename(root)
        lines.append(f"{indent}{label}/")
        if depth == max_depth:
            continue
        for f in sorted(files):
            if f.startswith("."):
                continue
            lines.append(f"{indent}  {f}")
    return "\n".join(lines)


def build():
    parts = ["# VAPE Repository Digest\n",
             "_Generated by scripts/build_repo_digest.py — real, deterministic, no LLM "
             "involved in producing this file. Fed only to VAPE's Vertex-tuned candidate "
             "(agents/llm.py::_call_vertex_tuned()) as grounding context, not to the "
             "frontier-tier chain._\n"]

    parts.append("## 1. Architecture docs (verbatim)\n")
    for rel in DOCS_FILES:
        full = os.path.join(ROOT, rel)
        if not os.path.exists(full):
            continue
        with open(full, encoding="utf-8") as f:
            content = f.read()
        parts.append(f"### {rel}\n\n{content}\n")

    parts.append("## 2. Directory tree (depth-bounded, noise dirs excluded)\n")
    parts.append(f"```\n{_real_dir_tree()}\n```\n")

    parts.append("## 3. Python module docstrings\n")
    py_files = sorted(_iter_py_files(), key=lambda p: os.path.relpath(p, ROOT))
    for path in py_files:
        rel = os.path.relpath(path, ROOT)
        doc = _module_docstring(path)
        if doc:
            parts.append(f"### {rel}\n\n{doc.strip()}\n")
        else:
            parts.append(f"### {rel}\n\n(no module docstring)\n")

    parts.append("## 4. Worker (TypeScript) file headers\n")
    ts_dir = os.path.join(ROOT, TS_SCAN_DIR)
    if os.path.isdir(ts_dir):
        ts_files = []
        for root, dirs, files in os.walk(ts_dir):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIR_NAMES]
            for f in files:
                if f.endswith(".ts"):
                    ts_files.append(os.path.join(root, f))
        for path in sorted(ts_files, key=lambda p: os.path.relpath(p, ROOT)):
            rel = os.path.relpath(path, ROOT)
            header = _ts_leading_comment(path)
            if header:
                parts.append(f"### {rel}\n\n{header}\n")
            else:
                parts.append(f"### {rel}\n\n(no header comment)\n")

    return "\n".join(parts) + "\n"


def main():
    content = build()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[build_repo_digest] wrote {os.path.relpath(OUT_PATH, ROOT)} "
          f"({len(content)} bytes, ~{len(content) // 4} tokens)")


if __name__ == "__main__":
    main()
