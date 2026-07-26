#!/usr/bin/env python3
"""A git merge driver for VAPE's JSON state blobs (see .gitattributes).

These files — skillforge/memory/anomaly_state.json, *_quota.json — are flat
objects keyed by observation, written independently by concurrent scheduled
workflows. Two runs that touch different keys still produce a textual conflict,
which halts a rebase mid-flight and strands the runner on a detached HEAD (the
2026-07-26 bounty-cycle failure). They can't use git's built-in `union` driver
the way the append-only .jsonl ledgers do: concatenating two JSON objects
yields syntactically invalid JSON.

So merge them the way they're actually meant to combine — per key:

  * key only on one side          -> keep it (neither side deleted it; they
                                     simply observed different things)
  * key on both sides, same value -> keep it
  * key on both sides, different  -> keep whichever carries the newer "ts",
                                     because that is exactly the last-write-
                                     wins semantics the writers assume
  * no usable "ts" to compare     -> keep the local ("ours") value, since the
                                     run performing the merge just computed it

Deletions are intentionally NOT propagated. Reviving a key that one side pruned
costs at most one duplicate anomaly alert; dropping a key that the other side
still needs would suppress a real one. For state whose whole job is "have I
already reported this?", over-reporting is the safe direction to fail.

Git invokes a merge driver as:  driver %O %A %B
  %O  ancestor version   %A  ours (also the OUTPUT path)   %B  theirs
Exit 0 = merged cleanly, non-zero = conflict. On any parse failure this exits
non-zero and leaves %A untouched, so a malformed file degrades to a normal
git conflict rather than being silently overwritten.
"""
import json
import sys


def _load(path):
    """Parse `path` as a JSON object, or return None if it isn't one."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read().strip()
    except OSError:
        return None
    if not text:
        return {}
    try:
        value = json.loads(text)
    except (ValueError, UnicodeDecodeError):
        return None
    # Only flat objects have per-key merge semantics; a list or scalar does not.
    return value if isinstance(value, dict) else None


def _timestamp(value):
    """The comparable "ts" of a state entry, or None when there isn't one.

    Timestamps here are ISO-8601 UTC ("2026-07-26T01:09:10Z"), which sort
    correctly as plain strings, so no date parsing (or its failure modes) is
    needed.
    """
    if isinstance(value, dict):
        ts = value.get("ts")
        if isinstance(ts, str) and ts:
            return ts
    return None


def merge_states(base, ours, theirs):
    """Merge two JSON state dicts. `base` is advisory only — see module docs."""
    merged = dict(ours)
    for key, their_value in theirs.items():
        if key not in merged:
            merged[key] = their_value
            continue
        our_value = merged[key]
        if our_value == their_value:
            continue
        our_ts, their_ts = _timestamp(our_value), _timestamp(their_value)
        if their_ts is not None and (our_ts is None or their_ts > our_ts):
            merged[key] = their_value
        # else: keep ours — newer, or nothing to compare on.
    return merged


def main(argv):
    if len(argv) != 4:
        print(f"usage: {argv[0]} <ancestor> <ours> <theirs>", file=sys.stderr)
        return 2
    ancestor_path, ours_path, theirs_path = argv[1], argv[2], argv[3]

    ours, theirs = _load(ours_path), _load(theirs_path)
    if ours is None or theirs is None:
        print("[merge-json-state] not a flat JSON object on both sides — "
              "leaving this to a normal git conflict", file=sys.stderr)
        return 1

    merged = merge_states(_load(ancestor_path) or {}, ours, theirs)
    try:
        # %A is git's output path. Match the writers' formatting (2-space
        # indent, sorted keys) so the merge doesn't churn the whole file.
        with open(ours_path, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=2, sort_keys=True)
            fh.write("\n")
    except OSError as exc:
        print(f"[merge-json-state] could not write {ours_path}: {exc}", file=sys.stderr)
        return 1
    print(f"[merge-json-state] merged {len(merged)} key(s) in {ours_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
