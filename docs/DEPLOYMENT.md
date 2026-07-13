# Deployment Guide

V.A.P.E. runs on free tiers. There are several independently deployable surfaces —
**(A) the autonomous CI engine**, **(C) the UI**, **(D) the ACP job monitor**,
**(E) the x402 payment worker** — plus **(B) local Python runs** for one-off,
non-deployed invocations.

## Prerequisites
- GitHub account (free Actions minutes; public repo = unlimited)
- Groq API key (free) — `GROQ_API_KEY`
- Optional: Gemini key, Etherscan V2 key, Base RPC URL, Virtuals/ACP credentials
- Python 3.11+ (for local Python runs)
- Node.js 18+ (only for the `worker/` Cloudflare Worker, section E)

## 0. Clone & configure
```bash
git clone https://github.com/jUXTAPOSITION1/V.A.P.E.git
cd V.A.P.E
cp .env.example .env       # fill in real values; .env is gitignored
```

---

## A. Autonomous CI engine (recommended — 24/7, zero cost)
The Python engine + SKILLFORGE run entirely in GitHub Actions. No server needed.

### A1. Set repository secrets
`Settings → Secrets and variables → Actions → New repository secret`:

| Secret | Required | Used by |
|---|---|---|
| `GROQ_API_KEY` | [OK] | bounty-cycle, synthesize, redteam, self-improve, skillforge-build — every scheduled LLM call |
| `CEREBRAS_API_KEY` | recommended | `agents/llm.py`'s automatic fallback when Groq rate-limits (free, 1M tokens/day) |
| `OPENROUTER_API_KEY` | optional | further fallback in the same chain (20+ free models) |
| `GEMINI_API_KEY` | optional | frontier tier for the 50 USDC deep-dive audit (`gemini-2.5-pro`); also a fallback in the normal chain |
| `TOGETHER_API_KEY` | optional | last fallback rung in the same chain |
| `ETHERSCAN_API_KEY` | optional | recon toolcheck (contract_recon) |
| `GITHUB_TOKEN` | auto | commits/pushes (injected by Actions) |

> If `GITHUB_TOKEN` is restricted by org policy and pushes fail, add a fine-grained
> **PAT** with `contents: write` as a secret (e.g. `VAPE_PAT`) and reference it in the
> workflow checkout/push step.

> **Set at least one fallback LLM key.** `agents/llm.py` is built as a
> multi-provider chain, but with only `GROQ_API_KEY` configured it's a single
> point of failure in practice — a real rate-limit audit of this repo's own
> `reports/bounty_report_*.md` history found ~3.5% of hourly bounty-cycle
> runs hit "Rate limit persistent. Try later." with Groq alone. Adding
> `CEREBRAS_API_KEY` (free, highest daily quota of the fallbacks, zero code
> changes needed) closes that gap.

### A2. Workflows (already in `.github/workflows/`)
| Workflow | Schedule | Purpose |
|---|---|---|
| `bounty-cycle.yml` | hourly `0 * * * *` | bounty-hunt + self-review → commits reports/ |
| `skillforge-harvest.yml` | hourly `:17` | real CVE + tool-release intel (no LLM) |
| `skillforge-toolcheck.yml` | every 4h `:37` | install+verify 13 security tools (no LLM) |
| `skillforge-synthesize.yml` | daily `06:00` | Groq distill → opens PR |
| `sync-to-hub.yml` | manual/dispatch | mirror to Hugging Face Space |

### A3. Enable & verify
```bash
# Enable Actions in the repo UI, then trigger a manual run:
#   Actions → "VAPE + HACK Bounty + Self-Improvement Cycle" → Run workflow
# Confirm a new file appears under reports/ after the run.
```

---

## B. Local Python run (single pass)
```bash
pip install -r agents/requirements.txt
python -m agents.run                 # bounty mode
python -m agents.run --review-repo   # self-review mode
```

---

## C. UI surfaces
### C1. Hugging Face Space (Gradio)
`app.py` + `requirements.txt` (`gradio`) deploy to a HF Space. The repo auto-mirrors via
`sync-to-hub.yml` (set the `HF_TOKEN` secret). The Space frontmatter lives in the repo
README/Space config.

### C2. GitHub Pages (public site)
`docs/index.html` is VAPE's public site — narrative "case file" pages, live Base/market
data, wallet connect, a wallet profile (portfolio, P&L, cost-basis estimate, case
history), and the hiring panels (x402 + ACP).
Enable Pages: `Settings → Pages → Source: Deploy from branch → main /docs`.
Zero build step — `docs/assets/*.js` are plain files, no bundler required.

---

## D. ACP job monitor (autonomous revenue)
The provider monitor (catch → negotiate → fund → complete) runs on a host with the ACP
CLI configured. One-time setup:
```bash
acp configure                 # auth (one URL click)
acp agent add-signer --policy restricted   # signer (one URL click)
acp offering list             # confirm offerings live
# start the monitor daemons (see acp-monitor/README.md on the host)
```
See `docs/ACP_PROTOCOL.md` for the full lifecycle.

---

## E. x402 payment worker (pay-per-call hiring)
`worker/` is a Cloudflare Worker gating 21 of VAPE's 29 offerings behind Coinbase's x402
HTTP payment protocol (the other 8 need the SKILLFORGE tool tier — hire those via a real
ACP job instead, see section D). Runs on Base mainnet against Coinbase Developer
Platform's hosted facilitator (real funds) — the full pay → verify → settle loop was
proven first on Base Sepolia + the free public facilitator before that switch.
It also hosts five free, unpaid endpoints (`/portfolio`, `/nfts`, `/network-status`,
`/prices`, `/cost-basis`, all Alchemy/CoinGecko-backed) that the site's wallet profile and
metrics strip prefer over direct public-RPC calls once deployed, plus the unpriced
`/x402/feed` and `/x402/stats` live job-ledger showcase. See `worker/README.md` for full
setup; summary:

```bash
cd worker
npm install
npx wrangler login
npx wrangler secret put ETHERSCAN_API_KEY   # optional, only 2 of 6 offerings use it
npx wrangler secret put CDP_API_KEY_ID      # required for real mainnet settlement
npx wrangler secret put CDP_API_KEY_SECRET
npx wrangler secret put ALCHEMY_API_KEY     # optional, powers /portfolio /nfts /network-status /cost-basis
npx wrangler secret put COINGECKO_API_KEY   # optional, powers /prices; required for /cost-basis
npx wrangler deploy
```

### E1. Repository secrets for CI deploy (`.github/workflows/deploy-worker.yml`)
| Secret | Required | Used for |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | [OK] | Workers Scripts: Edit permission |
| `CLOUDFLARE_ACCOUNT_ID` | [OK] | target account |

Without these set, the workflow still runs (checkout, install, typecheck) and skips the
live deploy step rather than failing — safe to merge before you've set up Cloudflare.
The Worker secrets above (`CDP_API_KEY_ID`/etc.) are separate from these — they're set
once via `wrangler secret put`, not as GitHub Actions repo secrets, since the CI job
only builds and deploys code, never runs it.

**Before the first deploy on a fresh Cloudflare account**, claim a `workers.dev`
subdomain from the dashboard (Workers & Pages → Overview) and confirm it shows an active
value (not blank) — `wrangler deploy` cannot register this non-interactively, and this is
the one step that has hit a real account-level Cloudflare bug before (see `worker/README.md`'s
"Cloudflare + Deno Deploy" section). If it recurs, `worker/deno/` runs the identical app
on Deno Deploy as a documented fallback — see E3.

### E2. CDP mainnet credentials
Get a [Coinbase Developer Platform](https://portal.cdp.coinbase.com) Secret API Key —
that's `CDP_API_KEY_ID`/`CDP_API_KEY_SECRET` above. `worker/src/lib/cdpAuth.ts` uses it to sign
the Bearer JWT the facilitator requires on every `/verify` and `/settle` call; without
it, settlement calls go out unauthenticated and CDP returns 401.

### E3. Fallback: Deno Deploy
`worker/deno/deno-entry.ts` + `worker/deno/deno.json` (deliberately its own directory,
not next to `package.json` — see `worker/README.md` for why that matters) run the same
worker code unmodified on [Deno Deploy](https://deno.com/deploy), which assigns a working
`*.deno.dev` URL automatically with no subdomain-registration step. Connect the repo at
dash.deno.com with entry point `worker/deno/deno-entry.ts`, set the same secrets as
environment variables there. Kept live as a documented fallback in case the Cloudflare
account-level subdomain bug recurs — switching is just updating `WORKER_BASE` in
`docs/assets/app.js`/`profile.js` to the Deno URL, no code changes needed either way.

---

## Verification checklist
- [ ] `.env` filled (or secrets set in Actions) — never commit `.env`
- [ ] Manual workflow run produced a new `reports/` file
- [ ] SKILLFORGE toolcheck shows tools verified (Actions log)
- [ ] (Python) `python -m agents.run` connects to Base RPC and logs a cycle
- [ ] (ACP) `acp agent whoami` shows agent + signer; offerings listed
- [ ] (Pages) status dashboard reachable
- [ ] No secrets in git history (`git log -p -- .env` should be empty/placeholder)

## Security notes
- `.env` is gitignored; only `.env.example` (placeholders) is committed.
- Private keys live in GitHub Secrets or 600-perm local files — never in the repo.
- The ACP signer is `restricted`-scoped and per-environment (revocable from the dashboard).
