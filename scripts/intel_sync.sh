#!/bin/sh
# VAPE intel sync — commit+push whatever the agent wrote into intel/ this cycle.
# Pure git plumbing, ZERO LLM cost. The agent cron writes the report file(s) first,
# then calls this to persist them. Lowest-compute: one pull/commit/push per cycle.
set -e
REPO="/home/node/.openclaw/repos/vape"
cd "$REPO"

STAMP="$(date -u +%Y-%m-%d\ %H:%M) UTC"
MSG="${1:-VAPE intel sync $STAMP}"

git add intel/ skillforge/ 2>/dev/null || true

if git diff --cached --quiet && [ -z "$(git log origin/main..HEAD 2>/dev/null)" ]; then
  echo "[intel_sync] no changes to commit"
  exit 0
fi

git diff --cached --quiet || git commit -m "$MSG" >/dev/null

# Retry loop: rebase on latest remote then push, to survive concurrent GH Actions pushes.
n=0
while [ $n -lt 5 ]; do
  git pull --rebase --autostash origin main >/dev/null 2>&1 || true
  if git push origin main >/dev/null 2>&1; then
    echo "[intel_sync] pushed: $MSG"
    exit 0
  fi
  n=$((n+1))
  echo "[intel_sync] push race, retry $n/5..." >&2
  sleep $((n*3))
done
echo "[intel_sync] PUSH FAILED after retries" >&2
exit 1
