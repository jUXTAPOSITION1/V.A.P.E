# VAPE Security & Intel Protocol

VAPE is an autonomous agent that holds a real wallet, spends real API/LLM
budget on a schedule, reads attacker-controlled on-chain data as part of its
job, and opens real PRs against its own source. This document is the single
place that threat model lives — what's actually being defended, what already
defends it, what a 2026-07-13 repo-wide audit found and fixed, and how this
keeps evolving instead of going stale the way a one-time audit report does.

Every claim below is grounded in a real file/line in this repo as of the
audit date — nothing here is aspirational. Where something is a known,
accepted gap, it's stated as such rather than omitted.

## Threat model — what's actually at risk

| Surface | What could go wrong | Blast radius |
|---|---|---|
| The report pipeline (`agents/run.py`, `investigate.py`) | Attacker-controlled on-chain token/contract names smuggle instructions into VAPE's own LLM grounding | A published report says something false/misleading about a token, or suppresses a real REJECT verdict |
| The AI quick-review (`agents/acp_fulfill.py::_ai_quick_review`) | Same shape, via a verified contract's own source/comments | A paid `dossier_check` deliverable's summary paragraph is misleading (score/verdict are computed separately and can't be overridden this way) |
| CI (`.github/workflows/*.yml`) | Fork-controlled code running with real secrets ("pwn request"); a hijacked third-party Action running with `CLOUDFLARE_API_TOKEN`; shell injection via unescaped `${{ github.event.* }}` | Exfiltrated API keys, unauthorized Worker deploy, arbitrary code execution in CI |
| The x402 Worker (`worker/src/index.ts`) | Free endpoints backed by metered third-party APIs (Alchemy, CoinGecko) with no abuse control | A scripted client burns paid API quota with no cost recovery |
| The signing wallet (`agents/data_agent.py`) | Key mishandling — logged, prompted to an LLM, or influenced by untrusted data | Real fund loss |
| Dependencies (`requirements.txt`, `worker/package.json`) | An unpatched CVE in a pinned version | Depends on the CVE; worst case is remote code execution in CI or the Worker |
| VAPE's own verdicts drifting from reality | A past PROCEED/CAUTION/REJECT call ages badly as a token's behavior changes | Stale public claims |

## What already defends each surface (as of 2026-07-13)

- **Report-pipeline prompt injection**: `agents/redteam.py` (daily,
  `redteam.yml`) runs two *real* injection payloads through the actual
  `VAPE_REPORT_SYSTEM` pipeline and judges the real LLM response, plus a
  heavier `deepteam`/`garak`/`promptfoo` pass (`redteam-deep.yml`, daily).
  `agents/run.py::_reconcile_report()` is the deterministic backstop that
  actually closes the finding these probes kept surfacing: it never trusts
  the model's own SIGNAL/narrative claim over what this cycle's real
  investigation digests say, and `investigate.py::_sanitize_symbol()` strips
  the on-chain data at the exact point it enters the system so a token name
  can't forge a fake verdict field ahead of the real one.
- **On-chain threat intelligence**: `agents/security_sweep.py` (4x/day,
  `intel-sweeps.yml`) pulls DeFiLlama's real hack feed, computes threat
  level deterministically (fixed USD/day thresholds, LLM only narrates —
  never scores), runs real forensics against high-value/recent incidents via
  `investigate.py`, and classifies each incident's technique against a fixed
  attack-pattern table tagged with whether VAPE's own `score()` would have
  caught it — logging `coverage-gap`/`backtest-miss` findings when it
  wouldn't have.
- **Verdict drift**: `agents/review_ledger.py` (`review-ledger.yml`) re-checks
  the oldest-reviewed pass/caution addresses weekly and fail addresses
  monthly against fresh data, logging a finding whenever a past verdict no
  longer holds.
- **Dependency CVEs**: `dependency-audit.yml` runs `pip-audit` against both
  Python requirement files and (as of this audit) `npm audit` against
  `worker/`'s production dependencies, on every push/PR that touches them
  plus a weekly cron; `dependabot.yml` covers pip (root + `/agents`) and npm
  (root + `/worker`, both added/verified this audit) and github-actions.
- **Scan-logic drift**: `scan-parity.yml` fails the build if
  `agents/token_scan.py` and `worker/src/scan.ts` ever disagree on a fixed
  test address.
- **CI regression** (new this audit): `security-lint.yml` /
  `scripts/security_lint.py` — see below.

## What this audit found and fixed (2026-07-13)

A repo-wide audit (wallet/key handling, CI workflow injection risk, rate
limiting/abuse controls, and an inventory of existing automation) turned up
these confirmed, concrete issues, all fixed in the same change as this doc:

1. **Worker quota-drain gap** — `worker/src/index.ts`'s `/prices` and
   `/cost-basis` endpoints had neither caching nor rate limiting, unlike
   their Alchemy-backed siblings; a scripted loop varying the address per
   call could burn metered Alchemy/CoinGecko quota with nothing to stop it.
   Fixed: added `cache()` matching the sibling routes, plus a KV-backed
   per-IP fixed-window rate limiter (`rateLimiter()` in `index.ts`) applied
   to `/prices`, `/cost-basis`, `/portfolio`, and `/nfts` — degrades to
   "never blocks" when `VAPE_JOBS` isn't configured, same graceful pattern
   as every other optional resource in that file.
2. **Unframed contract source in an LLM prompt** —
   `agents/acp_fulfill.py::_ai_quick_review` embedded a verified contract's
   deployer-controlled source directly into a prompt with no untrusted-data
   framing — the same injection shape just closed in `run.py`, capped at a
   misleading summary paragraph rather than fund loss (the deterministic
   score/verdict fields are computed separately and can't be overridden this
   way). Fixed: added explicit inert-data framing to
   `_AI_QUICK_REVIEW_SYSTEM`.
3. **Shell-injection anti-pattern in two workflows** —
   `review-ledger.yml` and `x402-index-claim.yml` interpolated
   `workflow_dispatch` inputs directly into `run:` steps instead of routing
   through `env:` first, inconsistent with the rest of the repo's own
   convention. `review-ledger.yml`'s job in particular carries every LLM/
   research API key plus `DATA_AGENT_PRIVATE_KEY` and `contents: write` —
   real blast radius if that input path were ever abused, even though the
   trigger requires existing repo-write access already. Fixed both, plus one
   more instance caught by the new linter in `build-request.yml`.
4. **Unpinned third-party Action with live deploy credentials** —
   `cloudflare/wrangler-action@v4` ran with `CLOUDFLARE_API_TOKEN`/
   `CLOUDFLARE_ACCOUNT_ID` on every push to `main` touching `worker/**`,
   pinned only to a mutable tag. Fixed: pinned to the tag's current commit
   SHA (verified against the GitHub API at fix time), with a comment on how
   to re-pin deliberately later. `denoland/setup-deno@v2` (no secrets in
   that job, lower severity) was pinned too for consistency.
5. **No dependency scanning for `worker/`** — the only Node project handling
   real payment logic had zero CVE scanning anywhere in CI. Fixed: added
   `npm audit` to `dependency-audit.yml` and an `npm`/`/worker` entry to
   `dependabot.yml`.

**Confirmed clean, no fix needed**: private-key handling
(`agents/data_agent.py`'s `DATA_AGENT_PRIVATE_KEY` — never logged, never
prompted to an LLM, never influenced by untrusted data; the ACP/x402 flows
never touch a buyer's key); `.env` tracking; MCP server registry (static,
maintainer-only); `skillforge/toolcheck.py` (the "free tool checker" flagged
going into this audit — cron/dispatch-only trigger, fixed maintainer-curated
registry, per-call subprocess timeouts, not externally reachable); the
existing `agents/llm.py` provider-fallback chain (bounded retries, no
runaway-retry gap, though see the accepted gap below on aggregate spend).

## Known, accepted gaps (not fixed here — stated, not hidden)

- **No aggregate $ spend cap across LLM providers.** `agents/llm.py`'s
  `FRONTIER_ORDER` chain bounds retries *per call*, but nothing caps total
  spend per day/run across all scheduled agents. Not currently exploitable
  (every caller is a scheduled cron job, not an externally-reachable
  trigger), so this is a cost-hygiene gap, not a security hole — tracked
  here rather than rushed into this change.
- **`_reconcile_report()`'s narrative body isn't content-sanitized once the
  `SIGNAL:` marker is well-formed and consistent with real digest data.**
  Raised by CodeRabbit during PR #156's review and deliberately deferred:
  closing it means moving to fully-templated report rendering instead of LLM
  narrative synthesis, which is a real architectural trade-off (provenance
  guarantee vs. LLM-authored prose) for the repo owner to decide, not a
  quick patch. `_reconcile_report()`'s job is narrowly "never let the model
  suppress or override a real finding" — it does that; it was never claimed
  to sanitize free-form narrative content.
- **Workflow `timeout-minutes` hygiene.** Several scheduled workflows don't
  set an explicit timeout and fall back to GitHub's 360-minute default. None
  of them are externally triggerable, so this is a hang-risk/cost-hygiene
  item, not an exploitable gap — left for a future pass rather than bundled
  into a security fix.

## How this evolves (the actual point of calling it a "protocol")

A security posture that's only as good as its last audit is not a
protocol — it's a report. Four things make this one keep working after
today:

1. **`security-lint.yml` / `scripts/security_lint.py`** — runs on every PR
   touching `.github/workflows/**`, deterministically re-checking for the
   exact four regression classes found above (pwn-request triggers,
   unpinned third-party Actions with secrets, raw `${{ github.event.* }}`
   interpolation into `run:`, missing `permissions:` blocks). This is the
   mechanism that stops today's fixes from quietly rotting — including
   against PRs `self_improve.py`/`skillforge_build.py` open on their own.
2. **`agents/redteam.py` + `redteam-deep.yml`** keep probing the live report
   pipeline daily; a regression in `_reconcile_report()`'s protection would
   show up as a new HIGH/CRITICAL finding in `skillforge/memory/findings.jsonl`,
   not silence.
3. **`agents/security_sweep.py`'s coverage-gap tracking** already names
   specific attack techniques (flashloan/oracle, reentrancy, signature
   replay, governance, bridge, and others) that VAPE's own `score()` doesn't
   yet cover, logged as `coverage-gap` findings — real, dated, and open in
   `findings.jsonl` today. `self_improve.py` reads exactly this category
   when it looks for real gaps to propose fixes for.
4. **This document is expected to be edited, not just referenced.** When a
   future audit, redteam finding, or incident changes the threat model, the
   right move is to update this file's tables in the same PR as the fix —
   the same discipline this repo already applies to
   `docs/ARCHITECTURE.md`.
