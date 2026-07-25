#!/usr/bin/env bash
# market_data.sh — free crypto market data (CoinGecko + DeFiLlama). No key, no LLM.
# Usage:
#   market_data.sh price <coingecko_id,...>   -> usd price, 24h chg, vol, mcap
#   market_data.sh global                       -> btc/eth dominance, 24h mcap chg
#   market_data.sh chaintvl <ChainName>         -> DeFiLlama chain TVL (e.g. Base)
set -euo pipefail
CG="https://api.coingecko.com/api/v3"
LLAMA="https://api.llama.fi"
case "${1:-}" in
  price)  curl -s "$CG/simple/price?ids=$2&vs_currencies=usd&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true";;
  global) curl -s "$CG/global" | python3 -c "
import sys,json
try:
    body=json.load(sys.stdin)
except ValueError:
    print('market_data global: CoinGecko returned a non-JSON response (likely rate-limited)', file=sys.stderr); sys.exit(1)
if not isinstance(body, dict):
    print('market_data global: unexpected response shape (likely rate-limited)', file=sys.stderr); sys.exit(1)
d=body.get('data')
if not isinstance(d, dict):
    err=None
    status=body.get('status')
    if isinstance(status, dict):
        err=status.get('error_message')
    print(f'market_data global: {err or \"no data field in response (likely rate-limited)\"}', file=sys.stderr); sys.exit(1)
try:
    print('btc_dom',round(d['market_cap_percentage']['btc'],2),'eth_dom',round(d['market_cap_percentage']['eth'],2),'mcap_chg_24h',round(d['market_cap_change_percentage_24h_usd'],2))
except (KeyError, TypeError):
    print('market_data global: response missing expected market metrics (likely rate-limited)', file=sys.stderr); sys.exit(1)
";;
  chaintvl) curl -s "$LLAMA/v2/chains" | python3 -c "import sys,json;n='$2'.lower();[print(x['name'],'TVL',round(x['tvl'],2),'chainId',x.get('chainId')) for x in json.load(sys.stdin) if x.get('name','').lower()==n]";;
  *) echo "usage: market_data.sh {price <ids>|global|chaintvl <Chain>}" >&2; exit 1;;
esac
