#!/usr/bin/env bash
# wallet_trace.sh — wallet/address forensics via Alchemy's Transfers API.
# Replaces the prior Etherscan V2 account-module backend: Etherscan gates
# txlist/tokentx on Base behind a paid plan (see the "unsupported" verdict
# this repo logged against the old backend), while Alchemy's
# alchemy_getAssetTransfers has no such Base-specific gate. Base=8453 is the
# default/primary chain; Eth=1, Arb=42161, Op=10 also supported since the
# prior tool covered them.
# Usage:
#   wallet_trace.sh txs   <chainId> <address> [n]   -> last n transfers, any asset, both directions
#   wallet_trace.sh erc20 <chainId> <address> [n]   -> last n ERC-20 transfers, both directions
#   wallet_trace.sh first <chainId> <address>       -> first-seen transfer (funding source)
set -euo pipefail
KEY="${VAPE_TRACE_ALCHEMY_API:-}"
[ -z "$KEY" ] && { echo '{"error":"VAPE_TRACE_ALCHEMY_API required"}'; exit 3; }

case "${2:-}" in
  8453) HOST=base-mainnet.g.alchemy.com ;;
  1)    HOST=eth-mainnet.g.alchemy.com ;;
  42161) HOST=arb-mainnet.g.alchemy.com ;;
  10)   HOST=opt-mainnet.g.alchemy.com ;;
  *) echo "{\"error\":\"unsupported or missing chainId: ${2:-}\"}" >&2; exit 4 ;;
esac

case "${1:-}" in
  txs)   CATEGORY='["external","erc20","erc721","erc1155","internal"]' ;;
  erc20) CATEGORY='["erc20"]' ;;
  first) CATEGORY='["external","erc20","erc721","erc1155","internal"]' ;;
  *) echo 'usage: wallet_trace.sh {txs|erc20|first} <chainId> <address> [n]' >&2; exit 1;;
esac

MODE="$1" ADDR="$3" N="${4:-10}" HOST="$HOST" KEY="$KEY" CATEGORY="$CATEGORY" python3 <<'PYEOF'
import json, os, urllib.request

host, key, addr = os.environ["HOST"], os.environ["KEY"], os.environ["ADDR"]
mode, category = os.environ["MODE"], json.loads(os.environ["CATEGORY"])
n = int(os.environ["N"])
url = f"https://{host}/v2/{key}"
order = "asc" if mode == "first" else "desc"
max_count = 1 if mode == "first" else min(n, 100)


def fetch(direction):
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "alchemy_getAssetTransfers",
        "params": [{
            "fromBlock": "0x0", "toBlock": "latest",
            f"{direction}Address": addr, "category": category,
            "order": order, "maxCount": hex(max_count), "withMetadata": True,
        }],
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read())
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}))
        raise SystemExit(0)
    if "error" in d:
        print(json.dumps({"error": d["error"]}))
        raise SystemExit(0)
    return d.get("result", {}).get("transfers", [])


transfers = fetch("to") + fetch("from")
transfers.sort(key=lambda t: t.get("blockNum", "0x0"), reverse=(order == "desc"))
# Both directions can return the same transfer's counterpart view once each
# is fetched from opposite ends of a single fromAddress<->toAddress edge —
# dedupe on the unique tx hash + log index Alchemy assigns per transfer.
seen = set()
deduped = []
for t in transfers:
    uid = t.get("uniqueId") or t.get("hash")
    if uid in seen:
        continue
    seen.add(uid)
    deduped.append(t)
transfers = deduped[:1 if mode == "first" else n]

if not transfers:
    print("no data: no transfers found")
    raise SystemExit(0)

if mode == "first":
    t = transfers[0]
    print("first_seen block", int(t.get("blockNum", "0x0"), 16),
          "counterparty", t.get("from") if t.get("to", "").lower() == addr.lower() else t.get("to"),
          "hash", t.get("hash"))
else:
    for t in transfers:
        val = t.get("value")
        asset = t.get("asset") or "?"
        print(t.get("hash", "?")[:14], asset, val if val is not None else "?",
              "from", (t.get("from") or "?")[:10], "to", (t.get("to") or "?")[:10])
PYEOF
