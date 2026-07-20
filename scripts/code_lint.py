#!/usr/bin/env python3
"""Deterministic security-pattern scanner for source code.

Sibling to scripts/security_lint.py, which covers .github/workflows/*.yml
only — this one covers the actual Python/TypeScript/JS source, the class of
bug that linter was never scoped to catch. Same design law: pure text/AST
pattern matching on real files, no network, no LLM, deterministic — safe to
run on every PR, and its findings are exactly the kind of thing worth
feeding to an LLM reviewer as grounding rather than making it re-derive them
from scratch (see agents/code_review.py, the caller this was built for).

Checks (the specific bug classes this repo has actually hit before, not a
generic OWASP grab bag):

1. `eval(`/`exec(`/`pickle.loads(` called on anything that isn't a string
   literal — Python AST, not regex, so it can't be fooled by whitespace or
   miss a multi-line call.
2. `subprocess.*`/`os.system(`/`os.popen(` given a shell command built from
   an f-string, `%`-format, `.format(`, or `+` string concatenation instead
   of a literal — the exact shape `agents/*.py`'s own `_run()` helpers
   avoid by always passing a list, never a shell string.
3. A variable named `*_KEY`/`*_SECRET`/`*_TOKEN`/`*_PASSWORD` (case-
   insensitive) assigned a literal string that isn't an obvious placeholder
   (`your_..._here`, `xxx`, `changeme`, empty) — the exact hardcoded-secret
   shape manually grepped for during this repo's 2026-07-19 secrets audit,
   now codified as a standing check instead of a one-off.
4. `.innerHTML =`/`.innerHTML +=` assigned directly from a bare variable
   (not a literal, not a call) in `docs/assets/*.js` or `worker/src/**/*.ts`
   — this repo has an established `_esc()`/`escapeHtml()` convention for
   template-literal interpolation everywhere else; a bare-variable
   assignment bypasses that convention entirely and is the classic vanilla-
   JS DOM-XSS shape.

NOT covered by design: multi-line template-literal interpolation (`` `...
${x}...` ``) is NOT traced here — this repo's own convention already wraps
untrusted values in `_esc(`/`escapeHtml(` at the interpolation site in the
overwhelming majority of real usages, and a per-line regex trying to prove
absence of escaping across a multi-line template would false-positive
constantly. Only the narrow, unambiguous bare-variable-assignment shape is
flagged. A real regression in the template-literal path needs a human (or a
future AST-based JS/TS parser) to notice — same accepted-gap framing
scripts/security_lint.py already uses for its own blind spot.

Usage: python3 scripts/code_lint.py <file_or_dir> [<file_or_dir> ...]
Exit code 0 if clean, 1 if any HIGH/CRITICAL finding (MEDIUM findings are
printed but don't fail the run — same "some things are worth flagging
without blocking" tier security_lint.py's own missing-permissions check
uses).
"""
import ast
import os
import re
import sys

PLACEHOLDER_RE = re.compile(
    r"^\s*$|your_.*_here|changeme|xxx+|placeholder|example|<.*>|\.\.\.$",
    re.IGNORECASE,
)
# "_secret"/"_token"/"_password" are rarely used for anything other than a
# real credential, so matched broadly. "_key" alone is not — cache_key,
# sort_key, primary_key, lookup_key, dict_key, etc. are extremely common,
# entirely non-secret variable names in this codebase (confirmed real false
# positives: agents/data_fetchers.py's/defillama.py's/prediction_markets.py's
# `cache_key="cg_virtual_chart_30d"`-style kwargs) — so a "key"-suffixed name
# only counts here if it's ALSO adjacent to a word that actually suggests a
# credential (api/auth/access/secret/private/bearer/sign/encrypt/session).
SECRET_LITERAL_ASSIGN_RE = re.compile(
    r"""(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:_secret|_token|_password)
        |(?:api|auth|access|secret|private|bearer|sign|encrypt|session)[A-Za-z0-9_]*key
        |key[A-Za-z0-9_]*(?:api|auth|access|secret|private|bearer|sign|encrypt|session))
        \s*[:=]\s*['"](?P<value>[^'"]{16,})['"]""",
    re.IGNORECASE | re.VERBOSE,
)
INNERHTML_BARE_VAR_RE = re.compile(
    r"\.innerHTML\s*\+?=\s*([A-Za-z_$][\w$]*)\s*;"
)
SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx"}


def _iter_source_files(paths):
    for p in paths:
        if os.path.isfile(p):
            if os.path.splitext(p)[1] in SOURCE_EXTS:
                yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in ("node_modules", ".git", "__pycache__", "dist")]
                for f in files:
                    if os.path.splitext(f)[1] in SOURCE_EXTS:
                        yield os.path.join(root, f)


def _is_dynamic_str_node(node):
    """True if an AST node builds a string at runtime rather than being a
    plain literal — f-string, %-format, .format(), or + concatenation."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return False
    if isinstance(node, ast.JoinedStr):  # f-string
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mod, ast.Add)):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return True
    return not isinstance(node, ast.Constant)


def _check_python_ast(path, text, findings):
    try:
        tree = ast.parse(text, filename=path)
    except SyntaxError:
        return  # not valid Python (or a .py file we can't parse) — skip, don't crash the scan
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
        if name in ("eval", "exec") and node.args and _is_dynamic_str_node(node.args[0]):
            findings.append(("HIGH", path, node.lineno,
                              f"{name}() called on a dynamically-built string — "
                              "arbitrary code execution if any part of it is influenced by untrusted input."))
        elif name == "loads" and isinstance(func, ast.Attribute) and _module_name(func.value) == "pickle":
            if node.args and _is_dynamic_str_node(node.args[0]):
                findings.append(("HIGH", path, node.lineno,
                                  "pickle.loads() on a non-literal — insecure deserialization if the "
                                  "bytes came from anything other than this process's own trusted output."))
        elif name in ("system", "popen") and isinstance(func, ast.Attribute) and _module_name(func.value) == "os":
            if node.args and _is_dynamic_str_node(node.args[0]):
                findings.append(("HIGH", path, node.lineno,
                                  f"os.{name}() given a dynamically-built command string — shell injection "
                                  "if any part of it is influenced by untrusted input. Use subprocess with "
                                  "a list of args instead."))
        elif name in ("run", "call", "check_call", "check_output", "Popen"):
            shell_true = any(
                kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords
            )
            if shell_true and node.args and _is_dynamic_str_node(node.args[0]):
                findings.append(("HIGH", path, node.lineno,
                                  f"subprocess.{name}(..., shell=True) given a dynamically-built command "
                                  "string — shell injection risk. Pass a list of args and drop shell=True."))


def _module_name(node):
    return node.id if isinstance(node, ast.Name) else None


def _check_hardcoded_secrets(path, text, findings):
    for lineno, line in enumerate(text.splitlines(), start=1):
        for m in SECRET_LITERAL_ASSIGN_RE.finditer(line):
            value = m.group("value")
            if PLACEHOLDER_RE.search(value):
                continue
            findings.append(("HIGH", path, lineno,
                              f"'{m.group('name')}' assigned a literal string that looks like a real "
                              "secret, not a placeholder — secrets belong in env vars/GitHub secrets/"
                              "wrangler secret put, never committed source."))


def _check_innerhtml(path, text, findings):
    if not path.endswith((".js", ".jsx", ".ts", ".tsx")):
        return
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = INNERHTML_BARE_VAR_RE.search(line)
        if m and m.group(1) not in ("''", '""'):
            findings.append(("MEDIUM", path, lineno,
                              f"innerHTML assigned directly from '{m.group(1)}' — pass it through "
                              "_esc()/escapeHtml() first, or confirm it's already sanitized upstream."))


def lint_text(path, text, findings):
    """Pure function — runs all checks against already-read text, no disk
    I/O. `path` is used only for extension-sniffing and finding messages, so
    this works equally well on a real file or content fetched over the
    network (see agents/code_review.py, which never checks out a PR's code
    locally and fetches each changed file's text via the GitHub API)."""
    if path.endswith(".py"):
        _check_python_ast(path, text, findings)
    _check_hardcoded_secrets(path, text, findings)
    _check_innerhtml(path, text, findings)


def lint_file(path, findings):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        return
    lint_text(path, text, findings)


def run(paths):
    findings = []
    files = list(_iter_source_files(paths))
    for path in files:
        lint_file(path, findings)
    return files, findings


def main():
    paths = sys.argv[1:] or ["."]
    files, findings = run(paths)
    if not findings:
        print(f"code_lint: clean — {len(files)} source file(s) checked, no findings.")
        return 0
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: (severity_order.get(f[0], 9), f[1], f[2]))
    for severity, path, lineno, msg in findings:
        print(f"[{severity}] {os.path.relpath(path)}:{lineno}: {msg}")
    high_or_worse = [f for f in findings if f[0] in ("CRITICAL", "HIGH")]
    print(f"\ncode_lint: {len(findings)} finding(s) across {len(files)} source file(s) "
          f"({len(high_or_worse)} HIGH/CRITICAL).")
    return 1 if high_or_worse else 0


if __name__ == "__main__":
    sys.exit(main())
