#!/usr/bin/env python3
"""
Arbitrum Oracle Manipulation Tracer (VAPE agents/oracle_tracer.py)

Stdlib-only forensic tool. Consumes tx hash, walks receipt + logs for
Chainlink AggregatorV3Interface (and known custom feeds), extracts
pre/post roundData, flags deltas > threshold or stale rounds, emits
compact JSON report with call graph and rough USD impact.
"""
import argparse
import json
import logging
import sys
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

# Known oracle addresses on Arbitrum (extend via env/arg in future runs)
KNOWN_ORACLES: Dict[str, str] = {
    "0x639fe6ab55c921f74e7fac1ee960c0b6293ba612": "Chainlink ETH/USD",
    "0x50834f3163758fcc1df9973b6e6b0b0a1e2f0a1e": "Chainlink USDC/USD",
}

# Simple thresholds (tunable)
DELTA_THRESHOLD_PCT = 5.0
STALE_ROUNDS = 3
RPC_URLS = {
    "arbitrum": "https://arb1.arbitrum.io/rpc",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("oracle_tracer")


def rpc_call(method: str, params: List[Any], rpc_url: str) -> Any:
    """Perform JSON-RPC call with basic error handling."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(rpc_url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            if "error" in result:
                raise RuntimeError(result["error"])
            return result.get("result")
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"RPC failure: {exc}") from exc


def get_receipt(tx_hash: str, rpc_url: str) -> Dict[str, Any]:
    return rpc_call("eth_getTransactionReceipt", [tx_hash], rpc_url) or {}


def get_logs(address: str, from_block: int, to_block: int, rpc_url: str) -> List[Dict[str, Any]]:
    params = [{"address": address, "fromBlock": hex(from_block), "toBlock": hex(to_block)}]
    return rpc_call("eth_getLogs", params, rpc_url) or []


def decode_price(log: Dict[str, Any]) -> Optional[Tuple[int, int]]:
    """Decode AnswerUpdated event (roundId, answer) from Chainlink log."""
    data = log.get("data", "0x")
    if len(data) < 130:
        return None
    try:
        round_id = int(data[2:66], 16)
        answer = int(data[66:130], 16)
        return round_id, answer
    except ValueError:
        return None


def build_call_graph(receipt: Dict[str, Any]) -> List[str]:
    """Minimal call graph from logs (to + topics)."""
    graph = []
    for log in receipt.get("logs", []):
        addr = log.get("address", "")
        if addr.lower() in {k.lower() for k in KNOWN_ORACLES}:
            graph.append(f"{addr}:{log.get('topics', [''])[0][:10]}")
    return graph


def trace_oracle(tx_hash: str, chain: str, block_range: Optional[int] = None) -> Dict[str, Any]:
    """Core tracer entrypoint."""
    rpc_url = RPC_URLS.get(chain)
    if not rpc_url:
        raise ValueError(f"Unsupported chain: {chain}")

    receipt = get_receipt(tx_hash, rpc_url)
    if not receipt:
        raise RuntimeError("Transaction not found or pending")

    block_num = int(receipt.get("blockNumber", "0x0"), 16)
    start_block = max(0, block_num - (block_range or 100))
    end_block = block_num + 1

    findings = []
    for addr, name in KNOWN_ORACLES.items():
        logs = get_logs(addr, start_block, end_block, rpc_url)
        prices = []
        for log in logs:
            decoded = decode_price(log)
            if decoded:
                prices.append({"round": decoded[0], "price": decoded[1], "tx": log.get("transactionHash")})

        if len(prices) >= 2:
            pre, post = prices[0], prices[-1]
            delta = abs(post["price"] - pre["price"]) / max(pre["price"], 1) * 100
            if delta > DELTA_THRESHOLD_PCT or (post["round"] - pre["round"]) > STALE_ROUNDS:
                findings.append({
                    "oracle": name,
                    "address": addr,
                    "pre": pre,
                    "post": post,
                    "delta_pct": round(delta, 2),
                    "anomaly": "large_delta" if delta > DELTA_THRESHOLD_PCT else "stale_round",
                })

    report = {
        "tx": tx_hash,
        "block": block_num,
        "call_graph": build_call_graph(receipt),
        "findings": findings,
        "usd_impact_estimate": sum(f["delta_pct"] * 1000 for f in findings),  # placeholder heuristic
        "assumptions": [
            "Only monitors known Chainlink addresses",
            "USD impact is rough heuristic (price * notional TBD)",
            "No L2-specific sequencer delay analysis",
        ],
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Arbitrum oracle manipulation tracer")
    parser.add_argument("tx_hash", help="Arbitrum transaction hash")
    parser.add_argument("--chain", default="arbitrum", choices=list(RPC_URLS.keys()))
    parser.add_argument("--blocks", type=int, default=100, help="Block range to scan")
    args = parser.parse_args()

    try:
        report = trace_oracle(args.tx_hash, args.chain, args.blocks)
        print(json.dumps(report, indent=2))
    except Exception as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()