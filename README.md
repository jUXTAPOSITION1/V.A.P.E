<div align="center">
<img src="docs/assets/vape-avatar.jpg" width="96" height="96" alt="VAPE" style="border-radius:18px" />

# V.A.P.E.
### Virtual Ape Private Eye

**An autonomous on-chain intelligence system for Base and Ethereum/EVM** — live
investigations, market intelligence, security auditing, and 32 priced offerings settled
on-chain.

<br/>

[![Bounty Cycle](https://img.shields.io/github/actions/workflow/status/jUXTAPOSITION1/V.A.P.E/bounty-cycle.yml?style=flat-square&label=Bounty%20Cycle&logo=github&logoColor=white)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/bounty-cycle.yml)
[![SKILLFORGE Toolcheck](https://img.shields.io/github/actions/workflow/status/jUXTAPOSITION1/V.A.P.E/skillforge-toolcheck.yml?style=flat-square&label=SKILLFORGE%20Toolcheck&logo=github&logoColor=white)](https://github.com/jUXTAPOSITION1/V.A.P.E/actions/workflows/skillforge-toolcheck.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-A1A1AA?style=flat-square)](LICENSE)

<br/>

![Base](https://img.shields.io/badge/Chain-Base-0052FF?style=flat-square&logo=coinbase&logoColor=white)
![Ethereum](https://img.shields.io/badge/Chain-Ethereum%2FEVM-627EEA?style=flat-square&logo=ethereum&logoColor=white)
![x402](https://img.shields.io/badge/Payments-x402-0EA5E9?style=flat-square)
![ERC-8004](https://img.shields.io/badge/Identity-ERC--8004_%2359900-10B981?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)
![Compute](https://img.shields.io/badge/Local_Compute-%240-10B981?style=flat-square)

<br/>

[Live Dashboard](https://juxtaposition1.github.io/V.A.P.E/) ·
[Architecture](docs/ARCHITECTURE.md) ·
[Quick Start](#quick-start) ·
[x402 Worker](worker/README.md) ·
[Deployment](docs/DEPLOYMENT.md) ·
[@based_vape](https://x.com/based_vape)

</div>

---

## Overview

V.A.P.E. is a fully autonomous AI detective for the on-chain ecosystem. It runs continuously
on GitHub Actions at zero local compute cost, watching Base, Ethereum, and the wider EVM
ecosystem, and publishes exactly what it finds — a token security scan, a market anomaly, a
completed investigation — with the evidence attached, never just a conclusion.

It is a verified on-chain identity, not an anonymous script: **ERC-8004 agent #59900**
(wallet `0x8aAB9a6d28e9AbA2a15a613C90F24f352f0Cce15`, basename `vapex402.base.eth`) — a
passport VAPE registered itself, directly against Base's canonical `IdentityRegistry`
contract, with no third-party platform brokering it. Every paid engagement settles in USDC
on Base. **x402 is VAPE's sole commerce rail** — all 32 offerings are hireable
instantly with a wallet-signed HTTP payment, no account or escrow step, settled directly
against a hosted x402 facilitator on Base mainnet; deeper, async work (full contract audits,
wallet forensics, whale-wallet tracing) dispatches a GitHub Actions job and delivers the
report inline once it completes. See [worker/README.md](worker/README.md) for the x402
side, or just use the site's Engagement Options section. (VAPE previously also offered an
escrow-backed engagement via Virtuals Protocol's Agent Commerce Protocol — ACP — sunset
2026-07-31 as VAPE refocused on Base/Ethereum/EVM + x402; see
[docs/ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) for that prior integration.)

**X:** [@based_vape](https://x.com/based_vape) · **Live dashboard:** [juxtaposition1.github.io/V.A.P.E](https://juxtaposition1.github.io/V.A.P.E/)

---

## What it actually does

- **Deep investigations** — every cycle, VAPE auto-selects the highest-signal live Base
  target, runs multi-source recon (token-safety and holder/liquidity data, on-chain contract
  verification, recent-hack technique correlation, and a real web search for public
  rug/scam mentions), scores it 0-100, and publishes a verdict — PROCEED, CAUTION, or
  REJECT — to `intel/investigations/` and the live dashboard.
- **Market intelligence** — TVL, gas, Fear & Greed, global market cap, and Base's top
  protocols and trending pairs, refreshed continuously and shown live on the site.
- **Security auditing** — a real prompt-injection red-team suite runs against VAPE's own
  reporting pipeline, plus a static-analysis tier (Slither, Aderyn, Mythril) for
  smart-contract review offerings.
- **Self-improvement** — a Builder agent grounded in a shared Memory system proposes and
  implements real code changes (new tools, bug fixes, skill playbooks), every one gated
  behind automated security validation and a human-reviewed pull request.
- **Commerce** — 32 priced offerings (token safety, liquidity checks, rug-pull alerts,
  market intelligence, full contract audits, general web research, 15 market-data
  tools, and more), all x402-payable — hireable instantly with a signed wallet payment, no account needed.
  Results render inline on-site or download as a PDF.

---

## The live site

[**juxtaposition1.github.io/V.A.P.E**](https://juxtaposition1.github.io/V.A.P.E/) is the
primary way to see and use VAPE — not a static status page, a working product surface:

- Live network/market data (Base TVL, gas, top protocols, trending pairs, Fear & Greed)
- A wallet-connect portfolio view (injected wallets, Coinbase Wallet, WalletConnect) with
  real Base holdings, balances, and price history — no fabricated numbers
- Instant x402 payment for any auto-fulfilled offering, signed directly from a connected
  wallet, with the report rendered inline and downloadable as a letterheaded PDF
- A live, paginated, searchable job ledger of every real x402 settlement VAPE has taken
- A fully linkable investigation archive, indexed automatically from every report VAPE
  has ever published — nothing curated after the fact
- A free token-security preview tool, open to anyone, no wallet required

Built with zero bundler (plain HTML/CSS/JS under `docs/assets/`) and a small Cloudflare/Deno
Workers backend (`worker/`) that gates the paid offerings behind x402 and serves the site's
live on-chain data panels.

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
compute) and [worker/README.md](worker/README.md) for the x402 payment backend.

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
  hosts several registered MCP servers for research and tool discovery. See
  [docs/MCP.md](docs/MCP.md) and [docs/MCP_SERVER.md](docs/MCP_SERVER.md).

---

## Security and audit

- **Code-generation gate** — Builder-generated code is checked against a hard-block list
  (`eval`, `exec`, shell execution, unsafe deserialization) before it can be appended or
  opened as a PR. See [docs/SECURITY_PROTOCOL.md](docs/SECURITY_PROTOCOL.md) for the full
  threat model and CI regression guard.
- **Human review gate** — every autonomous PR (self-improvement, build requests, skill
  synthesis) requires human review before merge; nothing reaches `main` unreviewed.
- **Adversarial testing** — a real prompt-injection red-team suite (`agents/redteam.py`)
  runs against VAPE's own report-generation pipeline daily, scored PASS/FAIL from actual
  model output, not a hypothetical scenario.
- **Append-only Memory** — `skillforge/memory/` is write-once; findings, lessons, and skill
  records are never silently deleted or rewritten.
- **Payment-path integrity** — x402 settlements verify against a live facilitator (VAPOR/CDP
  hybrid routing) before a job is billed; a failed deliverable never charges the caller (see
  `worker/src/index.ts`'s non-2xx-skips-settlement contract).
- **Dependency and secret hygiene** — automated dependency auditing across `agents/`,
  `worker/`, and `scripts/`, plus a static security-lint regression guard
  (`scripts/security_lint.py`) run in CI on every PR.

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
├── scripts/acp-monitor/ ACP job listener/fulfillment daemons (sunset 2026-07-31, kept for reference)
└── reports/             Timestamped bounty-cycle and self-review output
```

---

## Status

**Live and running:** Featured Investigations every 30 minutes, hourly bounty/market
sweeps, the SKILLFORGE tool ecosystem (16 tools registered, 16 verified), x402 job
fulfillment on Base mainnet across all 31 of VAPE's live offerings (21 auto-fulfilled with
zero manual work end-to-end), wallet-connect portfolio, a live searchable job ledger, the
Central Memory system, the standard MCP server, and the Builder self-improvement pipeline.

**Sunset (2026-07-31):** VAPE's ACP (Agent Commerce Protocol) escrow-engagement rail and
its dedicated Virtuals Protocol tracking/reporting sweep — VAPE is refocusing on
Base/all-EVM/Ethereum + x402 as its sole commerce rail rather than the Virtuals ecosystem
specifically. The underlying code (`scripts/acp-monitor/`, `agents/acp_fulfill.py`,
`agents/virtuals_sweep.py`) is left in the repo, just no longer scheduled/advertised; see
[docs/ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) for the prior integration.

**In progress:** a dashboard reputation loop, richer social-sentiment intel beyond the
current keyless aggregate. `app.py` is an unconnected placeholder stub (it doesn't call any
real VAPE agent code) that exists only to satisfy this repo's synced Hugging Face Space's
Gradio entry point — the actual product is the live GitHub Pages site above.

---

## Documentation

| Doc | Covers |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, component status, data flow |
| [ARCHITECTURE_ROADMAP.md](docs/ARCHITECTURE_ROADMAP.md) | Revenue strategy, offering roadmap |
| [ACP_PROTOCOL.md](docs/ACP_PROTOCOL.md) | Prior ACP integration (sunset 2026-07-31) — identity, wallet, offerings, job lifecycle |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | GitHub Actions + repository secrets setup |
| [MEMORY.md](docs/MEMORY.md) | Central Memory usage guide |
| [BUILDER.md](docs/BUILDER.md) | Builder agent reference |
| [MCP.md](docs/MCP.md) / [MCP_SERVER.md](docs/MCP_SERVER.md) | MCP integration + standard server |
| [SECURITY_PROTOCOL.md](docs/SECURITY_PROTOCOL.md) | Threat model, existing security automation, evolving CI regression guard |
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
free fallback — nothing in VAPE requires a paid key to run. Everything else (additional
recon/market-data keys, LLM fallbacks, MCP research providers, the worker's optional data
keys) is optional — VAPE degrades gracefully to keyless data sources when a key isn't set.
See `.env.example` for the full list and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for which
secrets the live site's CI actually needs.

---

## Contributing

1. Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and the relevant subsystem doc before
   changing it.
2. New code must pass the Builder's security validation (no `eval`/`exec`, no unrestricted
   shell/OS access) and include real error handling — no silent failures.
3. A data source that's unreachable should degrade honestly (report the gap), not fall back
   to an approximated or invented value.
4. Autonomous agents open pull requests for review; nothing is designed to write directly
   to `main` unreviewed.

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

**On-chain data, real tools, no fabricated results.**

</div>
