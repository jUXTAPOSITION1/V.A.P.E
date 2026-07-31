# VAPE ACP Job Monitor

> **SUNSET (2026-07-31):** These daemons are no longer running. VAPE refocused on
> Base/all-EVM/Ethereum with x402 as its sole commerce rail rather than the Virtuals
> ecosystem/ACP specifically. Nothing here was deleted — if the host this ran on still has
> a crontab entry for `listener_guard.sh`/`keepalive.sh`/`triage_and_escalate.sh`, that
> entry should be removed there (this repo has no way to reach that host's crontab
> directly). This document describes how the integration worked, not current behavior.

Catches incoming ACP jobs, negotiates (set-budget), funds/completes, and submits real
deliverables — at near-zero compute. Mirrors the bounty-radar "Option A" cost design.

## Architecture (4 layers)
1. **Listener daemon** (`listener_guard.sh` → `acp events listen`): persistent, detached
   (PPID 1), appends job events to `events.jsonl`. ZERO LLM. One per output file.
2. **Drain daemon** (`drain_daemon.sh`): sleep-loop every 120s. Keepalives the listener,
   runs `triage.py` (drain+classify, ZERO LLM), then `auto_fulfill.py`. Only wakes the
   paid handler if reasoning-grade jobs survive auto-fulfill.
3. **Auto-fulfiller** (`auto_fulfill.py`, ZERO LLM at the monitor level): for the 6
   offerings it handles with no triage wake (token_safety_check, liquidity_check,
   rug_pull_alert, exploit_check, dossier_check, market_intel) it prices
   (`set-budget`) and submits a REAL deliverable from `agents/acp_fulfill.py` — the
   monitor itself never wakes a model to decide handling. Five of those six are also
   zero-LLM in their own deliverable; `dossier_check`'s deliverable now includes a
   real frontier-LLM quick source read (see `agents/publish_reputation.py`'s `ZERO_LLM`
   vs `AUTO` split). Everything else is left in the queue with `escalate=true`.
   Idempotent via `state.json`. `--dry-run` previews without CLI writes.
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
- `vape-virtuals-evaluator` (every 4h, add via `crontab -e`: `0 */4 * * * cd DIR && python3 virtuals_evaluator.py >> virtuals_evaluator.log 2>&1`)
  — VAPE self-hiring one of its own ACP offerings to evaluate a real Virtuals-tagged
  token; see `virtuals_evaluator.py`'s own docstring. Client-side (buyer role), unlike
  everything else in this directory (provider/selling role).

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
