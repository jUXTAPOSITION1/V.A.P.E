#!/usr/bin/env bash
# token_safety.sh — token honeypot / safety scan via GoPlusLabs (free, no key) + DexScreener.
# Usage:
#   token_safety.sh goplus <chainId> <tokenAddr>   -> GoPlus security fields (tax, honeypot, owner, mint)
#   token_safety.sh dex    <tokenAddr>             -> DexScreener pairs: liquidity, price, volume
#   token_safety.sh check  <chainId> <tokenAddr>   -> combined verdict heuristic (PROCEED/CAUTION/REJECT)
set -euo pipefail
GP="https://api.gopluslabs.io/api/v1/token_security"
DS="https://api.dexscreener.com/latest/dex/tokens"

goplus(){ curl -s "$GP/$1?contract_addresses=$2"; }

case "${1:-}" in
  goplus) goplus "$2" "$3" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('result',{})
addr=next(iter(d),None)
if not addr: print('{\"error\":\"no data (unverified/unknown token)\"}'); sys.exit()
t=d[addr]
print(json.dumps({k:t.get(k) for k in ('is_honeypot','buy_tax','sell_tax','is_mintable','owner_address','is_open_source','cannot_sell_all','is_proxy','holder_count','lp_holder_count')}))";;
  dex)    curl -s "$DS/$2" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('pairs') or []
for p in d[:3]:
    print(p.get('chainId'),p.get('dexId'),'liq_usd',(p.get('liquidity') or {}).get('usd'),'price',p.get('priceUsd'),'vol24h',(p.get('volume') or {}).get('h24'))";;
  check)  raw=$(goplus "$2" "$3"); echo "$raw" | python3 -c "
import sys,json
d=json.load(sys.stdin).get('result',{})
addr=next(iter(d),None)
if not addr: print('REJECT — no GoPlus data (unverified token)'); sys.exit()
t=d[addr]
hp=t.get('is_honeypot')=='1'; bt=float(t.get('buy_tax') or 0); st=float(t.get('sell_tax') or 0)
mint=t.get('is_mintable')=='1'; nosell=t.get('cannot_sell_all')=='1'
flags=[]
if hp: flags.append('HONEYPOT')
if nosell: flags.append('CANNOT_SELL_ALL')
if bt>0.10 or st>0.10: flags.append(f'HIGH_TAX(buy{bt} sell{st})')
if mint: flags.append('MINTABLE')
verdict='REJECT' if (hp or nosell) else ('CAUTION' if flags else 'PROCEED')
print(verdict,'—',', '.join(flags) if flags else 'no critical flags')";;
  *) echo 'usage: token_safety.sh {goplus <chainId> <addr>|dex <addr>|check <chainId> <addr>}' >&2; exit 1;;
esac
