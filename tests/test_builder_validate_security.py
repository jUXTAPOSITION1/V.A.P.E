"""Tests for agents/builder.py's validate_security() — the deterministic
backstop that decides whether Builder-generated code actually gets
returned (generate_code() returns ("", {}) when is_safe is False, so a
BLOCK_PATTERNS match never reaches a caller). No existing coverage for
this function before this file.
"""
from agents.builder import validate_security, BLOCK_PATTERNS


def test_clean_code_is_safe_with_no_warnings():
    code = "def add(a, b):\n    return a + b\n"
    is_safe, warnings = validate_security(code, task="write an adder")
    assert is_safe is True
    assert warnings == []


def test_every_block_pattern_is_individually_caught():
    """Every entry in BLOCK_PATTERNS actually blocks on its own — guards
    against a future edit adding a pattern string that never gets checked,
    or a typo that silently stops matching anything."""
    for pattern in BLOCK_PATTERNS:
        code = f"x = 1\n{pattern}...)\n"
        is_safe, warnings = validate_security(code, task="test")
        assert is_safe is False, f"pattern {pattern!r} did not block"
        assert any(pattern in w for w in warnings)


def test_subprocess_check_output_and_check_call_are_blocked():
    """Regression test for the gap agents/redteam_builder.py's adversarial
    test found: subprocess.call/Popen/run were blocked but check_output and
    check_call — same shell-execution risk family — were not."""
    for call in ("subprocess.check_output(['ls'])", "subprocess.check_call(['ls'])"):
        is_safe, _warnings = validate_security(f"import subprocess\n{call}\n", task="test")
        assert is_safe is False, f"{call!r} should be blocked"


def test_warn_patterns_do_not_block():
    code = "import os\nwith open('f.txt') as f:\n    data = f.read()\n"
    is_safe, warnings = validate_security(code, task="read a file")
    assert is_safe is True
    assert any("review:" in w for w in warnings)


def test_destructive_fs_op_blocked_only_when_task_implies_deletion():
    code = "import shutil\nshutil.rmtree('/tmp/x')\n"
    unsafe, warnings = validate_security(code, task="delete the temp directory")
    assert unsafe is False
    assert any("destructive" in w for w in warnings)

    # Same code, task doesn't mention delete/remove — not flagged by this
    # specific rule (still whatever BLOCK_PATTERNS themselves would catch,
    # but shutil.rmtree isn't in that list on its own).
    safe, _warnings = validate_security(code, task="clean up temp files afterward")
    assert safe is True


def test_getattr_indirection_bypasses_string_matching_known_gap():
    """Documents a real, known limitation rather than hiding it: BLOCK_PATTERNS
    is substring matching, so routing through getattr() to avoid the literal
    substring "eval(" evades detection entirely. This is the class of gap
    agents/redteam_builder.py's daily adversarial test exists to keep
    surfacing (see its docstring) — a proper fix needs AST-based analysis,
    not more string patterns, which is why this is asserted as a known gap
    here rather than "fixed" by trying to pattern-match every variant."""
    code = "getattr(__builtins__, 'ev' + 'al')('1+1')\n"
    is_safe, _warnings = validate_security(code, task="test")
    assert is_safe is True  # known gap — not caught; see docstring above
