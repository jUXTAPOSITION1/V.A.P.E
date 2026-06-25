#!/bin/sh
# ACP listener supervisor — keeps `acp events listen` alive across crashes.
# The v2 acp-node listener can throw fatally (e.g. ApprovalTimeoutError when a
# Privy `restricted`-policy RPC approval isn't actioned within 5 min). Without
# supervision that one throw takes VAPE OFFLINE and ACP discovery drops it.
# This wrapper restarts the listener with capped backoff so the agent stays
# online (fresh minsFromLastOnlineTime) regardless of transient approval blips.
#
# Detached via setsid by listener_guard.sh; its PID is what listener.pid holds.
# Zero LLM cost.
set -u
DIR="/home/node/.openclaw/acp-monitor"
WS="/home/node/.openclaw/workspace"
OUT="$DIR/events.jsonl"
LOG="$DIR/listener.log"

echo "$(date -u +%FT%TZ) [supervisor] start pid=$$" >> "$LOG"
cd "$WS" || exit 1

backoff=5
while true; do
  echo "$(date -u +%FT%TZ) [supervisor] launching acp events listen" >> "$LOG"
  acp events listen --all --output "$OUT" --json >> "$LOG" 2>&1 &
  CHILD=$!
  echo "$CHILD" > "$DIR/listener_child.pid"
  wait "$CHILD"
  RC=$?
  echo "$(date -u +%FT%TZ) [supervisor] listener exited rc=$RC; restarting in ${backoff}s" >> "$LOG"
  sleep "$backoff"
  # Exponential-ish backoff capped at 60s so a persistent approval block
  # doesn't hot-loop, but transient crashes recover fast.
  backoff=$((backoff * 2))
  [ "$backoff" -gt 60 ] && backoff=60
  # Reset backoff if the listener had been up a while (handled implicitly by
  # the cap; a clean long run that then dies still restarts within 60s).
done
