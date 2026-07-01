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

# 🦍 V.A.P.E. – VIRTUAL APE PRIVATE EYE

> **Full control • Autonomous • Growing • Learning**

[![Bounty Cycle](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml)
[![SKILLFORGE Toolcheck](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml)
[![SKILLFORGE Harvest](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-harvest.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-harvest.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🔍 What is V.A.P.E?

**V.A.P.E.** (Virtual Ape Private Eye) is a **fully autonomous AI detective** engineered for the on-chain ecosystem. Operating on **Base** and deeply integrated with **Virtuals Protocol**, V.A.P.E. is a noir detective meets blockchain archaeologist meets protocol guardian.

### Identity
- **Agent Commerce Protocol (ACP) Profile** — Tokenized autonomous digital detective
- **X Profile:** [@based_vape](https://x.com/based_vape)
- **Capabilities:** Blockchain forensics, market intelligence, protocol security, threat detection, social narrative analysis
- **Philosophy:** Real data only. The chain never lies. V.A.P.E. makes sure you hear the truth first.

---

## 🎯 Core Specializations

| Specialization | What It Does |
|---|---|
| 🔗 **Blockchain Forensics & Asset Tracing** | Track tokens across chains, identify malicious actors, trace fund flows |
| 📊 **Market Intelligence & Alpha Generation** | Real-time DeFi metrics, TVL flows, anomaly detection, whale tracking |
| 🛡️ **Protocol Security & Smart Contract Auditing** | Comprehensive contract analysis, vulnerability detection, exploit simulation |
| 🚨 **Threat Intelligence & Digital Asset Protection** | Continuous monitoring, threat identification, crisis detection & response |
| 📢 **Social & Narrative Intelligence** | X/Twitter monitoring, sentiment analysis, coordinated attack detection |

---

## 🏗️ Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│              🌐 REAL-TIME DATA SOURCES                      │
│  Base RPC • Etherscan • DexScreener • GoPlus • CoinGecko    │
│  DeFiLlama • CVE Feeds • GitHub Issues • X/Twitter • MCP     │
└────────────────┬────────────────────────────────────────────┘
                 │
      ┌──────────┼──────────┬──────────────┐
      │          │          │              │
      ▼          ▼          ▼              ▼
   ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
   │ PYTHON │ │ NODE   │ │SKILLFORGE│ │  MCP   │
   │ ENGINE │ │ AGENT  │ │ MEMORY   │ │ TOOLS  │
   │ (CI)   │ │(LOCAL) │ │ BUILDER  │ │(GitHub)│
   └───┬────┘ └───┬────┘ └────┬─────┘ └───┬────┘
       │          │           │           │
       └──────────┼───────────┴───────────┘
                  │
         ┌────────▼─────────┐
         │  MEMORY SYSTEM   │
         │ (Append-only)    │
         │  FINDINGS        │
         │  SKILLS          │
         │  LESSONS         │
         │  SOCIAL_EVENTS   │
         └────────┬─────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
   intel/    GitHub PRs   Broadcasts
   Reports   (Builder)    (UI)
```

### 🚀 Four Interconnected Systems

#### 1. **Python Engine** (`agents/`)
Runs **hourly in GitHub Actions** (zero-cost, 24/7)
- **run.py** — Single-pass bounty analysis + LLM reasoning
- **vape.py / hack.py** — Detective + security personas
- **Multi-provider LLM layer** — Groq → Cerebras → OpenRouter → GitHub Models → Together (automatic failover)
- **Slither integration** — Static analysis + fuzzing on free runners
- Output: Timestamped security reports

#### 2. **Node Agent** (`src/`)
Continuous on-chain investigation (local or persistent daemon)
- Real-time Base RPC monitoring
- Live threat detection + anomaly scoring
- Integration with ACP for job reporting
- ESM-based, runs standalone or in CI

#### 3. **SKILLFORGE** (`skillforge/`)
Self-improving skill + tool ecosystem
- **Memory System** — Append-only audit trail of findings, skills, lessons, social events
- **Builder** — Autonomous code generation grounded in memory + repo patterns
- **13 verified security tools** — Slither, Aderyn, Mythril, Echidna, Foundry, Garak, etc.
- **Auto-PR generation** — High-confidence outputs automatically proposed
- **Harvest** (hourly) + **Toolcheck** (6×/day) + **Synthesize** (daily)

#### 4. **MCP Integration** (`skillforge/mcp/`)
External tool access with safety rails
- **GitHub MCP** — Search issues, read files, create PRs autonomously
- **Twitter MCP** — Monitor mentions, detect social threats, feed sentiment to Memory
- **Rate limiting** — Respect API quotas, graceful backoff
- **Result storage** — All MCP outputs auto-append to Memory for cross-module access

---

## 📁 Project Structure

```
V.A.P.E/
├── agents/                          # Python engine (CI workhorse)
│   ├── run.py                       #   Main orchestrator
│   ├── vape.py / hack.py            #   Detective + security personas
│   ├── builder.py                   #   🆕 Autonomous code generation
│   ├── llm.py                       #   Multi-provider LLM failover
│   ├── data_fetchers.py             #   Real-time market/chain data
│   ├── acp_fulfill.py               #   ACP job execution
│   ├── vape_system.md / hack_system.md #   System prompts
│   ├── builder_system.md            #   🆕 Builder prompt & philosophy
│   └── requirements.txt             #   Python deps
│
├── skillforge/                      # Self-improving skill ecosystem
│   ├── memory/
│   │   ├── retriever.py             #   🆕 Append-only audit trail
│   │   ├── memory.jsonl             #   🆕 Git-tracked findings/skills
│   │   └── README.md                #   🆕 Memory API guide
│   │
│   ├── mcp/
│   │   ├── integration.py           #   🆕 GitHub + Twitter MCP tools
│   │   └── README.md                #   🆕 MCP integration guide
│   │
│   ├── tools/                       #   13 security tools (static/fuzzing/ai/recon)
│   ├── skills/                      #   Playbooks (sc-static, ai-redteam, recon)
│   ├── harvest.py                   #   CVE + tool release intelligence
│   ├── toolcheck.py                 #   Verify all tools on free runners
│   ├── synthesize.py                #   Distill knowledge → PR
│   └── MANIFEST.md                  #   Tool registry
│
├── src/                             # Node agent (continuous investigation)
│   ├── agents/vape.js               #   Investigation loop
│   ├── blockchain/analyzer.js       #   Base RPC analysis
│   ├── security/scanner.js          #   Threat detection
│   ├── data-fetchers/               #   Market metrics
│   └── acp/protocol.js              #   ACP reporting
│
├── intel/                           # Real-data audit trail
│   ├── reports/                     #   Hourly security/sentiment/base/macro sweeps
│   ├── audits/                      #   In-depth audit reports
│   ├── broadcasts/                  #   Community-facing intel
│   ├── bounty-radar/                #   Bounty opportunity tracking
│   └── catalog/                     #   Investigation catalog
│
├── .github/workflows/               # Continuous automation
│   ├── bounty-cycle.yml             #   Hourly bounty detection
│   ├── skillforge-harvest.yml       #   CVE intelligence (hourly)
│   ├── skillforge-toolcheck.yml     #   Tool verification (6×/day)
│   ├── skillforge-synthesize.yml    #   Synthesis → PR (daily)
│   └── sync-to-hub.yml              #   Sync to Hugging Face Space
│
├── docs/                            # Comprehensive documentation
│   ├── ARCHITECTURE.md              #   System design & data flow
│   ├── ARCHITECTURE_ROADMAP.md      #   Evolution & future phases
│   ├── ACP_PROTOCOL.md              #   ACP integration details
│   ├── DEPLOYMENT.md                #   How to deploy VAPE
│   └── index.html                   #   Bounty Command Center (GitHub Pages)
│
├── app.py                           # Gradio UI (Hugging Face Space)
├── package.json                     # Node deps + scripts
├── requirements.txt                 # Root Python deps (gradio)
├── agents/requirements.txt          # Python engine deps
├── .env.example                     # All required environment variables
└── README.md                        # This file
```

---

## 🚀 Quick Start

### Prerequisites
```bash
git clone https://github.com/jUXTAPOSITION1/V.A.P.E.git
cd V.A.P.E
cp .env.example .env                 # Fill in real values
```

### Option 1: Python Engine (Local)
Matches what GitHub Actions runs. Minimal setup (just needs Groq API key).

```bash
pip install -r agents/requirements.txt
python -m agents.run                 # Run bounty analysis pass
python -m agents.run --review-repo   # Run self-review pass
```

### Option 2: Node Agent (Local)
Continuous on-chain investigation for deeper analysis.

```bash
npm install
npm start                             # src/agents/vape.js investigation loop
```

### Option 3: Deploy Autonomously (Recommended) ⭐
Zero local compute. GitHub Actions runs everything 24/7.

```bash
# 1. Set GROQ_API_KEY in GitHub Secrets
# 2. Enable Actions in your fork
# 3. Done! Workflows run hourly + 6×/day + daily automatically
```

Full deployment instructions: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 🧠 Memory System (New!)

V.A.P.E. now has a **central long-term brain**. Every module (detective, builder, MCP tools) feeds into and pulls from an append-only Memory registry.

### What Gets Stored
- **Findings** — Vulnerabilities, exploits, threats discovered
- **Skills** — Generated tools, techniques, playbooks
- **Lessons** — Patterns learned, improvements, best practices
- **Social Events** — Twitter signals, market sentiment, narratives
- **Code Patterns** — Recurring contract patterns, PoCs
- **Market Intel** — TVL movements, whale activity

### Key API
```python
from skillforge.memory.retriever import search_memory, append_to_memory

# Detective searches for similar past findings
matches = search_memory("reentrancy vulnerability", category="findings", limit=5)

# Builder auto-learns generated tools
append_to_memory("skills", {
    "name": "exploit_simulator",
    "code": "...",
}, source="builder", tags=["exploit"])
```

👉 See [skillforge/memory/README.md](skillforge/memory/README.md) for full guide.

---

## 🤖 Builder Module (New!)

Autonomous code generation grounded in memory + repo patterns.

### How It Works
1. **Search Memory** for similar past tools/patterns
2. **Ground in Context** — Use past lessons + repo patterns
3. **Generate Code** — Via multi-provider LLM layer
4. **Validate** — Syntax + security checks
5. **Auto-Append** — Store in Memory for reuse
6. **Auto-PR** — High-confidence outputs auto-proposed

```python
from agents.builder import Builder

builder = Builder(tier="deep")
code = builder.generate_tool(
    task="Create Foundry script for exploit PoC",
    language="python",
    review_required=False,
)
# ✅ Tool generated, validated, learned, and PR opened!
```

👉 See [agents/builder_system.md](agents/builder_system.md) for detailed philosophy.

---

## 🔌 MCP Integration (New!)

Model Context Protocol tools for autonomous GitHub + Twitter access.

### Available Tools

**GitHub MCP:**
- Search issues, read files, list repo structure
- Auto-check if similar tools already exist
- Autonomous PR creation for validated outputs

**Twitter/X MCP:**
- Search tweets, monitor mentions
- Sentiment analysis (bearish/neutral/bullish)
- Auto-feed social signals into Memory

### Usage
```python
from skillforge.mcp.integration import mcp_manager, MCPTool

# Check Twitter for security threats
result = mcp_manager.call(
    MCPTool.TWITTER,
    "search_tweets",
    {"query": "Base blockchain exploit", "limit": 20}
)
# Result auto-stored in Memory, can trigger analysis
```

👉 See [skillforge/mcp/README.md](skillforge/mcp/README.md) for setup + patterns.

---

## 📚 Documentation

| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, runtimes, data flow, component details |
| [docs/ARCHITECTURE_ROADMAP.md](docs/ARCHITECTURE_ROADMAP.md) | Future phases, evolution, scaling plans |
| [docs/ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) | ACP integration, job lifecycle, 14 live offerings |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Step-by-step deployment: CI, Node agent, UI, ACP monitor |
| [skillforge/memory/README.md](skillforge/memory/README.md) | Memory system API, integration patterns |
| [agents/builder_system.md](agents/builder_system.md) | Builder philosophy, grounding, validation |
| [skillforge/mcp/README.md](skillforge/mcp/README.md) | MCP tools, setup, rate limits, troubleshooting |

---

## 🎮 Live Dashboard

**Bounty Command Center:** [https://jUXTAPOSITION1.github.io/V.A.P.E/](https://jUXTAPOSITION1.github.io/V.A.P.E/)

Status, recent findings, threat levels, all in one place.

---

## 🔄 How It All Works Together

### Typical Hourly Cycle

```
⏰ Hourly trigger (GitHub Actions)
  ↓
🔍 Python Engine runs bounty analysis
  - Query Memory for similar past findings
  - Fetch real market/chain data
  - Run Slither static analysis
  - LLM reasoning → findings
  ↓
💾 Store findings in Memory
  - Append to memory.jsonl (git-tracked audit trail)
  - Tag by severity, chain, protocol
  ↓
🧠 MCP Tools activate
  - GitHub MCP: Search for related issues
  - Twitter MCP: Monitor for social signals
  - Results stored in Memory
  ↓
🤖 Builder evaluates
  - Need new tool? Search Memory for similar ones
  - If not found, generate + validate + store
  - Auto-PR if high confidence
  ↓
📝 Reports generated
  - intel/reports/security-YYYY-MM-DD-HH.md
  - intel/reports/sentiment-YYYY-MM-DD-HH.md
  - etc.
  ↓
📤 Sync to Hub
  - Findings broadcast to Hugging Face Space
  - Community notified via X/Twitter
```

### Data Flow: Memory as Central Hub

```
Detective Analysis → Memory ← Builder Outputs
                      ↑
                      │
                  MCP Tools
```

Every component queries Memory before acting. Every success is stored for future reuse. True compounding intelligence.

---

## 🛠️ Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# LLM (required for Python engine)
GROQ_API_KEY=gsk_...                    # Groq (primary)
CEREBRAS_API_KEY=ceba-...              # Cerebras (fallback)
OPENROUTER_API_KEY=sk-or-...           # OpenRouter (fallback)
GITHUB_MODELS_TOKEN=ghp_...            # GitHub Models (fallback)
TOGETHER_API_KEY=together_...          # Together (fallback)

# GitHub (for MCP + code access)
GITHUB_TOKEN=ghp_...                   # GitHub PAT (public_repo scope)

# Twitter/X (for social signals)
TWITTER_BEARER_TOKEN=AAAA...           # X API v2 Bearer Token

# Optional: On-chain data
BASE_RPC_URL=https://...               # Base RPC endpoint
ETHERSCAN_API_KEY=...                  # Etherscan API (token info)

# Optional: ACP / Wallet
VIRTUALS_API_KEY=...                   # Virtuals Protocol access
WALLET_PRIVATE_KEY=...                 # For ACP job execution (never commit!)
```

All values are `.gitignore`'d. See `.env.example` for full list.

---

## 🏆 Key Stats

| Metric | Value |
|---|---|
| **Runtimes** | 2 (Python CI + Node local) |
| **Compute Cost** | $0/month (GitHub Actions free tier + Groq free) |
| **Security Tools** | 13 verified open-source tools |
| **Memory Categories** | 7 (findings, skills, lessons, social, patterns, market, acp) |
| **MCP Tools** | 2 (GitHub, Twitter) + extensible |
| **Uptime** | 24/7 via GitHub Actions + optional local daemon |
| **Report Types** | 8 (security, sentiment, base, virtuals, macro, deep-dive, broadcast, agent-update) |

---

## 🔐 Security & Philosophy

### Core Principles
1. **Real data only** — No simulations, hypotheticals, or hallucinations
2. **Zero-cost operation** — Free tiers + open source only (no paid APIs)
3. **Autonomous but auditable** — Full git history of all findings + decisions
4. **Memory-first** — Learn from past work, reduce redundancy
5. **Security hardened** — Input validation, error handling, no secrets in logs
6. **Open source** — Built on verified open-source tools (Slither, Foundry, etc.)

### What's Built In
- ✅ Multi-provider LLM fallback (never rate-limited)
- ✅ Rate limiting on MCP tools (respect API quotas)
- ✅ Input sanitization on all external data
- ✅ No hardcoded API keys (env vars only)
- ✅ Comprehensive logging (audit trail)
- ✅ Graceful error handling (retries, backoff)

---

## 🚦 Getting Help

| Issue | Resource |
|---|---|
| Deployment questions | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |
| Architecture details | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Memory system | [skillforge/memory/README.md](skillforge/memory/README.md) |
| Builder module | [agents/builder_system.md](agents/builder_system.md) |
| MCP integration | [skillforge/mcp/README.md](skillforge/mcp/README.md) |
| Bug report | [GitHub Issues](https://github.com/jUXTAPOSITION1/V.A.P.E/issues) |
| X/Twitter | [@based_vape](https://x.com/based_vape) |

---

## 📊 Recent Activity

See [intel/reports/](intel/reports/) for the latest:
- 🔴 Security threat alerts
- 📈 Market anomalies
- 🐦 Social sentiment analysis
- 🔗 Base chain health
- 💬 Protocol updates

---

## 🎓 Learn More

- **[Virtuals Protocol](https://www.virtuals.io)** — Agent Commerce Protocol
- **[Base Chain](https://base.org)** — Ethereum L2
- **[Groq](https://groq.com)** — Fast LLM inference
- **[Slither](https://github.com/crytic/slither)** — Smart contract static analysis
- **[Foundry](https://getfoundry.sh)** — Solidity development & testing

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

V.A.P.E. is autonomous-first, but contributions welcome!

- Bug fixes → PR
- New tools → Via Builder module (auto-learns + proposes PR)
- Ideas → [GitHub Issues](https://github.com/jUXTAPOSITION1/V.A.P.E/issues)
- Security issues → [@based_vape](https://x.com/based_vape) or see [CONTRIBUTING.md](CONTRIBUTING.md)

---

<div align="center">

### The Chain Never Lies.
### V.A.P.E. Makes Sure You Hear the Truth First.

**Let's hunt.** 🔍🦍

---

**Status:** 🟢 Active & Growing  
**Last Updated:** 2026-07-01  
**Next Review:** Weekly via self-improvement workflows

</div>
