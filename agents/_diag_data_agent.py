#!/usr/bin/env python3
"""Temporary diagnostic (2026-07-17) — agents/data_agent.py's hire() truncates
everything down to `f"HTTP {r.status_code} {r.text[:200]}"`, which is why the
ledger/workflow logs only ever showed "HTTP 500 Internal Server Error" with
no further detail. This bypasses hire()'s quota/interval gate and its
truncation, calling the same _build_session()/session.get() directly against
one real offering and dumping the full response (status, headers, body) or
full exception traceback if the request itself raises. Costs the same one
real $0.01 hire attempt data_agent.py would make anyway. Delete once the
worker-side bug is root-caused and fixed.
"""
import sys
import traceback

sys.path.insert(0, ".")
from agents import data_agent as da  # noqa: E402

session = da._build_session()
if session is None:
    print("[diag] _build_session() returned None — check DATA_AGENT_PRIVATE_KEY / x402 SDK availability")
    sys.exit(0)

print("[diag] session built OK, requesting /data/chain_overview with real payment flow...")
try:
    r = session.get(f"{da.WORKER_BASE}/data/chain_overview", params={"chain": "Base"}, timeout=30)
    print(f"[diag] status_code={r.status_code}")
    print(f"[diag] headers={dict(r.headers)}")
    print(f"[diag] body={r.text!r}")
except Exception:
    print("[diag] session.get() raised an exception:")
    traceback.print_exc()
