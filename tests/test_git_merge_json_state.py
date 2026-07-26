"""Tests for scripts/git_merge_json_state.py — the git merge driver that keeps
concurrent scheduled workflows from conflicting on JSON state blobs.

Why this matters: on 2026-07-26 a completed bounty cycle was thrown away
because two overlapping runs each wrote skillforge/memory/anomaly_state.json,
`git pull --rebase` conflicted, and the runner was left on a detached HEAD.
These cover the merge semantics that fix it, plus the degrade-safely paths —
a bad merge here would silently corrupt state rather than fail loudly.
"""
import importlib.util
import json
import os

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "git_merge_json_state",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "git_merge_json_state.py"),
)
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


def _entry(ts, value):
    return {"ts": ts, "value": value}


def test_disjoint_keys_are_both_kept():
    """The common case: two runs observed different movers. Neither side is
    wrong, so the merge is the union."""
    ours = {"a": _entry("2026-01-01T00:00:00Z", 1)}
    theirs = {"b": _entry("2026-01-02T00:00:00Z", 2)}
    assert mod.merge_states({}, ours, theirs) == {**ours, **theirs}


def test_same_key_newer_timestamp_wins_regardless_of_side():
    """Last-write-wins per key is what the writers assume, so the winner must
    depend on `ts` alone — not on which side happens to be 'ours'."""
    older, newer = _entry("2026-01-01T00:00:00Z", 1), _entry("2026-05-05T00:00:00Z", 9)
    assert mod.merge_states({}, {"k": older}, {"k": newer})["k"] == newer
    assert mod.merge_states({}, {"k": newer}, {"k": older})["k"] == newer


def test_identical_values_are_not_duplicated_or_altered():
    same = _entry("2026-01-01T00:00:00Z", 1)
    assert mod.merge_states({}, {"k": same}, {"k": same}) == {"k": same}


def test_untimestamped_conflict_keeps_ours():
    """With no `ts` to compare, prefer the value the merging run just computed
    rather than picking arbitrarily."""
    assert mod.merge_states({}, {"k": "ours"}, {"k": "theirs"})["k"] == "ours"
    # A ts on only one side is still a usable signal: that side wins.
    ts_only = _entry("2026-09-09T00:00:00Z", 5)
    assert mod.merge_states({}, {"k": "ours"}, {"k": ts_only})["k"] == ts_only


def test_deletions_are_not_propagated():
    """Reviving a pruned key costs one duplicate alert; dropping a live key
    suppresses a real one. Fail toward over-reporting."""
    base = {"gone": _entry("2026-01-01T00:00:00Z", 1)}
    merged = mod.merge_states(base, {}, base)
    assert "gone" in merged


def test_end_to_end_driver_writes_merged_file(tmp_path):
    """Exercise main() exactly as git invokes it: driver %O %A %B, with %A
    doubling as the output path."""
    base, ours, theirs = (tmp_path / n for n in ("base.json", "ours.json", "theirs.json"))
    base.write_text("{}")
    ours.write_text(json.dumps({"a": _entry("2026-01-01T00:00:00Z", 1)}))
    theirs.write_text(json.dumps({"b": _entry("2026-02-02T00:00:00Z", 2)}))

    assert mod.main(["driver", str(base), str(ours), str(theirs)]) == 0
    written = json.loads(ours.read_text())
    assert set(written) == {"a", "b"}
    assert ours.read_text().endswith("\n")


@pytest.mark.parametrize("bad", ["not json at all", "[1, 2, 3]", '"a string"'])
def test_non_object_input_degrades_to_a_real_conflict(tmp_path, bad):
    """Anything that isn't a flat object has no per-key semantics. Exit
    non-zero so git raises a normal conflict instead of us guessing."""
    base, ours, theirs = (tmp_path / n for n in ("base.json", "ours.json", "theirs.json"))
    base.write_text("{}")
    ours.write_text(bad)
    theirs.write_text(json.dumps({"b": 1}))
    original = ours.read_text()

    assert mod.main(["driver", str(base), str(ours), str(theirs)]) != 0
    assert ours.read_text() == original, "must not overwrite on failure"


def test_empty_file_is_treated_as_empty_state(tmp_path):
    """A freshly-created ledger is legitimately empty; that isn't corruption."""
    base, ours, theirs = (tmp_path / n for n in ("base.json", "ours.json", "theirs.json"))
    base.write_text("")
    ours.write_text("")
    theirs.write_text(json.dumps({"b": _entry("2026-02-02T00:00:00Z", 2)}))
    assert mod.main(["driver", str(base), str(ours), str(theirs)]) == 0
    assert set(json.loads(ours.read_text())) == {"b"}


def test_wrong_argument_count_is_rejected():
    assert mod.main(["driver", "only-one"]) == 2
