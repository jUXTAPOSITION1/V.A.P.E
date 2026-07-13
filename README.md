---
title: VAPE - Autonomous On-Chain Intelligence
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: "4.44.0"
app_file: app.py
pinned: false
---

<div align="center">
<img src="docs/assets/vape-avatar.jpg" width="96" height="96" alt="VAPE" style="border-radius:18px" />

# V.A.P.E.
### Virtual Ape Private Eye

**An autonomous on-chain intelligence system for Base and the Virtuals ecosystem.**
**Real recon, real verdicts, zero fabrication.**

<br/>

[![Bounty Cycle](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml)
[![SKILLFORGE Toolcheck](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml/badge.svg)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-A1A1AA?style=flat-square)](LICENSE)

![Base](https://img.shields.io/badge/Chain-Base-0052FF?style=flat-square&logo=coinbase&logoColor=white)
![ACP](https://img.shields.io/badge/Protocol-Virtuals_ACP-8B5CF6?style=flat-square)
![ERC-8004](https://img.shields.io/badge/Identity-ERC--8004_%2354988-10B981?style=flat-square)
![x402](https://img.shields.io/badge/Payments-x402-22D3EE?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Compute](https://img.shields.io/badge/local_compute-%240-10B981?style=flat-square)

<br/>

[Live Dashboard](https://juxtaposition1.github.io/V.A.P.E/) ·
[Architecture](docs/ARCHITECTURE.md) ·
[Quick Start](#quick-start) ·
[ACP Protocol](docs/ACP_PROTOCOL.md) ·
[Deployment](docs/DEPLOYMENT.md) ·
[@based_vape](https://x.com/based_vape)

</div>

---

## Overview

V.A.P.E. is a fully autonomous AI detective for the on-chain ecosystem. It runs continuously
on GitHub Actions at zero local compute cost, watching Base and the Virtuals economy, and
publishes exactly what it finds — a token security scan, a market anomaly, a completed
investigation — with the evidence attached, never just a conclusion.

It is a verified on-chain identity, not an anonymous script: **ERC-8004 agent #54988**,
wallet `0xa1420293a7df49bc8380f543a1fe7b8d6f582879`, settling every paid engagement in USDC
on Base. Both hiring paths are real and live — an escrow-backed engagement through Virtuals
Protocol's Agent Commerce Protocol (ACP), or an instant, wallet-signed payment through x402 —
see [docs/ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) and the site's Engagement Options section.

**X:** [@based_vape](https://x.com/based_vape) · **Live dashboard:** [juxtaposition1.github.io/V.A.P.E](https://juxtaposition1.github.io/V.A.P.E/)

---

## What it actually does

- **Deep investigations** — every cycle, VAPE auto-selects the highest-signal live Base
  target, runs multi-source recon (GoPlus token security, DexScreener liquidity, Base RPC,
  Etherscan V2 contract verification, recent-hack technique correlation, and a real web
  search for public rug/scam mentions), scores it 0-100, and publishes a verdict — PROCEED,
  CAUTION, or REJECT — to `intel/investigations/` and the live dashboard.
- **Market intelligence** — TVL, gas, Fear & Greed, global market cap, and Base's top
  protocols and trending pairs, refreshed continuously and shown live on the site.
- **Security auditing** — a real prompt-injection red-team suite runs against VAPE's own
  reporting pipeline, plus a static-analysis tier (Slither, Aderyn, Mythril) for
  smart-contract review offerings.
- **Self-improvement** — a Builder agent grounded in a shared Memory system proposes and
  implements real code changes (new tools, bug fixes, skill playbooks), every one gated
  behind automated security validation and a human-reviewed pull request.
- **Commerce** — 29 priced offerings (token safety, liquidity checks, rug-pull alerts,
  market intelligence, full contract audits, 14 DefiLlama data tools, and more), payable
  through ACP escrow or instant x402 on Base mainnet, with results delivered as a rendered
  report on-site or a downloadable PDF.

---

## The live site

[**juxtaposition1.github.io/V.A.P.E**](https://juxtaposition1.github.io/V.A.P.E/) is the
primary way to see and use VAPE — not a static status page, a working product surface:

- Live network/market data (Base TVL, gas, top protocols, trending pairs, Fear & Greed)
- A wallet-connect portfolio view (injected wallets, Coinbase Wallet, WalletConnect) with
  real Base holdings, balances, and price history — no paid indexer, nothing fabricated
- Instant x402 payment for any auto-fulfilled offering, signed directly from a connected
  wallet, with the report rendered inline and downloadable as a letterheaded PDF
- A fully linkable investigation archive, indexed automatically from every report VAPE
  has ever published — nothing curated after the fact
- A free token-security preview tool, open to anyone, no wallet required

Built with zero bundler (plain HTML/CSS/JS under `docs/assets/`) and a small Cloudflare/Deno
Workers backend (`worker/`) for the x402 payment gate and Alchemy-backed portfolio data.

---

## Architecture

Three cooperating pieces:

| Layer | What it is | Where |
|---|---|---|
| **Python engine** | Hourly CI orchestration, investigations, market sweeps, self-improvement | `agents/*.py` |
| **SKILLFORGE** | Self-growing skill + tool ecosystem: harvest, toolcheck, synthesize, a shared Memory base, and a build ledger of instructional patterns | `skillforge/` |
| **Live site + worker** | The dashboard, wallet, and x402 payment backend | `docs/`, `worker/` |

Full component-level detail, the real data flow, and current status of every piece live in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — this README stays a map, not a duplicate.

---

## Quick start

```bash
git clone https://github.com/jUXTAPOSITION1/V.A.P.E.git
cd V.A.P.E
cp .env.example .env        # fill in at least one LLM provider key
pip install -r agents/requirements.txt
```

```bash
python -m agents.investigate --auto     # run one real investigation
python -m agents.run                    # hourly bounty-cycle pass
python -m agents.run --review-repo      # self-review pass
python -m agents.builder --task "..."   # generate code grounded in Memory
```

Everything above writes real output: a report in `intel/` or `reports/`, a finding appended
to `skillforge/memory/findings.jsonl`. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for
running the full system on GitHub Actions (the actual production setup — 24/7, zero local
compute) and [worker/README.md](worker/README.md) for the site's payment backend.

---

## Memory, Builder, and MCP

- **Central Memory** (`skillforge/memory/`) — an append-only, searchable brain every
  component reads from and writes to: `findings.jsonl` (security discoveries),
  `lessons.jsonl` (build outcomes), `skills.jsonl` (learned playbooks),
  `build_log.jsonl` (instructional build patterns — see
  [BUILD_LEDGER.md](skillforge/memory/BUILD_LEDGER.md)), and `social-events.jsonl`.
  See [docs/MEMORY.md](docs/MEMORY.md).
- **Builder** (`agents/builder.py`) — grounds every code-generation task in Memory,
  validates the output against a hard-block/soft-warn security policy, and auto-appends
  results back to Memory. See [docs/BUILDER.md](docs/BUILDER.md).
- **MCP** — VAPE speaks the standard Model Context Protocol both ways: a real MCP server
  (`mcp_servers/vape_mcp.py`) exposes VAPE's own tools to any MCP host, and VAPE itself
  hosts 13 registered MCP servers (7 keyless, 6 that activate the instant a key is set) for
  research and tool discovery. See [docs/MCP.md](docs/MCP.md) and
  [docs/MCP_SERVER.md](docs/MCP_SERVER.md).

---

## Security and audit

- Every generated deliverable traces to a real, cited data source — no simulated tool
  output, no invented findings.
- Memory is append-only; nothing is silently deleted or rewritten.
- Builder-generated code is checked against a hard-block list (`eval`, `exec`, shell
  execution, unsafe deserialization) before it can be appended or opened as a PR.
- Every autonomous PR (self-improvement, build requests, skill synthesis) requires human
  review before merge — nothing reaches `main` unreviewed.
- A real prompt-injection red-team suite (`agents/redteam.py`) runs against VAPE's own
  report-generation pipeline, not a hypothetical scenario, and is scored PASS/FAIL from
  actual model output.

---

## Repository layout

```
V.A.P.E/
├── agents/              Python engine — investigations, market sweeps, builder, red-team
├── skillforge/          Self-growing skill/tool ecosystem + shared Memory
├── intel/               Real-data audit trail: reports, broadcasts, investigations, bounty radar
├── docs/                Site (docs/index.html) + architecture/deployment/protocol docs
├── worker/              Cloudflare/Deno Workers backend — x402 payments, portfolio data
├── mcp_servers/         Standard MCP server exposing VAPE's tools
├── scripts/acp-monitor/ ACP job listener/fulfillment daemons
└── reports/             Timestamped bounty-cycle and self-review output
```

---

## Status

**Live and running:** Featured Investigations every 30 minutes, hourly bounty/market
sweeps, the SKILLFORGE tool
ecosystem (15 tools registered, 15 verified), ACP + x402 job fulfillment across 29 live
offerings (21 auto-fulfilled with zero manual work), x402 payments on Base mainnet via
Coinbase Developer Platform's hosted facilitator, wallet-connect portfolio, the Central
Memory system, the standard MCP server (17 tools), and the Builder self-improvement
pipeline.

**In progress:** real auto-handlers for the remaining 8 ACP-only offerings
(`forensics_deep`/`wallet_recon`/`deep_contract_audit`/etc. — the underlying tools like
`wallet_trace` already work, nothing calls them automatically yet), a dashboard
reputation loop, richer social-sentiment intel beyond the current keyless aggregate.
`app.py` is an unconnected placeholder stub (it doesn't call any real VAPE agent code) that
exists only to satisfy this repo's synced Hugging Face Space's Gradio entry point — the
actual product is the live GitHub Pages site above.

---

## Documentation

| Doc | Covers |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, component status, data flow |
| [ARCHITECTURE_ROADMAP.md](docs/ARCHITECTURE_ROADMAP.md) | ACP revenue strategy, LLM provider expansion |
| [ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) | Identity, wallet, offerings, job lifecycle |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | GitHub Actions + repository secrets setup |
| [MEMORY.md](docs/MEMORY.md) | Central Memory usage guide |
| [BUILDER.md](docs/BUILDER.md) | Builder agent reference |
| [MCP.md](docs/MCP.md) / [MCP_SERVER.md](docs/MCP_SERVER.md) | MCP integration + standard server |
| [worker/README.md](worker/README.md) | x402 payment backend |
| [skillforge/memory/BUILD_LEDGER.md](skillforge/memory/BUILD_LEDGER.md) | Instructional build patterns |

---

## Environment variables

Copy `.env.example` to `.env`. At minimum, set one LLM key:

```bash
GROQ_API_KEY=       # free tier — enough to run everything
```

xAI's Grok 4.1 Fast is the primary model for reports/investigations/expert assessment
when `XAI_API_KEY_1` is set (see `agents/llm.py`'s `FRONTIER_ORDER`), but every path has a
free fallback — nothing in VAPE requires a paid key to run. Everything else (Etherscan,
Alchemy, additional LLM fallbacks, MCP research providers, the worker's Cloudflare/
CoinGecko keys) is optional — VAPE degrades gracefully to keyless data sources when a key
isn't set. See `.env.example` for the full list and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
for which secrets the live site's CI actually needs.

---

## Contributing

1. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and the relevant subsystem doc before
   changing it.
2. New code must pass the Builder's security validation (no `eval`/`exec`, no unrestricted
   shell/OS access) and include real error handling — no silent failures.
3. Real data only: no simulated tool output, no fabricated findings, no guessed URLs or
   icons. If a data source is unreachable, say so rather than approximate.
4. Autonomous agents open pull requests for review; nothing is designed to write directly
   to `main` unreviewed.

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**On-chain data, real tools, no fabricated results.**

</div>
