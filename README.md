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

<div align="center">

# 🦍 V.A.P.E.
### VIRTUAL APE PRIVATE EYE

**The chain never lies. V.A.P.E. makes sure you hear the truth first.**

_Autonomous • Self-Improving • Interconnected Intelligence • Zero Local Compute_

<br/>

[![Bounty Cycle](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml)
[![SKILLFORGE Toolcheck](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Chain](https://img.shields.io/badge/Base-0052FF?style=flat&logo=coinbase&logoColor=white)
![Protocol](https://img.shields.io/badge/Virtuals-ACP-6E56CF?style=flat)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![LLM](https://img.shields.io/badge/LLM-multi--provider-00A67E?style=flat)
![Compute](https://img.shields.io/badge/local%20compute-%240-brightgreen?style=flat)

<br/>

**Tokenized Autonomous Digital Detective** · Deployed on **Base** + **Virtuals Protocol (ACP)**

[🎯 Overview](#-overview) · [🏗️ Architecture](#-architecture-july-2026-release) · [🚀 Quick Start](#-quick-start) · [🧠 Memory](docs/MEMORY.md) · [🔨 Builder](docs/BUILDER.md) · [🔌 MCP](docs/MCP.md) · [🐦 @based_vape](https://x.com/based_vape)

</div>

---

## 🎯 Overview

V.A.P.E. is the Virtual Ape Private Eye, a **fully autonomous AI detective engineered for the on-chain ecosystem**. Operating 24/7 on Base and deeply integrated with Virtuals Protocol's Agent Commerce Protocol (ACP), V.A.P.E. delivers **real-time security intelligence, market alpha, and protocol monitoring** at zero local compute cost.

**As of July 2026:** V.A.P.E. now runs with **interconnected intelligence** — a Central Memory system that grounds all analysis in past findings and lessons, a self-improving Builder that generates new security tools, and MCP wrappers for safe external data access (GitHub, X/social, tool registries). Every cycle compounds intelligence.

**X Profile:** [@based_vape](https://x.com/based_vape)

---

## 🔍 Core Specializations

- **Blockchain Forensics & Asset Tracing** — Track tokens, identify malicious actors, analyze on-chain flows
- **Market Intelligence & Alpha Generation** — Real-time TVL, liquidity, anomaly detection, DeFi metrics
- **Protocol Security & Smart Contract Auditing** — AI red-teaming + static analysis (slither, aderyn, mythril)
- **Digital Asset Protection & Threat Intelligence** — Continuous monitoring, vulnerability feeds, CVE correlation
- **Social & Narrative Intelligence** — X sentiment tracking, narrative shifts, coordinated attack detection
- **Self-Improvement & Skill Generation** — Builder generates new playbooks grounded in Memory + past lessons
- **Autonomous Deep Investigations** — every cycle VAPE auto-selects the highest-signal Base target, runs multi-source recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · hack-feed correlation), scores it 0–100, and files a verdict (🟢 PROCEED / 🟡 CAUTION / 🔴 REJECT) to Memory + the live dashboard

---

## 🏗️ Architecture (July 2026 Release)

### Three Interconnected Systems

```
┌─────────────────────────────────────────────────────────────┐
│           CENTRAL MEMORY (General-Purpose Brain)             │
│    Append-only intelligence layer. Any component queries &   │
│    appends findings, lessons, skills, social events.         │
│    Every finding → future runs get grounded in Memory.       │
└──────────────────┬──────────────────────────────────────────┘
                   │ (queries & appends)
        ┌──────────┼──────────┐
        │          │          │
    ┌───▼────┐  ┌──▼────┐  ┌─▼──────┐
    │DETECTIVE│  │BUILDER│  │MCP     │
    │(agents) │  │ (self-│  │(GitHub,│
    │  run.py │  │ improv)│  │Social, │
    │ vape.py │  │Generate│  │Tools)  │
    └────┬────┘  │code &  │  └──┬────┘
    (LLM +      │skills  │     (safe
    data        │grounded│     external
    fetchers)   │in Memory│    data)
         │      └────┬────┘     │
         │           │           │
         └───────────┼───────────┘
                     │
            ┌────────▼─────────┐
            │  SKILLFORGE      │
            │  (self-growing   │
            │   tool+skill     │
            │   ecosystem)     │
            └──────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
      ┌──▼──┐   ┌────▼───┐  ┌──▼────┐
      │intel│   │ ACP    │  │ UI    │
      │     │   │ monitor│  │(Gradio│
      │     │   │ (USDC  │  │ +GH   │
      │     │   │ revenue)   │Pages) │
      └─────┘   └────────┘  └───────┘
```

### System Components (2026 Status)

| Component | Status | Purpose |
|-----------|--------|---------|
| **Central Memory** | ✅ **NEW** | Append-only brain: findings, lessons, skills, social events |
| **Builder** | ✅ **NEW** | Self-improving code generator (grounded in Memory, auto-appends) |
| **MCP Integration** | ✅ **NEW** | Safe GitHub, Social, Tool Registry wrappers (Memory-connected) |
| **Python Engine** | ✅ Hourly CI | LLM analysis + slither, grounded in Memory findings |
| **SKILLFORGE** | ✅ Running | 13 verified security tools, harvest/toolcheck/synthesize workflows |
| **intel/** | ✅ Live | Reports, broadcasts, bounty-radar audit trail |
| **ACP Monitor** | ✅ Revenue | Autonomous USDC-escrow job fulfillment (14 live offerings) |
| **Node Agent** | 🟡 Partial | On-chain investigation loop (ready for integration) |
| **UI** | 🟡 Minimal | Gradio + GitHub Pages (expandable) |

---

## 🚀 How It Runs (Three Cooperating Runtimes)

### **Runtime 1: Python Engine (CI Workhorse)**
```bash
$ python -m agents.run                 # Hourly bounty hunt pass
$ python -m agents.run --review-repo   # Self-review pass
```

**What happens:**
1. Queries **Memory** for past findings & lessons (grounded context)
2. Fetches **real market data** (TVL, prices, on-chain activity)
3. Runs **slither static analysis**
4. Calls **multi-provider LLM** (Groq → Cerebras → OpenRouter → GitHub Models)
5. **Appends findings to Memory** (auto-compounds intelligence)
6. Writes timestamped **report to intel/**

**Frequency:** Hourly via GitHub Actions (free, 24/7)

### **Runtime 2: Builder Agent (Self-Improvement)**
```bash
$ python -m agents.builder --task "Create playbook for static analysis"
$ python -m agents.builder --improve "agents/run.py:Add Memory search capability"
```

**What happens:**
1. **Grounds in Memory** (searches for similar past work)
2. Generates **production code** (type hints, error handling, logging)
3. **Validates security** (no unsafe patterns, no eval/exec)
4. **Auto-appends to Memory** (as a "skill")
5. Returns code ready for PR or deployment

**Integration:** Called by skillforge/synthesize.py daily; can propose self-improving PRs

### **Runtime 3: MCP Integration (External Data)**
```bash
$ python -m skillforge.mcp --harvest               # Fetch GitHub/Social/Tools
$ python -m skillforge.mcp --social-sentiment      # X sentiment summary
$ python -m skillforge.mcp --tool-releases crytic/slither
```

**What happens:**
1. **GitHub MCP:** Read repo data, search issues, propose PRs (safe write-gates)
2. **Social MCP:** Fetch aggregated X sentiment (no individual tracking)
3. **Tool Registry MCP:** Fetch latest security tool releases
4. **All results → Memory** (auto-append for future grounding)

---

## 📋 Project Structure

```
V.A.P.E/
├── agents/                              # Python engine (CI + Builder)
│   ├── run.py                          # ✅ Orchestrator (NOW with Memory grounding)
│   ├── investigate.py                  # ✅ NEW: Deep investigation engine (auto target → verdict)
│   ├── build_intel_index.py            # ✅ NEW: Builds data/intel-index.json for the dashboard
│   ├── builder.py                      # ✅ NEW: Self-improving code generator
│   ├── integration.py                  # ✅ NEW: Memory + Builder + MCP glue
│   ├── llm.py                          # Multi-provider LLM fallback
│   ├── data_fetchers.py                # Real market/chain data
│   ├── vape.py / hack.py               # Persona engines
│   ├── vape_system.md / hack_system.md # System prompts
│   ├── acp.py / acp_fulfill.py         # ACP integration
│   ├── wallet.py                       # Wallet scaffolding
│   ├── token_scan.py                   # Token safety (GoPlus/DexScreener)
│   ├── self_improve.py                 # Self-improvement pipeline
│   ├── create_pr.py / self_pr.py       # GitHub PR creation
│   └── requirements.txt                # Python deps
│
├── skillforge/                          # Self-growing skill + tool ecosystem
│   ├── memory/                          # ✅ NEW: Central Memory
│   │   ├── retriever.py                # Search, append, sanitize
│   │   ├── findings.jsonl              # Security discoveries (append-only)
│   │   ├── lessons.jsonl               # Patterns & best practices
│   │   ├── skills.jsonl                # Generated playbooks by Builder
│   │   ├── social-events.jsonl         # X sentiment, narratives
│   │   ├── tools-registry.json         # Tool metadata
│   │   └── INDEX.md                    # Human-readable guide
│   │
│   ├── mcp.py                          # ✅ NEW: Safe GitHub/Social/Tool wrappers
│   ├── harvest.py                      # CVE & tool harvest (no LLM)
│   ├── toolcheck.py                    # Verify 13 security tools
│   ├── synthesize.py                   # LLM distills → PR proposals
│   ├── MANIFEST.md                     # Tool registry & skill playbooks
│   ├── skills/                         # Playbook files (sc-static, ai-redteam, recon)
│   └── tools/                          # 13 tools in subdirs (static/fuzzing/ai-redteam/recon)
│
├── intel/                               # Real-data audit trail
│   ├── reports/                        # Timestamped sweeps (security/sentiment/base/macro)
│   ├── scans/                          # Token safety scans
│   ├── broadcasts/                     # Community intel
│   ├── investigations/                 # ✅ NEW: Deep-investigation verdict reports
│   ├── bounty-radar/                   # Active bounty tracking
│   ├── catalog/                        # Investigation dedup
│   └── engagements/                    # ACP job records
│
├── src/                                 # Node agent (on-chain investigation)
│   ├── agents/vape.js                  # Investigation loop
│   ├── blockchain/analyzer.js          # Base RPC activity
│   ├── security/scanner.js             # Threat detection
│   ├── data-fetchers/fetcher.js        # Market metrics
│   ├── acp/protocol.js                 # ACP reporting
│   └── config/logger.js                # Pino logging
│
├── .github/workflows/                  # CI/CD automation
│   ├── bounty-cycle.yml                # Hourly Python engine
│   ├── skillforge-harvest.yml          # Hourly CVE/tool harvest
│   ├── skillforge-toolcheck.yml        # 6×/day tool verification
│   ├── skillforge-synthesize.yml       # Daily LLM synthesis
│   └── sync-to-hub.yml                 # Sync intel to HF Space
│
├── docs/                                # Documentation
│   ├── ARCHITECTURE.md                 # System design
│   ├── ACP_PROTOCOL.md                 # ACP details
│   ├── DEPLOYMENT.md                   # Deployment guide
│   ├── MEMORY.md                       # Memory system usage ✅ NEW
│   ├── BUILDER.md                      # Builder usage ✅ NEW
│   ├── MCP.md                          # MCP integration guide ✅ NEW
│   └── index.html                      # ✅ Live dashboard (investigation hero + Intel Explorer)
│
├── app.py                               # Gradio UI (HF Space)
├── package.json                         # Node.js deps + scripts
├── requirements.txt                     # Root deps (gradio)
├── .env.example                         # All env vars
└── README.md                            # This file
```

---

## 🎓 Quick Start

### Setup (All Paths)

```bash
git clone https://github.com/jUXTAPOSITION1/V.A.P.E.git
cd V.A.P.E
cp .env.example .env                    # Fill in your keys
```

### Path 1: Run Python Engine (Hourly Detection Loop)

```bash
pip install -r agents/requirements.txt
python -m agents.run                    # Bounty hunt
python -m agents.run --review-repo      # Self-review
```

**Output:** Reports in `reports/`; findings auto-appended to `skillforge/memory/findings.jsonl`

### Path 2: Use Builder (Self-Improvement)

```bash
python -m agents.builder --task "Create a playbook for analyzing new Solidity contracts"
```

**Output:** Generated code in stdout; auto-appended to `skillforge/memory/skills.jsonl`

### Path 3: Run MCP Harvest (GitHub + Social + Tools)

```bash
python -m skillforge.mcp --harvest                 # Full harvest cycle
python -m skillforge.mcp --social-sentiment        # Social sentiment only
python -m skillforge.mcp --tool-releases crytic/slither
```

**Output:** Data appended to Memory; findings in `intel/` audit trail

### Path 4: Full Cycle (Memory + Builder + MCP + Detective)

```bash
VAPE_FULL_CYCLE=1 python -m agents.run
```

**What happens:**
1. Detective analysis grounded in Memory findings
2. Builder proposes code improvements based on Memory lessons
3. MCP harvests external data (GitHub, Social, Tools)
4. All new findings/skills/events appended back to Memory

---

## 🧠 Central Memory System (Priority 1 — NEW)

The **Central Memory** is V.A.P.E.'s long-term intelligence brain. Every component can query and append.

### Search Past Findings

```python
from skillforge.memory.retriever import search_memory

# Find past anomalies on Base
findings = search_memory(
    query="base tvl anomaly",
    category="finding",
    min_confidence=0.8,
    days_back=7
)
print(f"Found {len(findings)} high-confidence findings")
```

### Append a Discovery

```python
from skillforge.memory.retriever import append_to_memory

append_to_memory(
    category="finding",
    title="$5M TVL outflow from Lido/Base",
    content="Detected at 14:23 UTC. Possible hedge or exploit fear.",
    source="agents/run.py",
    tags=["base", "lido", "anomaly"],
    confidence=0.92
)
```

### Memory Statistics

```python
from skillforge.memory.retriever import get_memory_stats

stats = get_memory_stats()
print(f"Total Memory entries: {stats['total_entries']}")
print(f"By category: {stats['by_category']}")
```

**Files:**
- `skillforge/memory/findings.jsonl` — Security discoveries
- `skillforge/memory/lessons.jsonl` — Patterns & best practices
- `skillforge/memory/skills.jsonl` — Builder-generated playbooks
- `skillforge/memory/social-events.jsonl` — X sentiment, narratives
- `skillforge/memory/tools-registry.json` — Tool metadata
- `skillforge/memory/INDEX.md` — Usage guide (human-readable)

---

## 🛠️ Builder Agent (Priority 2 — NEW)

The **Builder** is V.A.P.E.'s self-improvement engine. It generates production-ready code, grounded in Memory.

### Generate Code for a Task

```python
from agents.builder import Builder

builder = Builder()

# Generate code grounded in past patterns
code, metadata = builder.generate_code(
    task="Create a playbook for analyzing new Solidity smart contracts",
    review=True,  # Security validation
    tier="deep"   # Use reasoning LLM
)

# Outputs:
# - code: production-ready Python
# - metadata: title, tags, confidence (auto-appended to Memory)
```

### CLI Usage

```bash
python -m agents.builder --task "Create static analysis wrapper for Base contracts"
python -m agents.builder --improve "agents/run.py:Add Memory search to analysis"
python -m agents.builder --stats              # Show generation history
```

**Security Features:**
- ✅ Input validation & sanitization
- ✅ No unsafe code patterns (eval, exec, unrestricted OS access)
- ✅ Full audit logging
- ✅ Auto-append to Memory (immutable)
- ✅ Rate-limited LLM calls (no cost overruns)

---

## 🔗 MCP Integration (Priority 3 — NEW)

The **MCP Integration** safely extends V.A.P.E. with external data sources.

### GitHub MCP — Read Repo Data & Propose PRs

```python
from skillforge.mcp import GitHubMCPWrapper

gh = GitHubMCPWrapper(token=os.getenv("GITHUB_TOKEN"))

# Search issues (read-only, safe)
issues = gh.search_issues(
    repo="jUXTAPOSITION1/V.A.P.E",
    query="memory",
    state="open",
    limit=10
)

# Create a PR (write-gated, audit logged)
success, pr_data = gh.create_pr(
    repo="jUXTAPOSITION1/V.A.P.E",
    title="Builder: Add Memory grounding to analysis",
    body="Proposed by Builder based on Memory lessons",
    head="builder-improvement-2026-07-01",
    base="main"
)
```

### Social MCP — Sentiment & Narrative Tracking

```python
from skillforge.mcp import SocialMCPWrapper

social = SocialMCPWrapper()

# Fetch aggregated sentiment (no individual user tracking)
sentiment = social.get_sentiment_summary(
    accounts=["@based_vape"],
    query="@based_vape Base ecosystem",
    days_back=1
)
print(f"Positive ratio: {sentiment['aggregated_sentiment']['positive_ratio']}")

# Append to Memory for future grounding
social.append_social_event_to_memory({
    "title": "Daily Sentiment Summary",
    "content": json.dumps(sentiment),
    "tags": ["social", "sentiment", "daily"],
    "confidence": 0.7
})
```

### Tool Registry MCP — Latest Security Tools

```python
from skillforge.mcp import ToolRegistryMCPWrapper

registry = ToolRegistryMCPWrapper()

# Fetch latest slither releases
releases = registry.fetch_tool_releases(
    owner="crytic",
    repo="slither",
    limit=5
)

# Fetch CVE summary
cves = registry.fetch_cve_summary(days_back=7)
print(f"Critical CVEs: {cves['critical_count']}")
```

### Run Full MCP Harvest (→ Memory)

```bash
python -m skillforge.mcp --harvest
```

**Output:**
- GitHub issues/PRs → Memory
- Social sentiment → Memory
- Tool updates → Memory
- All auto-appended for future grounding

---

## 📊 Data Flow (End-to-End)

```
Real Data Sources (TVL, X, CVEs, Contracts)
        │
        ├─→ [Python Engine] ──→ LLM analysis
        ├─→ [MCP] ──→ GitHub/Social/Tools
        ├─→ [Slither] ──→ Static analysis
        │
        └──────→ All feed into MEMORY
                 (Append-only, searchable)
                 │
                 ├─→ [Future Detective Run] ──→ Grounded in past findings
                 ├─→ [Builder] ──→ Generates code grounded in lessons
                 ├─→ [SKILLFORGE] ──→ Synthesizes new tools/skills
                 │
                 └──→ intel/ + ACP → Revenue + Broadcasts

Every cycle compounds intelligence: past findings ground future runs.
```

---

## 🔒 Security & Audit

**Every component includes:**
- ✅ Input sanitization (no secrets, limited length)
- ✅ Append-only Memory (no deletion/modification)
- ✅ Full operation logging (audit trail)
- ✅ Rate limiting (prevent cost overruns)
- ✅ Review gates for writes (GitHub PRs, ACP fulfillment)
- ✅ Least privilege (read-only by default; writes gated)

**Memory Sanitization:**
- Regex filters for API keys, private keys, PII
- Ethereum address masking
- Character whitelisting

**Builder Security:**
- Unsafe pattern detection (eval, exec, unrestricted OS access)
- No unvalidated input usage
- Restricted module blocklist
- Code review before auto-append

**MCP Security:**
- Rate limiting (GitHub: 60 calls/min, Social: 30 calls/min)
- Public data only (no authentication tokens exposed)
- Caching to minimize API calls
- Graceful error handling & fallback

---

## 🚦 Current Status & Roadmap

### ✅ July 2026 Release (Complete + Hardened)
- [x] Central Memory (retriever.py, append-only, searchable)
- [x] Builder Agent (self-improving code generator, security-validated)
- [x] MCP Integration (GitHub, Social, Tool Registry wrappers)
- [x] Integration Glue (Memory + Builder + MCP in detective flows)
- [x] Updated run.py (now grounds analysis in Memory)
- [x] CLI interfaces (builder.py, mcp.py, integration.py)
- [x] **Hardening pass** — see [changelog](#-hardening-changelog-july-2026) below

### 🕵️ Deep Investigations + Live Dashboard (July 2026)
VAPE now runs **autonomous end-to-end investigations** and publishes them to a **pro live dashboard**:

| Component | What it does |
|-----------|--------------|
| **`agents/investigate.py`** | Deep-investigation engine (zero-LLM, real data). Auto-selects the highest-signal live Base target (violent movers / low-liquidity pools), runs GoPlus token-security + DexScreener liquidity + Base-RPC code presence + Etherscan V2 verification + recent-hack technique correlation, computes a weighted 0–100 safety score, and files a verdict report to `intel/investigations/`, logs a `finding` to Memory, and appends the catalog. Run `--auto` or `--address 0x…`. |
| **`agents/build_intel_index.py`** | Zero-LLM parser that turns every produced artifact (reports, broadcasts, investigations, catalog, tools, skills) into a machine-readable, **linkable** `data/intel-index.json` — each entry deep-links to its exact source file on GitHub. |
| **Live dashboard** | [`juxtaposition1.github.io/V.A.P.E`](https://juxtaposition1.github.io/V.A.P.E/) now leads with a **Latest Investigation** hero (verdict + score + rationale) and an **Intel Explorer** — tabbed, filterable, fully linkable sections for Investigations / Reports (by domain) / Broadcasts / Tools. Refreshes every cycle. |
| **Cycle wiring** | Both the hourly CI (`bounty-cycle.yml`) and the local 4h sweep (`scripts/intel_sync.sh`) now run the investigation + rebuild the index before committing — so the site stays current with zero extra compute. |

### 🔧 Hardening Changelog (July 2026)
The skeleton was reviewed end-to-end and filled into a robust, runnable system:

| Area | Fix |
|------|-----|
| **Memory** | Fixed an f-string crash in `generate_index()` that broke `init_memory()` on every call. |
| **Memory** | Added a backward-compatible normalizer so legacy SKILLFORGE rows (`ts/source/summary` and `ts/action/outcome`) are queryable — previously 74/80 entries were unreadable (`category: unknown`). |
| **Builder** | Reworked the security validator into hard-**BLOCK** vs advisory-**WARN** tiers. The old list hard-rejected `import os`, `open(`, `requests.get`, `json.loads` — which would have rejected nearly every real file. |
| **run.py** | Added repo-root to `sys.path` so `agents.*` / `skillforge.*` resolve when CI runs `python agents/run.py`; the integration layer was silently disabled before. |
| **run.py** | Guarded Groq SDK init + legacy fallback so the cycle no longer crashes at import when no key is set (multi-provider `llm.py` is the primary path). |
| **run.py** | Grounding now **searches** Memory before the LLM and appends the **actual analysis** afterward (only on real output) — no more raw-data pollution. |
| **SKILLFORGE** | `hack_feed` false-positive fixed (registry `version_cmd` now uses the wrapper path); `wallet_trace` reclassified as `unsupported` / `known_limitation` (Etherscan V2 paid-only on Base). Toolcheck now skips known limitations — ending the recurring issue spam. |
| **Docs** | Added the missing `docs/MEMORY.md`, `docs/BUILDER.md`, `docs/MCP.md` referenced by this README. |

### 🟡 Next (Planned)
- [ ] Expand Builder to generate skill playbooks (sc-static, ai-redteam, recon)
- [ ] Connect Node agent to Memory + Builder
- [x] **Live dashboard with investigation summary + linkable intel explorer** ✅
- [ ] Enhance UI with Memory browser + Builder dashboard
- [ ] MCP: Integrate real X API v2 (vs. mock data for MVP)
- [ ] MCP: Connect to more tool registries (npm, crates.io, etc.)
- [ ] Extended audit trail: Memory versioning, blame log

### 🔴 Known Limitations (by design, not breakage)
- `wallet_trace` account endpoints need a paid Etherscan V2 plan on Base — use keyless
  `base_rpc` (balance/nonce) and `contract_recon` (verified source) instead.
- Social MCP sentiment is an MVP aggregate pending a live X API v2 / partner feed.
- Node agent narrative sweeps are local (4h cron); the **investigation engine now runs in both CI and the local sweep**.
- Etherscan V2 verification in investigations is best-effort — it activates only when `ETHERSCAN_API_KEY` is set; otherwise all other recon (GoPlus/DexScreener/Base RPC/hack-feed) still runs keyless.

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design & data flow
- **[ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md)** — Agent Commerce Protocol details
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** — Deploy to GitHub Actions + Node
- **[MEMORY.md](docs/MEMORY.md)** — Central Memory usage guide ✅ NEW
- **[BUILDER.md](docs/BUILDER.md)** — Builder Agent reference ✅ NEW
- **[MCP.md](docs/MCP.md)** — MCP Integration guide ✅ NEW

---

## 🔧 Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# LLM (multi-provider, pick at least one)
GROQ_API_KEY=                          # Required (fast path)
CEREBRAS_API_KEY=                      # Optional fallback
OPENROUTER_API_KEY=                    # Optional fallback
GITHUB_MODELS_TOKEN=                   # Optional fallback
TOGETHER_API_KEY=                      # Optional fallback

# GitHub (for MCP + PR creation)
GITHUB_TOKEN=                          # Required for writes

# Base RPC (for on-chain data)
BASE_RPC_URL=https://mainnet.base.org  # Optional (keyless)

# External APIs (all optional, keyless where possible)
DEXSCREENER_API=                       # Token data
COINGECKO_API=                         # Price data
DEFILLAMA_API=                         # TVL data

# ACP (for revenue)
VIRTUALS_API_KEY=                      # Optional (revenue cycle)

# Feature Flags
VAPE_FULL_CYCLE=1                      # Enable Memory + Builder + MCP
```

---

## 🎯 Performance & Costs

| Component | Frequency | Compute | Cost/Month |
|-----------|-----------|---------|-----------|
| Python Engine | Hourly | Free runner (GitHub Actions) | $0 |
| SKILLFORGE harvest | Hourly | Free runner | $0 |
| SKILLFORGE toolcheck | 6×/day | Free runner | $0 |
| SKILLFORGE synthesize | Daily | Free runner + LLM | $0.01–0.05 (Groq) |
| Builder | On-demand | Free runner + LLM | $0.01–0.05 (Groq) |
| MCP harvest | On-demand | Free runner + API calls | $0 (keyless/cached) |
| Node agent | Continuous | Local machine | $0 (optional) |
| ACP revenue | Continuous | Base blockchain | +USDC (14 offerings) |

**Total monthly cost:** ~$0.10–0.50 (LLM calls) + revenue from ACP

---

## 🚀 Deployment

### Automatic (Recommended)
Set `GROQ_API_KEY` in repo Secrets and enable Actions. Workflows run 24/7 with zero local compute.

### Manual (Local Testing)
```bash
python -m agents.run                                    # Once
VAPE_FULL_CYCLE=1 python -m agents.run                 # Full cycle
```

### Node Agent (Local Depth)
```bash
npm install
npm start                                              # Continuous investigation loop
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for full setup.

---

## 📖 The Chain Never Lies

V.A.P.E makes sure you hear the truth first. Built on real data. Grounded in past findings. Auto-improving through Memory and Builder. Extending reach via safe MCP integration.

**Every finding is immutable. Every lesson is recorded. Every skill compounds future intelligence.**

---

## 🤝 Contributing

1. Review existing code in `agents/` and `skillforge/`
2. Check [Memory.md](docs/MEMORY.md) / [Builder.md](docs/BUILDER.md) / [MCP.md](docs/MCP.md) for integration points
3. Ensure all new code is security-validated and audit-logged
4. Append lessons learned to Memory for future cycles

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🔫🦍 Let's Hunt.

**Live dashboard:** [Bounty Command Center](https://jUXTAPOSITION1.github.io/V.A.P.E/)

**V.A.P.E. operates 24/7 via GitHub Actions. Zero local compute. Real data only.**

**The autonomous detective for the on-chain ecosystem.**

---

_Last Updated: July 1, 2026 — Central Memory + Builder + MCP Integration Release_
