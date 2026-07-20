"""Tests for scripts/code_lint.py — the deterministic security-pattern
scanner for source code. Pure text/AST matching, no network, so these run
directly against in-memory fixtures via lint_text() rather than real files.
"""
import scripts.code_lint as cl


def _lint(path, text):
    findings = []
    cl.lint_text(path, text, findings)
    return findings


def test_eval_on_fstring_flagged():
    findings = _lint("x.py", "x = 1\neval(f'do({x})')\n")
    assert any(sev == "HIGH" and "eval" in msg for sev, _, _, msg in findings)


def test_eval_on_literal_not_flagged():
    findings = _lint("x.py", "eval('1 + 1')\n")
    assert findings == []


def test_exec_on_concat_flagged():
    findings = _lint("x.py", "cmd = 'a'\nexec('x = ' + cmd)\n")
    assert any("exec" in msg for _, _, _, msg in findings)


def test_pickle_loads_on_variable_flagged():
    findings = _lint("x.py", "import pickle\ndata = get_bytes()\npickle.loads(data)\n")
    assert any("pickle" in msg for _, _, _, msg in findings)


def test_pickle_loads_on_literal_not_flagged():
    findings = _lint("x.py", "import pickle\npickle.loads(b'\\x80\\x03.')\n")
    assert findings == []


def test_os_system_dynamic_flagged():
    findings = _lint("x.py", "import os\nu = 'x'\nos.system('ls ' + u)\n")
    assert any(sev == "HIGH" and "os.system" in msg for sev, _, _, msg in findings)


def test_os_system_literal_not_flagged():
    findings = _lint("x.py", "import os\nos.system('ls -la')\n")
    assert findings == []


def test_subprocess_shell_true_dynamic_flagged():
    findings = _lint("x.py", "import subprocess\nu='x'\nsubprocess.run('echo ' + u, shell=True)\n")
    assert any("shell=True" in msg for _, _, _, msg in findings)


def test_subprocess_list_args_not_flagged():
    findings = _lint("x.py", "import subprocess\nu='x'\nsubprocess.run(['echo', u])\n")
    assert findings == []


def test_subprocess_shell_true_on_literal_not_flagged():
    findings = _lint("x.py", "import subprocess\nsubprocess.run('echo hi', shell=True)\n")
    assert findings == []


def test_hardcoded_api_key_flagged():
    findings = _lint("x.py", 'API_KEY = "sk-abcdEFGH12345678reallookingsecret"\n')
    assert any(sev == "HIGH" and "API_KEY" in msg for sev, _, _, msg in findings)


def test_placeholder_key_not_flagged():
    findings = _lint("x.py", 'API_KEY = "your_api_key_here"\n')
    assert findings == []


def test_short_token_not_flagged():
    findings = _lint("x.py", 'SESSION_TOKEN = "short"\n')
    assert findings == []


def test_cache_key_kwarg_not_flagged():
    # Regression test: confirmed real false positive found scanning this
    # repo's own agents/data_fetchers.py/defillama.py/prediction_markets.py
    # before this exclusion was added — `cache_key="..."` is a cache
    # identifier, not a credential, despite ending in "_key".
    findings = _lint("x.py", 'fetch(url, ttl=3600, cache_key="cg_virtual_chart_30d_series")\n')
    assert findings == []


def test_sort_key_and_primary_key_not_flagged():
    findings = _lint("x.py", 'sort_key = "created_at_descending_order"\n'
                             'primary_key = "user_id_composite_index"\n')
    assert findings == []


def test_real_api_key_variant_names_flagged():
    # The reported name is the matched credential-shaped substring
    # (ACCESS_KEY), not necessarily the full identifier with its prefix —
    # still enough to identify and act on given the file:line it's paired with.
    findings = _lint("x.py", 'AWS_ACCESS_KEY = "AKIA1234567890ABCDEF1234"\n')
    assert any("ACCESS_KEY" in msg for _, _, _, msg in findings)


def test_innerhtml_bare_variable_flagged():
    findings = _lint("x.js", "el.innerHTML = userContent;\n")
    assert any(sev == "MEDIUM" and "innerHTML" in msg for sev, _, _, msg in findings)


def test_innerhtml_plus_equals_bare_variable_flagged():
    findings = _lint("x.ts", "el.innerHTML += chunk;\n")
    assert any("innerHTML" in msg for _, _, _, msg in findings)


def test_innerhtml_empty_string_not_flagged():
    findings = _lint("x.js", "el.innerHTML = '';\n")
    assert findings == []


def test_innerhtml_escaped_template_not_flagged():
    findings = _lint("x.js", "el.innerHTML = `<span>${this._esc(name)}</span>`;\n")
    assert findings == []


def test_innerhtml_check_skipped_for_python_files():
    findings = _lint("x.py", "el.innerHTML = userContent\n")  # not valid Python anyway, but check is JS/TS-only
    assert findings == []


def test_run_returns_files_and_findings(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("eval(input())\n")
    good = tmp_path / "good.py"
    good.write_text("print('hi')\n")
    files, findings = cl.run([str(tmp_path)])
    assert len(files) == 2
    assert any("eval" in msg for _, _, _, msg in findings)


def test_main_exit_code_clean(tmp_path, capsys):
    (tmp_path / "clean.py").write_text("print('hi')\n")
    import sys
    old_argv = sys.argv
    sys.argv = ["code_lint.py", str(tmp_path)]
    try:
        assert cl.main() == 0
    finally:
        sys.argv = old_argv


def test_main_exit_code_dirty(tmp_path):
    (tmp_path / "bad.py").write_text("eval(input())\n")
    import sys
    old_argv = sys.argv
    sys.argv = ["code_lint.py", str(tmp_path)]
    try:
        assert cl.main() == 1
    finally:
        sys.argv = old_argv
