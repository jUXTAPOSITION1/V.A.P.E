# VAPE Intel Rail — Rebuild State (2026-06-24)

## What happened
Container/volume reset wiped the agent-driven intel rail. GitHub Actions hourly rail
(reports/) still works. The rich intel/ updates were pushed by the AGENT (git author
"VAPE <37087973+jUXTAPOSITION1@users.noreply.github.com>") via OpenClaw crons — all gone.

## Rebuilt (done)
- [x] Repo cloned to persistent volume: /home/node/.openclaw/repos/vape
- [x] Git identity set to match history (VAPE / 37087973+jUXTAPOSITION1@users.noreply.github.com)
- [x] Credential helper: store --file=/home/node/.openclaw/repos/.vape-git-credentials
- [x] scripts/intel_sync.sh — zero-LLM commit+push of intel/
- [x] scripts/INTEL_RUNBOOK.md — the 6-vertical sweep spec (consolidated, low-compute)

## BLOCKED — needs user
1. GitHub push token. Create the credential file (gitignored, on volume):
   echo "https://<USER>:<GITHUB_PAT>@github.com" > /home/node/.openclaw/repos/.vape-git-credentials
   chmod 600 it. PAT needs `repo` scope.
2. OpenClaw cron-write scope. Device a5f12d1e… only has operator.read.
   Pending scope upgrade requestId (admin/write needed for `cron add`).
   Approve with: openclaw devices approve <requestId>   (USER decision — self-escalation paused)

## Planned cron (once scope granted)
Name: vape-intel-sweep | cron: 0 */4 * * * UTC | agent main | isolated | light-context
tools: exec read write web_search web_fetch | timeout 600s | no-deliver
Message: follow INTEL_RUNBOOK.md, write reports+broadcast, run intel_sync.sh. One turn/cycle.
(Old design was per-vertical 2h crons = wasteful. Consolidated to one 4h turn per first commandment.)
