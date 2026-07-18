#!/usr/bin/env python3
"""
DATA AGENT (VAPOR-pinned) — the VAPOR-only sibling of agents/data_agent.py.

Same wallet, same offerings, same rate limits — see data_agent.py's module
docstring for the full story on why this exists as a second, independently-
gated instance instead of one agent alternating facilitators. This instance
tags every request X-VAPE-Client: data-agent-vapor, which worker/src/index.ts
pins to VAPOR (our own facilitator) as primary rather than the 50/50 coin
flip or CDP, so VAPOR gets real, regular settlement volume from VAPE's own
traffic on a schedule that doesn't depend on shared state with the CDP-
pinned instance.

Usage: python -m agents.data_agent_vapor <address> [chain]
(same recruitment path as data_agent.py — called from
agents/investigate.py::_data_agent_intel())
"""
import sys

from agents.data_agent import _run, _State

_VAPOR_STATE = _State("data_agent_vapor")


def run_for_investigation(address, chain="8453"):
    """Recruited by agents/investigate.py::investigate() for every real
    report — VAPOR-pinned instance (X-VAPE-Client: data-agent-vapor)."""
    return _run(address, chain, client_tag="data-agent-vapor", state=_VAPOR_STATE, log_prefix="data_agent_vapor")


if __name__ == "__main__":
    addr = sys.argv[1] if len(sys.argv) > 1 else None
    chain = sys.argv[2] if len(sys.argv) > 2 else "8453"
    if not addr:
        print("usage: python -m agents.data_agent_vapor <address> [chain]")
        sys.exit(1)
    print(run_for_investigation(addr, chain))
