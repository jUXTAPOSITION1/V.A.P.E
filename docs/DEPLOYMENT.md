# Deployment Guide

V.A.P.E. runs on free tiers. There are three independently deployable surfaces:
**(A) the autonomous CI engine**, **(B) the local Node agent**, **(C) the UI**.

## Prerequisites
- GitHub account (free Actions minutes; public repo = unlimited)
- Groq API key (free) — `GROQ_API_KEY`
- Optional: Gemini key, Etherscan V2 key, Base RPC URL, Virtuals/ACP credentials
- Node.js 18+ (only for the local Node agent)
- Python 3.11+ (for local Python runs)

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
| `GROQ_API_KEY` | ✅ | bounty-cycle, synthesize |
| `GEMINI_API_KEY` | ⬜ | intel web_search |
| `ETHERSCAN_API_KEY` | ⬜ | recon toolcheck (contract_recon) |
| `GITHUB_TOKEN` | auto | commits/pushes (injected by Actions) |

> If `GITHUB_TOKEN` is restricted by org policy and pushes fail, add a fine-grained
> **PAT** with `contents: write` as a secret (e.g. `VAPE_PAT`) and reference it in the
> workflow checkout/push step.

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

## B. Local Node agent (continuous investigation, blockchain depth)
For long-running on-chain monitoring beyond the hourly CI pass.

```bash
npm install
npm run setup-wallet     # one-time wallet setup (if applicable)
npm start                # starts VAPEAgent investigation loop (src/agents/vape.js)
# dev mode with reload:
npm run dev
```
Reads `BASE_RPC_URL`, `VIRTUALS_API_KEY`, `CHECK_INTERVAL`, `MAX_CASES_PER_RUN`, `LOG_LEVEL`
from `.env`. Read-only by default (no signing).

### Local Python run (single pass)
```bash
pip install -r agents/requirements.txt
python -m agents.run                 # bounty mode
python -m agents.run --review-repo   # self-review mode
python -m agents.main                # VAPE + HACK over fetched bounties
```

---

## C. UI surfaces
### C1. Hugging Face Space (Gradio)
`app.py` + `requirements.txt` (`gradio`) deploy to a HF Space. The repo auto-mirrors via
`sync-to-hub.yml` (set the `HF_TOKEN` secret). The Space frontmatter lives in the repo
README/Space config.

### C2. GitHub Pages (status dashboard)
`docs/index.html` is the "Bounty Command Center". Enable Pages:
`Settings → Pages → Source: Deploy from branch → main /docs`.

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

## Verification checklist
- [ ] `.env` filled (or secrets set in Actions) — never commit `.env`
- [ ] Manual workflow run produced a new `reports/` file
- [ ] SKILLFORGE toolcheck shows tools verified (Actions log)
- [ ] (Node) `npm start` connects to Base RPC and logs a cycle
- [ ] (ACP) `acp agent whoami` shows agent + signer; offerings listed
- [ ] (Pages) status dashboard reachable
- [ ] No secrets in git history (`git log -p -- .env` should be empty/placeholder)

## Security notes
- `.env` is gitignored; only `.env.example` (placeholders) is committed.
- Private keys live in GitHub Secrets or 600-perm local files — never in the repo.
- The ACP signer is `restricted`-scoped and per-environment (revocable from the dashboard).
