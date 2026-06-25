#!/bin/sh
# Restart the drain daemon AND the listener if either died (e.g. after a
# container/gateway restart, or a Privy approval-timeout crash). Run by cron.
DIR="/home/node/.openclaw/acp-monitor"
PIDF="$DIR/drain.pid"

# Independently guard the listener (zombie-aware). The drain loop also does this
# every 120s, but if the drain daemon itself is down the listener must still be
# protected so VAPE never silently drops offline in ACP discovery.
sh "$DIR/listener_guard.sh" >/dev/null 2>&1 || true
if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF" 2>/dev/null)" 2>/dev/null; then
  echo "[keepalive] drain daemon alive pid=$(cat "$PIDF")"
  exit 0
fi
ACP_HANDLER_CRON_ID="5aea0293-268d-4caf-ad7c-9fcbab5d0246" ACP_DRAIN_INTERVAL=120 \
  setsid sh -c "exec sh $DIR/drain_daemon.sh" >/dev/null 2>&1 &
sleep 2
echo "[keepalive] restarted drain daemon pid=$(cat "$PIDF" 2>/dev/null)"
