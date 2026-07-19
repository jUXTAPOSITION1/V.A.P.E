#!/usr/bin/env python3
"""
HACK SWEEP — VAPE's daily proactive full-tool-coverage vulnerability sweep
across real Base/EVM targets, running for free against VAPE's own initiative
(not a paid engagement).

This is an escalation pipeline, not a fresh discovery mechanism:
agents/investigate.py's existing hourly auto-cycle (auto_target()) already
does real keyless recon + scoring across every EVM_CHAINS network and
records a verdict in its own ledger (agents/investigate.py::LEDGER_PATH) for
every target it touches. This sweep reuses that same real ledger as its
candidate pool and promotes a small number of the most interesting-looking
entries — CAUTION verdicts specifically: REJECT ones are already
conclusively bad under the free pass, PROCEED ones already look clean, but
CAUTION is exactly where a deeper, multi-tool pass earns its keep — to
VAPE's heaviest analysis: agents/deep_dive_audit.py's full tool suite
(GoPlus + DexScreener + on-chain recon + Etherscan source + Slither +
Halmos + Mythril + Aderyn + OCI Grok 4.3 frontier reasoning), the exact same
pipeline paying x402/ACP buyers get for the $50 bounty_deep_dive offering,
run here with engagement="sweep" so the resulting report honestly reads as
a proactive sweep rather than a paid job.

Keeps its own dedup state (skillforge/memory/hack_sweep_state.json) —
separate from investigate.py's ledger, since "already free-investigated"
and "already got the full heavy tool-suite deep dive" are different facts
about the same address. Real, not fabricated: never invents a target
address; skips cleanly (does nothing) if the ledger has no fresh
CAUTION-flagged candidate this cycle.

Logs a summary finding to skillforge/memory/findings.jsonl per address
swept — VAPE's memory review of its own daily proactive hunt, the same
convention agents/hack_agent.py already established for per-incident
threat writeups.
"""
import json
import os
import sys
from datetime import datetime, timezone

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from agents import investigate as inv
    from agents import deep_dive_audit as dda
except Exception:
    import investigate as inv
    import deep_dive_audit as dda

STATE_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "hack_sweep_state.json")
FINDINGS_PATH = os.path.join(_REPO_ROOT, "skillforge", "memory", "findings.jsonl")
MAX_TARGETS_PER_RUN = 3  # bounded: each deep dive is a real multi-tool + frontier-LLM pass, not cheap


def _load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def _select_candidates(limit=MAX_TARGETS_PER_RUN):
    """Real candidates only, sourced from investigate.py's own ledger — never
    invents a target. Never-swept candidates (empty last-swept timestamp)
    sort first; among already-swept ones, oldest-swept-first, so the same
    handful of addresses don't get re-picked every single day."""
    state = _load_state()
    ledger = inv._load_ledger()
    candidates = []
    for key, entry in ledger.items():
        if entry.get("last_verdict") != "CAUTION":
            continue
        address = entry.get("address")
        if not address:
            continue
        chain = entry.get("chain", "8453")
        candidates.append((state.get(key, ""), key, address, chain, entry.get("symbol", "?")))
    candidates.sort(key=lambda c: c[0])
    return candidates[:limit]


def _append_finding(result):
    entry = {
        "category": "finding",
        "title": f"HACK sweep deep-dive: {result.get('symbol', '?')} — {result.get('verdict')} "
                 f"({result.get('score')}/100)",
        "content": (
            f"Daily HACK sweep escalated {result.get('address')} (chain {result.get('chain')}) from "
            f"a free-cycle CAUTION verdict to VAPE's full heavy tool suite (Slither/Halmos/Mythril/"
            f"Aderyn + OCI Grok 4.3 frontier reasoning). Full report: {result.get('report')}"
        ),
        "source": "agents/hack_sweep.py",
        "tags": ["hack-sweep", "deep-dive", "evm", str(result.get("chain", "8453"))],
        "confidence": 0.7,
        "severity": "MED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        os.makedirs(os.path.dirname(FINDINGS_PATH), exist_ok=True)
        with open(FINDINGS_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"[hack_sweep] could not append finding: {e}")


def run(max_targets=MAX_TARGETS_PER_RUN):
    state = _load_state()
    candidates = _select_candidates(max_targets)
    if not candidates:
        print("[hack_sweep] no fresh CAUTION-flagged ledger candidates this cycle.")
        return []

    results = []
    for _, key, address, chain, symbol in candidates:
        print(f"[hack_sweep] deep-diving {symbol} ({address}) on chain {chain}")
        try:
            result = dda.run_audit(address, str(chain), engagement="sweep")
        except Exception as e:
            print(f"[hack_sweep] deep dive failed for {address}: {e}")
            continue
        if not isinstance(result, dict) or "error" in result:
            print(f"[hack_sweep] deep dive returned an error for {address}: "
                 f"{result.get('error') if isinstance(result, dict) else result}")
            continue
        state[key] = datetime.now(timezone.utc).isoformat()
        _append_finding(result)
        results.append(result)

    _save_state(state)
    return results


if __name__ == "__main__":
    out = run()
    print(json.dumps(out, indent=2, default=str))
