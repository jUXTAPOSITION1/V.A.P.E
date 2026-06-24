#!/bin/sh
# VAPE intel sync — commit+push whatever the agent wrote into intel/ this cycle.
# Pure git plumbing, ZERO LLM cost. The agent cron writes the report file(s) first,
# then calls this to persist them. Lowest-compute: one pull/commit/push per cycle.
set -e
REPO="/home/node/.openclaw/repos/vape"
cd "$REPO"

STAMP="$(date -u +%Y-%m-%d\ %H:%M) UTC"
MSG="${1:-VAPE intel sync $STAMP}"

git pull --rebase --autostash origin main >/dev/null 2>&1 || true
git add intel/ skillforge/ 2>/dev/null || true

if git diff --cached --quiet; then
  echo "[intel_sync] no changes to commit"
  exit 0
fi

git commit -m "$MSG" >/dev/null
if git push origin main 2>&1 | tail -2; then
  echo "[intel_sync] pushed: $MSG"
else
  echo "[intel_sync] PUSH FAILED — check credential file" >&2
  exit 1
fi
