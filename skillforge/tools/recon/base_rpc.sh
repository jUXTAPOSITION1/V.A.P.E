#!/usr/bin/env bash
# base_rpc.sh — query Base mainnet via public JSON-RPC (no key, no LLM)
# Usage:
#   base_rpc.sh balance <address>     -> ETH balance (decimal)
#   base_rpc.sh nonce   <address>     -> tx count / nonce
#   base_rpc.sh gas                   -> gas price (gwei)
#   base_rpc.sh block                 -> latest block number
set -euo pipefail
RPC="${BASE_RPC:-https://mainnet.base.org}"
call(){ curl -s -X POST "$RPC" -H "Content-Type: application/json" --data "$1"; }
hex2dec(){ python3 -c "import sys;print(int(sys.stdin.read().strip(),16))"; }
case "${1:-}" in
  balance) r=$(call "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getBalance\",\"params\":[\"$2\",\"latest\"],\"id\":1}");
           echo "$r" | python3 -c "import sys,json;print(int(json.load(sys.stdin)['result'],16)/1e18)";;
  nonce)   r=$(call "{\"jsonrpc\":\"2.0\",\"method\":\"eth_getTransactionCount\",\"params\":[\"$2\",\"latest\"],\"id\":1}");
           echo "$r" | python3 -c "import sys,json;print(int(json.load(sys.stdin)['result'],16))";;
  gas)     r=$(call '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}');
           echo "$r" | python3 -c "import sys,json;print(int(json.load(sys.stdin)['result'],16)/1e9)";;
  block)   r=$(call '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}');
           echo "$r" | python3 -c "import sys,json;print(int(json.load(sys.stdin)['result'],16))";;
  *) echo "usage: base_rpc.sh {balance <addr>|nonce <addr>|gas|block}" >&2; exit 1;;
esac
