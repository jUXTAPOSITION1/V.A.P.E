#!/usr/bin/env bash
# fear_greed.sh — Crypto Fear & Greed Index via alternative.me. No key, no LLM.
# Feeds the sentiment-sweep vertical with a single structured 0-100 gauge.
# Usage:
#   fear_greed.sh            -> latest value + classification
#   fear_greed.sh N          -> last N daily readings (value classification date)
#   fear_greed.sh raw        -> dump raw JSON
set -euo pipefail
URL="https://api.alternative.me/fng"
case "${1:-latest}" in
  raw) curl -s "$URL/?limit=0";;
  latest|"") curl -s "$URL/" | python3 -c "import sys,json;d=json.load(sys.stdin)['data'][0];print(d['value'],d['value_classification'])";;
  *) curl -s "$URL/?limit=$1" | python3 -c "
import sys,json,datetime
for d in json.load(sys.stdin)['data']:
    ts=datetime.datetime.utcfromtimestamp(int(d['timestamp'])).strftime('%Y-%m-%d')
    print(d['value'],d['value_classification'],ts)
";;
esac
