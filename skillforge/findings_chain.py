#!/usr/bin/env python3
"""
Tamper-evidence for skillforge/memory/findings.jsonl — VAPE's published
security findings/coverage-gaps/self-review results, read by
self_improve.py to decide what to act on and surfaced in intel reports.
Nothing in this repo currently detects if a line in that file were edited
or deleted after the fact (a compromised CI credential, a bug in a writer,
or a deliberate cover-up would all look identical: the file just has
different content next time anyone reads it).

Design deliberately does NOT touch how findings get written — six+ call
sites across agents/redteam.py, skillforge/harvest.py, the ai-redteam
tools, agents/llm.py, and skillforge/memory/retriever.py's shared
append_to_memory() all append lines their own way today, and making tamper
evidence meaningful there would mean migrating every one of them onto a
single write path, a much larger and riskier refactor than this repo's
current gap actually calls for. Instead this treats findings.jsonl as an
opaque append-only text file and periodically "seals" it: each seal
records a hash over every line added since the previous seal, chained to
that seal's own hash, in a separate append-only log
(findings.chain.jsonl). Verifying replays that same hash over the FILE'S
CURRENT content at each previously-sealed line range — any edit or
deletion inside an already-sealed range changes what gets rehashed there,
which no longer matches the recorded hash. Lines added since the last seal
aren't covered yet (same "outside the chain until sealed" idea as legacy
pre-migration rows in VAPOR's PaymentRecord chain) — that's why sealing
needs to run on a schedule (see .github/workflows/findings-seal.yml), not
just once.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = os.path.join(ROOT, "skillforge", "memory")
FINDINGS_PATH = os.path.join(MEM, "findings.jsonl")
CHAIN_PATH = os.path.join(MEM, "findings.chain.jsonl")

GENESIS_HASH = "GENESIS"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_lines(path):
    """Raw lines (content, not parsed JSON) — sealing/verifying works over
    the file's literal bytes, not its schema, so this stays valid even as
    individual finding dicts' shape evolves over time."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return f.readlines()


def _read_chain():
    """Every seal recorded so far, in order. A malformed/missing chain log
    is treated as "no seals yet" — the safest failure mode (verify simply
    has nothing to check, rather than raising and blocking whatever called
    it)."""
    if not os.path.exists(CHAIN_PATH):
        return []
    seals = []
    with open(CHAIN_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                seals.append(json.loads(line))
            except ValueError:
                continue
    return seals


def _segment_hash(prev_hash, lines):
    h = hashlib.sha256()
    h.update(prev_hash.encode())
    for line in lines:
        h.update(line.encode())
    return h.hexdigest()


def seal():
    """Hashes every findings.jsonl line added since the last seal and
    appends one new entry to findings.chain.jsonl. A no-op (not an error)
    when nothing new has been written since the last seal — running this
    on a fixed schedule regardless of whether findings changed is fine."""
    lines = _read_lines(FINDINGS_PATH)
    seals = _read_chain()
    sealed_through = seals[-1]["sealed_through_line"] if seals else 0
    prev_hash = seals[-1]["chain_hash"] if seals else GENESIS_HASH

    if len(lines) <= sealed_through:
        if len(lines) < sealed_through:
            print(
                f"[findings_chain] WARNING: findings.jsonl has {len(lines)} lines but "
                f"the last seal covers {sealed_through} — lines were removed since "
                f"the last seal. Run `verify` for details before sealing over this.",
                file=sys.stderr,
            )
        return None

    new_lines = lines[sealed_through:]
    new_hash = _segment_hash(prev_hash, new_lines)
    entry = {
        "ts": _now(),
        "sealed_through_line": len(lines),
        "new_lines_sealed": len(new_lines),
        "chain_hash": new_hash,
    }
    os.makedirs(MEM, exist_ok=True)
    with open(CHAIN_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def verify():
    """Re-derives every seal's hash from findings.jsonl's CURRENT content
    and compares against what was recorded at seal time. Returns a dict:
    ok, seals_checked, lines_covered, unsealed_lines, and (on failure)
    broken_at_seal/reason. Never raises — an unreadable findings.jsonl or
    chain log is itself reported as a failure, not an exception a caller
    has to handle specially."""
    try:
        lines = _read_lines(FINDINGS_PATH)
    except OSError as e:
        return {"ok": False, "reason": f"could not read findings.jsonl: {e}"}
    seals = _read_chain()

    if not seals:
        return {"ok": True, "seals_checked": 0, "lines_covered": 0, "unsealed_lines": len(lines)}

    prev_hash = GENESIS_HASH
    prev_through = 0
    for i, seal_entry in enumerate(seals):
        through = seal_entry.get("sealed_through_line")
        recorded_hash = seal_entry.get("chain_hash")
        if through is None or recorded_hash is None:
            return {"ok": False, "seals_checked": i, "broken_at_seal": i,
                     "reason": "malformed chain entry (missing sealed_through_line/chain_hash)"}
        if len(lines) < through:
            return {
                "ok": False, "seals_checked": i, "broken_at_seal": i,
                "reason": (
                    f"findings.jsonl has only {len(lines)} lines but seal #{i} "
                    f"({seal_entry.get('ts')}) covers {through} — lines were deleted "
                    f"after this seal."
                ),
            }
        segment = lines[prev_through:through]
        actual_hash = _segment_hash(prev_hash, segment)
        if actual_hash != recorded_hash:
            return {
                "ok": False, "seals_checked": i, "broken_at_seal": i,
                "reason": (
                    f"seal #{i} ({seal_entry.get('ts')}, lines {prev_through}-{through}) "
                    f"hash mismatch — content in that range was altered after sealing."
                ),
            }
        prev_hash = recorded_hash
        prev_through = through

    return {
        "ok": True,
        "seals_checked": len(seals),
        "lines_covered": prev_through,
        "unsealed_lines": len(lines) - prev_through,
    }


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seal"
    if cmd == "seal":
        result = seal()
        if result is None:
            print("[findings_chain] nothing new to seal")
        else:
            print(f"[findings_chain] sealed through line {result['sealed_through_line']} "
                  f"({result['new_lines_sealed']} new line(s)) -> {result['chain_hash'][:16]}...")
    elif cmd == "verify":
        result = verify()
        print(json.dumps(result, indent=2))
        if not result["ok"]:
            sys.exit(1)
    else:
        print(f"usage: {sys.argv[0]} [seal|verify]", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
