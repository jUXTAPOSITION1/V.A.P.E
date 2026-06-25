#!/bin/sh
# ACP listener guard — idempotent keepalive. Ensures exactly ONE healthy
# `acp events listen` daemon appending job events to events.jsonl.
# Zero LLM cost: pure socket->file. Run by cron/drain loop; only acts if the
# daemon is missing, dead, OR a zombie (<defunct>).
#
# Fix (2026-06-25): the old guard used `kill -0 $PID`, which returns TRUE for a
# ZOMBIE/<defunct> process — so when the listener crashed on a Privy approval
# timeout it was never restarted, VAPE went offline, and ACP discovery dropped it.
# We now treat zombie/non-acp PIDs as dead and respawn via a self-restarting
# supervisor so a single RPC-approval crash can't take the agent offline.
set -e
DIR="/home/node/.openclaw/acp-monitor"
WS="/home/node/.openclaw/workspace"
OUT="$DIR/events.jsonl"
PIDF="$DIR/listener.pid"
LOG="$DIR/listener.log"
SUP="$DIR/listener_supervisor.sh"

is_healthy() {
  PID="$1"
  [ -n "$PID" ] || return 1
  kill -0 "$PID" 2>/dev/null || return 1
  # Reject zombies (state Z / defunct).
  STATE=$(ps -o stat= -p "$PID" 2>/dev/null | tr -d ' ')
  case "$STATE" in
    Z*) return 1 ;;   # zombie
  esac
  # Must actually be our supervisor or an acp listen process, not a recycled PID.
  CMD=$(ps -o args= -p "$PID" 2>/dev/null || true)
  case "$CMD" in
    *listener_supervisor* | *"events listen"* | *"acp events"*) return 0 ;;
  esac
  return 1
}

if is_healthy "$(cat "$PIDF" 2>/dev/null)"; then
  echo "[guard] listener healthy pid=$(cat "$PIDF")"
  exit 0
fi

# Reap any stale/zombie pid record before respawning.
OLD=$(cat "$PIDF" 2>/dev/null || true)
if [ -n "$OLD" ]; then
  kill "$OLD" 2>/dev/null || true
  echo "[guard] $(date -u +%FT%TZ) replacing dead/zombie listener pid=$OLD" >> "$LOG"
fi

cd "$WS" || exit 1
# Launch the self-restarting supervisor, fully detached (survives parent exit).
setsid sh -c "exec sh '$SUP'" >/dev/null 2>&1 &
echo $! > "$PIDF"
sleep 3
if is_healthy "$(cat "$PIDF" 2>/dev/null)"; then
  echo "[guard] started listener supervisor pid=$(cat "$PIDF") -> $OUT"
else
  echo "[guard] FAILED to start listener; see $LOG" >&2
  tail -5 "$LOG" 2>/dev/null >&2
  exit 1
fi
