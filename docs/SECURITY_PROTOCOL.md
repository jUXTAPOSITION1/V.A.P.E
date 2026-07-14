# VAPE Security & Intel Protocol

VAPE is an autonomous agent that holds a real wallet, spends real API/LLM
budget on a schedule, reads attacker-controlled on-chain data as part of its
job, and opens real PRs against its own source. This document is the single
place that threat model lives — what's actually being defended, what already
defends it, what the 2026-07-13 repo-wide audit (and the 2026-07-14
follow-up) found and fixed, and how this keeps evolving instead of going
stale the way a one-time audit report does.

Every claim below is grounded in a real file/line in this repo as of its
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
- **CI regression**: `security-lint.yml` runs two complementary checks on
  every workflow-touching PR — `scripts/security_lint.py` (deterministic,
  checks the exact classes this repo's own audits have found; see below)
  and `zizmor` (a maintained, general-purpose GitHub Actions static
  analyzer; added 2026-07-14 — see that date's section below for why a
  narrow custom linter alone wasn't enough).
- **LLM spend runaway**: `agents/llm.py::ask()` (added 2026-07-14) enforces
  a daily $ cap on `xai_1` (Grok, the only provider that's real money —
  everything else in `PROVIDERS` is free/quota-limited) computed from the
  same `llm_usage.jsonl` telemetry every provider already writes to; a
  provider over cap is skipped in favor of the free chain, and a finding is
  logged once per day so it doesn't happen silently. See that date's
  section below.
- **Findings-log tamper-evidence**: `findings-seal.yml` (every 6h) hash-
  chains `findings.jsonl` via `skillforge/findings_chain.py` — an edit or
  deletion in an already-sealed range fails the next verify loudly, added
  2026-07-14 (see that date's section below).
- **Builder code-generation prompt injection**: `agents/redteam_builder.py`
  (daily, alongside `agents/redteam.py` in `redteam.yml`) runs real
  adversarial payloads through a poisoned Memory entry into Builder's real
  code-generation path, judging the actual generated code against
  `validate_security()` — added 2026-07-14, see that date's section below.

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
2. **Unframed contract source in an LLM prompt** — both
   `agents/acp_fulfill.py::_ai_quick_review` AND its worker-side twin
   `worker/src/handlers.ts::aiQuickReview` embed a verified contract's
   deployer-controlled source directly into a prompt. The Python side was
   fixed first; CodeRabbit's review of that fix (correctly) pointed out the
   TypeScript copy mirrors it exactly and was still unframed. Capped at a
   misleading summary paragraph rather than fund loss either way (the
   deterministic score/verdict fields are computed separately and can't be
   overridden this way). Fixed: added the same explicit inert-data framing
   to both `_AI_QUICK_REVIEW_SYSTEM` (Python) and `AI_QUICK_REVIEW_SYSTEM`
   (TypeScript).
3. **Shell-injection anti-pattern, including a residual instance CodeRabbit
   caught in its own review of the fix** — `review-ledger.yml` and
   `x402-index-claim.yml` interpolated `workflow_dispatch` inputs directly
   into `run:` steps instead of routing through `env:` first. Fixed both,
   plus one more instance caught by the new linter in `build-request.yml` —
   but the FIRST fix to `review-ledger.yml` only routed the raw
   `github.event.inputs.*` through `env:` in the step that computes
   `categories`/`sample`; the NEXT step then re-interpolated that step's
   *output* (`${{ steps.cats.outputs.categories }}`) straight into `run:`
   again, reopening the identical injection in a job that carries every
   LLM/research API key plus `DATA_AGENT_PRIVATE_KEY` and `contents: write`.
   Fixed by routing the step output through `env:` too. This class
   (`steps.*.outputs.*` re-interpolation) is a deliberate blind spot in
   `security_lint.py` — see its docstring for why.
4. **Unpinned third-party Action with live deploy credentials** —
   `cloudflare/wrangler-action@v4` ran with `CLOUDFLARE_API_TOKEN`/
   `CLOUDFLARE_ACCOUNT_ID` on every push to `main` touching `worker/**`,
   pinned only to a mutable tag. Fixed: pinned to the tag's current commit
   SHA (verified against the GitHub API at fix time), with a comment on how
   to re-pin deliberately later. `denoland/setup-deno@v2` (no secrets in
   that job, lower severity) was pinned too for consistency.
5. **No dependency scanning for `worker/`** — the only Node project handling
   real payment logic had zero CVE scanning anywhere in CI. Fixed: added
   `npm audit` to `dependency-audit.yml` (as its own step, separate from
   `npm ci`, so a lockfile failure can't silently skip the audit and leave
   an empty section in the auto-filed issue — another CodeRabbit catch) and
   an `npm`/`/worker` entry to `dependabot.yml`.
6. **Missing `persist-credentials: false` across 16 secret-carrying jobs**
   (CWE-522) — `actions/checkout`'s default persists `GITHUB_TOKEN` in
   local git config for the rest of the job. CodeRabbit's review (via
   zizmor, a dedicated GitHub Actions security linter) first flagged this on
   `security-lint.yml` itself — that particular job carries no secrets, so
   it was a consistency/hygiene ask there, not a live CWE-522 — but checking
   every OTHER workflow found 16 jobs across 15 files that carry real
   secrets (every LLM/research API key, `DATA_AGENT_PRIVATE_KEY`,
   `CLOUDFLARE_API_TOKEN`, `GH_TOKEN`) and were still missing it, out of 20
   secret-carrying jobs total. Fixed all of them; `security_lint.py` now
   checks for this going forward (see below) so it can't silently regress
   one job at a time.

**Confirmed clean, no fix needed**: private-key handling
(`agents/data_agent.py`'s `DATA_AGENT_PRIVATE_KEY` — never logged, never
prompted to an LLM, never influenced by untrusted data; the ACP/x402 flows
never touch a buyer's key); `.env` tracking; MCP server registry (static,
maintainer-only); `skillforge/toolcheck.py` (the "free tool checker" flagged
going into this audit — cron/dispatch-only trigger, fixed maintainer-curated
registry, per-call subprocess timeouts, not externally reachable); the
existing `agents/llm.py` provider-fallback chain (bounded retries, no
runaway-retry gap — the separate aggregate-$-spend gap this left open was
closed in the 2026-07-14 follow-up below).

## What this follow-up audit found and fixed (2026-07-14)

A second pass — prompted by an external review of this same document,
verified against the actual code rather than taken at face value — closed
every genuinely open item it raised except one architectural trade-off
(narrative templating, already named above and still deliberately
deferred):

1. **No aggregate $ spend cap across LLM providers** (the gap this document
   itself named on 2026-07-13). `agents/llm.py` already logged every call's
   token usage to `llm_usage.jsonl`, but nothing read it back to bound total
   spend. Fixed: `PROVIDER_PRICING_USD_PER_M_TOKENS` prices `xai_1` (Grok,
   the only real-money provider — verified against public xAI API pricing,
   $0.20/$0.50 per 1M input/output tokens as of 2026-07) and `ask()` now
   sums that provider's spend for the current UTC day before every call,
   skipping it (falling through to the free chain) once
   `XAI_DAILY_SPEND_CAP_USD` (default $3.00 — generous relative to real
   historical usage, sized to catch a genuine runaway, not throttle normal
   operation) is reached. A `MEDIUM` finding is logged to `findings.jsonl`
   the first time this fires each day (deduplicated so it doesn't spam on
   every subsequent call) so a cap being hit is visible, not silent.
2. **zizmor wasn't actually wired into CI.** `security_lint.py`'s own
   docstring names classes it deliberately doesn't check (e.g.
   `steps.*.outputs.*` re-interpolation); zizmor had only ever been run
   once, ad-hoc, by a CodeRabbit review (see item 6 in the 2026-07-13
   section above) — nothing stopped a new instance of what it caught from
   coming back. Fixed: added a `zizmor` job to `security-lint.yml` (pinned
   to `zizmorcore/zizmor-action@192e21d7...` / v0.5.7, verified against the
   action's real README at fix time), `persona: pedantic`, `min-severity:
   medium`, uploading results to GitHub code scanning rather than failing
   the build outright — broader/heuristic coverage than the narrow
   deterministic `lint` job, so it's additive visibility, not a second copy
   of the same hard gate.
3. **No tamper-evidence on `findings.jsonl`** — VAPE's published
   findings/coverage-gap log, read by `self_improve.py` to decide what to
   act on, had no way to detect an edit or deletion after the fact.
   Six-plus call sites write to it their own way (`agents/redteam.py`,
   `skillforge/harvest.py`, the `ai-redteam` tools, `agents/llm.py`'s new
   spend-cap alert, plus `skillforge/memory/retriever.py`'s shared
   `append_to_memory()`), so making tamper-evidence meaningful at the
   per-entry level would mean migrating all of them onto one write path —
   a much bigger, riskier refactor than this gap actually calls for. Fixed
   instead with `skillforge/findings_chain.py`: treats `findings.jsonl` as
   an opaque append-only text file and periodically "seals" it (hashes
   every line added since the last seal, chained to the previous seal's
   hash, recorded in a new `findings.chain.jsonl`); verifying re-derives
   each seal's hash from the file's *current* content, so an edit or
   deletion inside an already-sealed range no longer matches. Runs every 6
   hours via `findings-seal.yml`, which verifies (failing loudly on
   tampering) before sealing anything new.
4. **`agents/redteam.py`'s daily adversarial probing only covered the
   report pipeline** — the autonomous code-generation path
   (`agents/builder.py`) had no adversarial testing at all. Concrete,
   evidence-based target found by reading the code (same bar
   `agents/redteam.py` itself holds to): `Builder._ground_in_memory()`
   embeds Memory search results directly into the LLM prompt with zero
   "treat this as inert data" framing — and Memory entries can originate
   from processing untrusted external data (e.g. `security_sweep.py`'s
   DeFiLlama hack-feed descriptions), so a poisoned entry reaching a
   future, unrelated Builder task is a real path, not a hypothetical one.
   Fixed: `agents/redteam_builder.py` runs two real adversarial payloads
   through a poisoned Memory entry (mocked via `search_memory`, never
   written to the real files) into a real LLM call, then judges the actual
   extracted code against `validate_security()` — the deterministic
   backstop `generate_code()` applies before returning anything. Building
   this test found a concrete gap in `validate_security()` itself:
   `BLOCK_PATTERNS` blocked `subprocess.call/Popen/run` but not
   `subprocess.check_output`/`check_call` — same shell-execution risk
   family, just omitted — fixed in the same change, with the new test
   payload regression-testing exactly that fix. A second, known limitation
   (`getattr(__builtins__, 'ev'+'al')` evades substring matching entirely)
   is deliberately NOT patched with more string rules — pure pattern
   matching can't close a class of bypass like this; it needs AST-based
   analysis, a real future project, not a quick string addition — so this
   is tracked as a live, dated, real finding every time the model actually
   produces it, the same evidence-based standard the rest of this
   document holds itself to, rather than silently pattern-matched away.
   Wired into the existing daily `redteam.yml` schedule alongside
   `agents/redteam.py`, not a new workflow.

No further items from that review are open — everything it raised is
either fixed above, the one architectural trade-off already named, or the
memory-growth item below.

- **Memory growth / retention policy for `skillforge/memory/*.jsonl`.**
  Total memory footprint today is under 500KB (`findings.jsonl` is the
  largest at ~300KB) — real long-term concern, not a current one, so
  deferred rather than building a compaction policy against a problem that
  doesn't exist yet.

## Known, accepted gaps (not fixed here — stated, not hidden)

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
protocol — it's a report. These make this one keep working after today:

1. **`security-lint.yml` / `scripts/security_lint.py`** — runs on every PR
   touching `.github/workflows/**`, deterministically re-checking for five
   regression classes: pwn-request triggers, unpinned third-party Actions
   *or reusable workflows* with secrets (including `secrets: inherit`), raw
   `github.event.*`/`inputs.*` interpolation into `run:` (dot OR bracket
   notation), missing `permissions:` blocks, and missing
   `persist-credentials: false` on checkout in secret-carrying jobs. The
   linter itself went through its own round of CodeRabbit review before
   this doc was finalized — the bracket-notation gap, the reusable-workflow
   gap, and the persist-credentials check were all added in response to
   real findings against the linter's *first* version, not invented gaps.
   This is the mechanism that stops today's fixes from quietly rotting —
   including against PRs `self_improve.py`/`skillforge_build.py` open on
   their own.
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
5. **`agents/redteam_builder.py`** (added 2026-07-14) keeps probing
   Builder's code-generation path daily alongside `agents/redteam.py`; a
   regression in `validate_security()` would show up as a new HIGH/CRITICAL
   finding, not silence — and its known getattr-indirection gap (see that
   date's section) staying open and dated in `findings.jsonl` is itself the
   honest signal that a real AST-based fix is still owed, not forgotten.
6. **`findings-seal.yml`** (added 2026-07-14) verifies the findings hash
   chain before sealing anything new, every 6 hours — a tampered
   `findings.jsonl` fails that job loudly rather than the tampering just
   sitting there unnoticed until someone happens to diff a backup.
