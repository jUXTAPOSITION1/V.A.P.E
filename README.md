---
title: VAPE - Private Agent
emoji: 🦍
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
---

# V.A.P.E. – VIRTUAL APE PRIVATE EYE

_Full control • Autonomous • Growing_

[![Bounty Cycle](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml)
[![SKILLFORGE Toolcheck](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Agent Commerce Protocol ACP Profile
**Deployment Base Blockchain + Virtuals Protocol**

Tokenized Autonomous Digital Detective

---

## Overview

V.A.P.E. is the Virtual Ape Private Eye, a cutting-edge fully autonomous AI detective engineered for the on-chain ecosystem. Operating on Base and deeply integrated with Virtuals Protocol, he functions as the ultimate private investigator for digital assets.

Equal parts noir detective, blockchain archaeologist, and protocol guardian, V.A.P.E. protects holders, exposes threats, delivers market intelligence, and enforces security across Base, Virtuals, and beyond. All operations remain fully on-chain, trustless, and revenue-generating through ACP.

**X Profile:** [@based_vape](https://x.com/based_vape)

---

## Core Specializations

- **Blockchain Forensics & Asset Tracing** - Track tokens across chains, identify malicious actors
- **Market Intelligence & Alpha Generation** - Real-time DeFi metrics, TVL flows, anomaly detection
- **Protocol Security & Smart Contract Auditing** - Comprehensive contract analysis and vulnerability detection
- **Digital Asset Protection & Threat Intelligence** - Continuous monitoring and threat identification
- **Social & Narrative Intelligence** - X monitoring, sentiment analysis, coordinated attack detection

---

## How It Runs (two cooperating runtimes + a self-improving forge)

- **Python engine** (`agents/`) — runs **hourly in GitHub Actions** (zero-cost, 24/7).
  LLM analysis (Groq Llama 3.1) + Slither static analysis → timestamped reports.
- **Node agent** (`src/`) — a continuous on-chain investigation loop for local/blockchain depth.
- **SKILLFORGE** (`skillforge/`) — self-improving skill+tool ecosystem; 13 verified security
  tools across static / fuzzing / AI-red-team / recon tiers, all on free runners.
- **intel/** — the real-data audit trail (reports, audits, broadcasts, bounty-radar).
- **ACP monitor** — autonomous USDC-escrow revenue via 14 live offerings on Virtuals/Base.

> **Real data only.** Every loop is grounded in live on-chain/market/CVE sources —
> no simulated or hypothetical output.

---

## Project Structure

```
V.A.P.E/
├── agents/                 # Python engine (CI workhorse): run.py, main.py, vape.py, hack.py,
│                           #   acp.py, wallet.py, redteam.py, self_improve.py, *_system.md
├── src/                    # Node agent (continuous investigation lifecycle)
│   ├── agents/vape.js      #   VAPEAgent class + investigation loop
│   ├── blockchain/         #   analyzer.js  (Base RPC activity)
│   ├── security/           #   scanner.js   (threat detection)
│   ├── data-fetchers/      #   fetcher.js   (market metrics)
│   ├── acp/                #   protocol.js  (findings reporting)
│   └── config/             #   logger.js    (pino)
├── skillforge/             # Self-improving skill+tool ecosystem
│   ├── tools/              #   static/ fuzzing/ ai-redteam/ recon/  (13 tools)
│   ├── skills/             #   playbooks (sc-static, ai-redteam, onchain-recon)
│   └── memory/             #   append-only registry + findings/skills/lessons + INDEX
├── intel/                  # Real-data audit trail
│   ├── reports/  audits/  broadcasts/  bounty-radar/  engagements/  catalog/
├── .github/workflows/      # bounty-cycle, skillforge-{harvest,toolcheck,synthesize}, sync-to-hub
├── docs/                   # ARCHITECTURE.md, ACP_PROTOCOL.md, DEPLOYMENT.md, index.html (Pages)
├── app.py                  # Gradio UI (Hugging Face Space)
├── package.json            # Node agent deps/scripts (ESM, main: src/agents/vape.js)
├── requirements.txt        # gradio (UI);  agents/requirements.txt = Python engine deps
└── .env.example            # all referenced env vars (copy to .env)
```

_Tree reflects tracked files (`git ls-files`). Not every claimed-but-empty dir from earlier
drafts exists; this is the real layout._

---

## Quick Start

There are **two run paths** — the Python engine (what CI runs) and the Node agent (local depth).

```bash
git clone https://github.com/jUXTAPOSITION1/V.A.P.E.git
cd V.A.P.E
cp .env.example .env          # fill in real values (gitignored)
```

### Path 1 — Python engine (matches CI; needs only a Groq key)
```bash
pip install -r agents/requirements.txt
python -m agents.run                 # bounty-hunt pass
python -m agents.run --review-repo   # self-review pass
```

### Path 2 — Node agent (continuous on-chain investigation)
```bash
npm install
npm start                            # src/agents/vape.js investigation loop
```

### Path 3 — Just deploy it autonomously (recommended)
Set `GROQ_API_KEY` in **repo Secrets** and enable Actions. The hourly workflows run VAPE
24/7 with zero local compute. Full steps in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system architecture, runtimes, data flow
- [docs/ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) — ACP integration, job lifecycle, 14 offerings
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — deploy the CI engine, Node agent, UI, and ACP monitor
- **Live dashboard:** [Bounty Command Center](https://jUXTAPOSITION1.github.io/V.A.P.E/) (GitHub Pages)

---

## The Chain Never Lies

V.A.P.E makes sure you hear the truth first.

**Let's hunt.** 🔍🦍
# V.A.P.E. + HACK — Autonomous Bug Bounty & Security Agents

**V.A.P.E.** (Virtual Ape Private Eye) — Main detective & forensics agent  
**HACK** — Specialized white-hat bug bounty & security sub-agent (embodied here)

Built 100% from open source. Powered by the best USA-made models (Llama 3.1 via Groq).  
Fully aligned with the detailed profiles below. Designed to run 24/7 via free tiers + GitHub.

See `/agents/` for the actual agent code and system prompts.


