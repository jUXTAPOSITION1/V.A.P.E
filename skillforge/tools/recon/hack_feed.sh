#!/usr/bin/env bash
# hack_feed.sh — keyless DeFi exploit/hack feed via DeFiLlama. No key, no LLM.
# Feeds the security-sweep vertical with structured, dated incident data.
# Usage:
#   hack_feed.sh latest [N]          -> N most-recent hacks (default 10): date name $M chain technique
#   hack_feed.sh since YYYY-MM-DD    -> all hacks on/after a date
#   hack_feed.sh chain <ChainName>   -> recent hacks touching a chain (e.g. Base, Ethereum)
#   hack_feed.sh raw                 -> dump raw JSON
set -euo pipefail
URL="https://api.llama.fi/hacks"
fetch(){ curl -s "$URL"; }
case "${1:-latest}" in
  latest)
    fetch | N="${2:-10}" python3 -c "
import sys,json,os,datetime
d=json.load(sys.stdin); n=int(os.environ['N'])
d.sort(key=lambda x:x.get('date',0),reverse=True)
for h in d[:n]:
    ts=datetime.datetime.utcfromtimestamp(h['date']).strftime('%Y-%m-%d')
    print(ts,h.get('name'),round((h.get('amount') or 0)/1e6,2),'M',h.get('chain'),h.get('technique'))
";;
  since)
    fetch | D="$2" python3 -c "
import sys,json,os,datetime
d=json.load(sys.stdin); cut=datetime.datetime.strptime(os.environ['D'],'%Y-%m-%d').timestamp()
d.sort(key=lambda x:x.get('date',0),reverse=True)
for h in d:
    if h.get('date',0)>=cut:
        ts=datetime.datetime.utcfromtimestamp(h['date']).strftime('%Y-%m-%d')
        print(ts,h.get('name'),round((h.get('amount') or 0)/1e6,2),'M',h.get('chain'),h.get('technique'))
";;
  chain)
    fetch | C="$2" python3 -c "
import sys,json,os,datetime
d=json.load(sys.stdin); c=os.environ['C'].lower()
d.sort(key=lambda x:x.get('date',0),reverse=True)
for h in d:
    if any(c==str(x).lower() for x in (h.get('chain') or [])):
        ts=datetime.datetime.utcfromtimestamp(h['date']).strftime('%Y-%m-%d')
        print(ts,h.get('name'),round((h.get('amount') or 0)/1e6,2),'M',h.get('chain'),h.get('technique'))
";;
  raw) fetch;;
  *) echo "usage: hack_feed.sh {latest [N]|since YYYY-MM-DD|chain <Chain>|raw}" >&2; exit 1;;
esac
