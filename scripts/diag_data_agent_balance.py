#!/usr/bin/env python3
"""Read-only diagnostic: checks the DATA AGENT wallet's real on-chain USDC
balance on Base via a public RPC — the most likely explanation for every
paid attempt suddenly returning a bare HTTP 402 across both facilitators
(CDP and VAPOR) and multiple unrelated offerings is that the shared payer
wallet (agents/data_agent.py's EXPECTED_WALLET) has run out of USDC to
sign payments against. No private key needed — balanceOf is a public call.
"""
import json
import sys
import urllib.request

USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_RPC = "https://mainnet.base.org"


def _rpc(method, params):
    req = urllib.request.Request(
        BASE_RPC,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())


def usdc_balance(address: str) -> float:
    # balanceOf(address) selector 0x70a08231, address left-padded to 32 bytes
    data = "0x70a08231" + address[2:].lower().zfill(64)
    result = _rpc("eth_call", [{"to": USDC_BASE, "data": data}, "latest"])
    if "error" in result:
        raise RuntimeError(result["error"])
    raw = int(result["result"], 16)
    return raw / 1_000_000  # USDC has 6 decimals


def eth_balance(address: str) -> float:
    result = _rpc("eth_getBalance", [address, "latest"])
    if "error" in result:
        raise RuntimeError(result["error"])
    return int(result["result"], 16) / 1e18


if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "0x52af3E6D13f7C13EC887A2E69058A1432aa5B768"
    usdc = usdc_balance(address)
    eth = eth_balance(address)
    print(json.dumps({"address": address, "usdc_balance": usdc, "eth_balance": eth}, indent=2))
