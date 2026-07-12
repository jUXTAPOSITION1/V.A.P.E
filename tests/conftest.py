"""Shared pytest fixtures/helpers for VAPE's deterministic-core tests.

These tests exercise the pure, network-free decision logic — the code whose
correctness a reader (or VAPE's own self-improvement loop) actually needs to
trust before believing a verdict. Nothing here hits the network, an LLM, or
the filesystem; every input is a hand-built fixture so the assertions pin
real, reproducible behavior.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def clean_gp(**over):
    """A GoPlus dict with every red flag OFF — the baseline a real 'clean but
    anonymous' token would produce. Override individual fields per test."""
    base = {
        "is_honeypot": "0", "cannot_sell_all": "0", "is_mintable": "0",
        "can_take_back_ownership": "0", "owner_change_balance": "0",
        "hidden_owner": "0", "is_proxy": "0", "transfer_pausable": "0",
        "buy_tax": "0", "sell_tax": "0", "owner_address": "",
        "holder_count": "",
    }
    base.update(over)
    return base


def clean_dex(**over):
    base = {"name": "", "symbol": "", "liquidity_usd": 0,
            "change_24h_pct": None, "pair_created_ms": None}
    base.update(over)
    return base


def days_ago_ms(days):
    return (time.time() - days * 86400) * 1000
