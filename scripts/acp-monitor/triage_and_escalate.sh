#!/bin/sh
# ACP triage + escalate — the low-compute heartbeat.
# 1) keepalive the listener (idempotent)
# 2) drain+classify events (zero LLM)
# 3) ONLY if an actionable job exists, emit a wake signal for the handler.
# Run by cron every few minutes. Costs ~nothing while idle.
set -e
DIR="/home/node/.openclaw/acp-monitor"

# 1) ensure listener is up
sh "$DIR/listener_guard.sh" >/dev/null 2>&1 || true

# 2) triage (drain + classify -> action-queue.jsonl). exit 10 = actionable present.
OUT=$(python3 "$DIR/triage.py" 2>/dev/null) || RC=$?
RC=${RC:-0}
echo "$OUT"

# Nothing actionable -> done, zero cost.
[ "$RC" = "10" ] || exit 0

# 3) AUTO-FULFILL the deterministic zero-LLM offerings (token_safety, liquidity,
#    rug_pull, exploit_check, safety_preflight, market_intel). Prices + submits via
#    the ACP CLI; leaves only reasoning-grade jobs in the queue with escalate=true.
AF=$(python3 "$DIR/auto_fulfill.py" 2>/dev/null) || true
echo "$AF"

# 4) Did anything survive auto-fulfill (deep audit / forensics / wallet etc.)?
#    Only THEN wake the LLM handler.
REMAIN=0
if [ -f "$DIR/action-queue.jsonl" ]; then
  REMAIN=$(grep -c . "$DIR/action-queue.jsonl" 2>/dev/null || echo 0)
fi
if [ "$REMAIN" -gt 0 ]; then
  echo "[escalate] $REMAIN job(s) need reasoning — waking handler"
  date -u +%Y-%m-%dT%H:%M:%SZ > "$DIR/.wake"
  exit 10
fi
echo "[auto] all actionable jobs settled with zero LLM cost"
exit 0
