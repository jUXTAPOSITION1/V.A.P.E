#!/bin/sh
# ACP listener guard — idempotent keepalive. Starts at most ONE detached
# `acp events listen` daemon that appends job events to events.jsonl.
# Zero LLM cost: pure socket->file. Cron runs this every few hours; it only
# does real work if the daemon died (e.g. after a container/gateway restart).
set -e
DIR="/home/node/.openclaw/acp-monitor"
WS="/home/node/.openclaw/workspace"
OUT="$DIR/events.jsonl"
PIDF="$DIR/listener.pid"
LOG="$DIR/listener.log"

# Already running?
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; then
  echo "[guard] listener already running pid=$(cat "$PIDF")"
  exit 0
fi

cd "$WS" || exit 1
# Detach fully (survive parent exit). One listener per output file.
setsid sh -c "exec acp events listen --all --output '$OUT' --json >>'$LOG' 2>&1" &
echo $! > "$PIDF"
sleep 2
if kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; then
  echo "[guard] started listener pid=$(cat "$PIDF") -> $OUT"
else
  echo "[guard] FAILED to start listener; see $LOG" >&2
  tail -3 "$LOG" 2>/dev/null >&2
  exit 1
fi
