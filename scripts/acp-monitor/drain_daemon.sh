#!/bin/sh
# ACP drain daemon — persistent sleep-loop. ZERO LLM cost while idle.
# Every INTERVAL: keepalive listener, drain+classify events. On an actionable
# job (triage exit 10), trigger the on-demand handler cron ONCE (the only paid action).
# Detached via setsid (PPID 1); survives session end. Keepalive cron restarts it if it dies.
set -u
DIR="/home/node/.openclaw/acp-monitor"
INTERVAL="${ACP_DRAIN_INTERVAL:-120}"
HANDLER_CRON="${ACP_HANDLER_CRON_ID:-}"
LOG="$DIR/drain.log"
PIDF="$DIR/drain.pid"

echo $$ > "$PIDF"
echo "[drain] started pid=$$ interval=${INTERVAL}s handler=${HANDLER_CRON}" >> "$LOG"

while true; do
  sh "$DIR/listener_guard.sh" >/dev/null 2>&1 || true
  OUT=$(python3 "$DIR/triage.py" 2>>"$LOG"); RC=$?
  if [ "$RC" = "10" ]; then
    echo "$(date -u +%FT%TZ) ACTIONABLE: $OUT" >> "$LOG"
    # ZERO-LLM auto-fulfill first: price+submit the 6 deterministic offerings via ACP CLI.
    AF=$(python3 "$DIR/auto_fulfill.py" 2>>"$LOG") || true
    echo "$(date -u +%FT%TZ) AUTOFULFILL: $AF" >> "$LOG"
    # Only wake the PAID handler if reasoning-grade jobs survived (escalate=true).
    REMAIN=0
    [ -f "$DIR/action-queue.jsonl" ] && REMAIN=$(grep -c . "$DIR/action-queue.jsonl" 2>/dev/null || echo 0)
    if [ "$REMAIN" -gt 0 ] && [ -n "$HANDLER_CRON" ]; then
      echo "$(date -u +%FT%TZ) ESCALATE: $REMAIN job(s) need reasoning" >> "$LOG"
      openclaw cron run "$HANDLER_CRON" >> "$LOG" 2>&1 || echo "[drain] handler trigger failed" >> "$LOG"
      sleep 30   # give the handler a head start; avoid double-trigger
    else
      echo "$(date -u +%FT%TZ) SETTLED: all jobs auto-fulfilled, zero LLM cost" >> "$LOG"
    fi
  fi
  sleep "$INTERVAL"
done
