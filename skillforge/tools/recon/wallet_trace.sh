#!/usr/bin/env bash
# wallet_trace.sh — wallet/address forensics via Etherscan-family V2 API (multichain).
# Uses ETHERSCAN_API_KEY if set (free tier); falls back to no-key (rate-limited).
# Etherscan V2: one key, all chains, via &chainid=. Base=8453, Eth=1, Arb=42161, Op=10.
# Usage:
#   wallet_trace.sh txs   <chainId> <address> [n]   -> last n normal txs (default 10)
#   wallet_trace.sh erc20 <chainId> <address> [n]   -> last n ERC-20 transfers
#   wallet_trace.sh first <chainId> <address>       -> first-seen tx (funding source)
set -euo pipefail
KEY="${ETHERSCAN_API_KEY:-}"
[ -z "$KEY" ] && { echo '{"error":"ETHERSCAN_API_KEY required (Etherscan V2 has no keyless tier)"}'; exit 3; }
API="https://api.etherscan.io/v2/api"
q(){ curl -s "$API?chainid=$1&module=account&action=$2&address=$3&page=1&offset=${4:-10}&sort=${5:-desc}&apikey=$KEY"; }

case "${1:-}" in
  txs)   q "$2" txlist "$3" "${4:-10}" desc | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('status')!='1': print('no data:',d.get('message'),d.get('result')); sys.exit()
for t in d['result']:
    print(t['hash'][:14],'blk',t['blockNumber'],'from',t['from'][:10],'to',(t['to'] or '')[:10],'val',int(t['value'])/1e18)";;
  erc20) q "$2" tokentx "$3" "${4:-10}" desc | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('status')!='1': print('no data:',d.get('message')); sys.exit()
for t in d['result']:
    dec=int(t.get('tokenDecimal') or 18); print(t['hash'][:14],t.get('tokenSymbol'),int(t['value'])/(10**dec),'from',t['from'][:10],'to',t['to'][:10])";;
  first) q "$2" txlist "$3" 1 asc | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('status')!='1' or not d['result']: print('no data:',d.get('message')); sys.exit()
t=d['result'][0]; print('first_seen blk',t['blockNumber'],'funded_by',t['from'],'hash',t['hash'])";;
  *) echo 'usage: wallet_trace.sh {txs|erc20|first} <chainId> <address> [n]' >&2; exit 1;;
esac
