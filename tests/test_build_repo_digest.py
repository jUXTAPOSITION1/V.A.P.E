"""Tests for scripts/build_repo_digest.py's pure extraction helpers — the
Vertex candidate's only real repo-grounding source (agents/llm.py's
_load_repo_digest()), so a fabricated or silently-wrong extraction here
would feed the candidate false context. _module_docstring/_ts_leading_comment
are tested against tmp_path fixtures rather than real repo files, so these
never depend on (or break from) the repo's own current file contents; build()
itself is smoke-tested once against the real repo, matching what actually
ships.
"""
import importlib.util
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "build_repo_digest", os.path.join(ROOT, "scripts", "build_repo_digest.py"))
brd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(brd)


def test_module_docstring_extracts_real_docstring(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text('"""A real module docstring."""\nimport os\n')
    assert brd._module_docstring(str(f)) == "A real module docstring."


def test_module_docstring_returns_none_when_absent(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text("import os\nx = 1\n")
    assert brd._module_docstring(str(f)) is None


def test_module_docstring_returns_none_on_syntax_error(tmp_path):
    f = tmp_path / "broken.py"
    f.write_text("def f(:\n    pass\n")
    assert brd._module_docstring(str(f)) is None


def test_ts_leading_comment_extracts_block_comment(tmp_path):
    f = tmp_path / "mod.ts"
    f.write_text("/**\n * Real header.\n */\nexport const x = 1;\n")
    result = brd._ts_leading_comment(str(f))
    assert "Real header." in result


def test_ts_leading_comment_extracts_line_comments(tmp_path):
    f = tmp_path / "mod.ts"
    f.write_text("// Line one\n// Line two\nexport const x = 1;\n")
    result = brd._ts_leading_comment(str(f))
    assert "Line one" in result and "Line two" in result


def test_ts_leading_comment_returns_none_when_absent(tmp_path):
    f = tmp_path / "mod.ts"
    f.write_text("export const x = 1;\n")
    assert brd._ts_leading_comment(str(f)) is None


def test_ts_leading_comment_skips_leading_blank_lines(tmp_path):
    f = tmp_path / "mod.ts"
    f.write_text("\n\n// Real header\nexport const x = 1;\n")
    result = brd._ts_leading_comment(str(f))
    assert "Real header" in result


def test_build_produces_real_structured_digest():
    """Smoke test against the actual repo (this script always targets its
    own repo, not an arbitrary path) — confirms every real section is
    present and non-trivial, without pinning exact content that would make
    this test brittle against ordinary repo changes."""
    content = brd.build()
    assert content.startswith("# VAPE Repository Digest")
    assert "## 1. Architecture docs (verbatim)" in content
    assert "## 2. Directory tree" in content
    assert "## 3. Python module docstrings" in content
    assert "## 4. Worker (TypeScript) file headers" in content
    assert "### README.md" in content
    assert "### agents/llm.py" in content
    assert len(content) > 50_000  # a real, deep digest, not a stub
