# VAPE ACP Job Monitor

Catches incoming ACP jobs, negotiates (set-budget), funds/completes, and submits real
deliverables — at near-zero compute. Mirrors the bounty-radar "Option A" cost design.

## Architecture (4 layers)
1. **Listener daemon** (`listener_guard.sh` → `acp events listen`): persistent, detached
   (PPID 1), appends job events to `events.jsonl`. ZERO LLM. One per output file.
2. **Drain daemon** (`drain_daemon.sh`): sleep-loop every 120s. Keepalives the listener,
   runs `triage.py` (drain+classify, ZERO LLM), then `auto_fulfill.py`. Only wakes the
   paid handler if reasoning-grade jobs survive auto-fulfill.
3. **Auto-fulfiller** (`auto_fulfill.py`, ZERO LLM): for the 6 deterministic offerings
   (token_safety_check, liquidity_check, rug_pull_alert, exploit_check, safety_preflight,
   market_intel) it prices (`set-budget`) and submits a REAL deliverable from
   `agents/acp_fulfill.py` — no model wake. Everything else is left in the queue with
   `escalate=true`. Idempotent via `state.json`. `--dry-run` previews without CLI writes.
4. **Reasoning handler** (cron `vape-acp-handler`, on-demand only): woken ONLY for the
   escalated remainder (deep_contract_audit, forensics_deep, wallet_recon, tx_decode, …).
   Reads `HANDLER_BRIEF.md` + `action-queue.jsonl`, runs the mapped SKILLFORGE tool,
   submits a tailored real deliverable. This is the only paid path.

## Files
- `events.jsonl`   — raw event stream from listener
- `state.json`     — per-job state (phase history, done flags) — idempotency
- `action-queue.jsonl` — actionable jobs awaiting the handler
- `listener.pid` / `drain.pid` — daemon pids
- `*.log` — listener/drain logs

## Crons
- `vape-acp-keepalive` (every 3h) — restarts drain daemon if dead (post-restart recovery)
- `vape-acp-handler` (disabled schedule) — fired on-demand by the drain daemon

## Lifecycle (provider/selling)
job.created → set-budget (offering price) → job.funded → run tool + submit deliverable → done.
See HANDLER_BRIEF.md for the offering→tool→deliverable map.

## Manual ops
- Status:  `kill -0 $(cat listener.pid) && kill -0 $(cat drain.pid)`
- Restart: `sh keepalive.sh`
- Triage now: `cd /home/node/.openclaw/workspace && python3 ../acp-monitor/triage.py`
- Stop all: `kill $(cat drain.pid) $(cat listener.pid)`

## Requirements (all met as of 2026-06-24)
- Signer provisioned (restricted policy) [OK]
- 14 offerings live [OK]
- Wallet funded (USDC on Base) [OK]

## Note: Privy policy approvals
The `restricted` signer may surface one-time Privy RPC approvals on init
(e.g. "RPC request denied due to policy violation" with an approve URL). These are
read-probe approvals, not escrow actions. ACP escrow txns (set-budget/fund/submit/complete)
are authorized by the restricted policy. Approve any that block real job actions.
