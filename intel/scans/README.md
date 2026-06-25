# Token Scans

Real-data token safety scans logged by `agents/token_scan.py` (GoPlus + DexScreener).
The agent-side twin of the dashboard's Hunt console. Each scan writes a `scan-*.md`
report and appends to `scans.jsonl`. Real data only — verdicts: PROCEED / CAUTION / REJECT.
