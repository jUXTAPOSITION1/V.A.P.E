#!/usr/bin/env bash
# contract_recon.sh — contract source/verification recon via Etherscan V2 (multichain).
# Uses ETHERSCAN_API_KEY if set. Base=8453, Eth=1, Arb=42161, Op=10, Polygon=137.
# Usage:
#   contract_recon.sh verified <chainId> <addr>   -> is source verified? name + compiler
#   contract_recon.sh abi      <chainId> <addr>   -> ABI (json) if verified
#   contract_recon.sh creation <chainId> <addr>   -> creator address + creation tx
#   contract_recon.sh source   <chainId> <addr>   -> verified source code (truncated)
set -euo pipefail
KEY="${ETHERSCAN_API_KEY:-}"
[ -z "$KEY" ] && { echo '{"error":"ETHERSCAN_API_KEY required (Etherscan V2 has no keyless tier)"}'; exit 3; }
API="https://api.etherscan.io/v2/api"
c(){ curl -s "$API?chainid=$1&module=contract&action=$2&address=$3&apikey=$KEY"; }

case "${1:-}" in
  verified) c "$2" getsourcecode "$3" | python3 -c "
import sys,json
r=json.load(sys.stdin).get('result',[{}])[0]
src=r.get('SourceCode','')
print('verified' if src else 'UNVERIFIED','| name:',r.get('ContractName') or '?','| compiler:',r.get('CompilerVersion') or '?','| proxy:',r.get('Proxy'),'| impl:',r.get('Implementation') or '-')";;
  abi)      c "$2" getabi "$3" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['result'][:2000] if d.get('status')=='1' else 'no ABI (unverified)')";;
  creation) curl -s "$API?chainid=$2&module=contract&action=getcontractcreation&contractaddresses=$3&apikey=$KEY" | python3 -c "
import sys,json
d=json.load(sys.stdin)
if d.get('status')!='1': print('no data:',d.get('message')); sys.exit()
r=d['result'][0]; print('creator',r.get('contractCreator'),'tx',r.get('txHash'))";;
  source)   c "$2" getsourcecode "$3" | python3 -c "
import sys,json
r=json.load(sys.stdin).get('result',[{}])[0]
src=r.get('SourceCode','')
print(src[:3000] if src else 'UNVERIFIED — no source available')";;
  *) echo 'usage: contract_recon.sh {verified|abi|creation|source} <chainId> <addr>' >&2; exit 1;;
esac
