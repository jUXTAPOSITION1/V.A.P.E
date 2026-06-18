# Bug Bounty / White-Hat Source Map — mid-June 2026

_Intel drop logged 2026-06-18. Reference for bounty_radar.py source expansion + manual hunting._

## Platform Landscape

### 1. Immunefi — largest & highest-paying
- ~200+ active programs. On-chain vaults show pledged TVL.
- Notable: Ethena up to **$3M**, DeXe **$500k**, SSV Network **$250k**, ENS **$250k**,
  Lombard Finance **$250k**, The Graph **$50k**, Hedera, LayerZero, Uniswap (high max).
- 2026 payouts: **$12.5M+** in first 5 months. Multiple 6-/7-figure rewards.
- Models: Primacy of Impact vs Rules. KYC + PoC + arbitration common.
- Attackathons (mostly concluded early June): Firedancer V1 $1M, Base Azul $250k.
- **Immunefi SR Summer 2026**: bonus pools (IMU tokens + USD) through ≥ July 2026.
- Track: immunefi.com/explore or /bug-bounty. RADAR STATUS: ✅ covered (browser cache + scrape).

### 2. HackenProof — ⚠️ NOT YET IN RADAR
- ~400+ programs. Web/mobile/SC/exchanges. Good beginner→mid, many always-open.
- Active: **Arcadia Finance** (NEW, Base/Optimism/Unichain) up to **$25k** (~June 2026) ← OUR LANE.
  SuperEarn, idOS Apps+SC, Cetus Web, NiceHash, CoinW. Some up to $1M.
- **Hyperbridge**: $50k program (May 2026, post-incident).
- Track: hackenproof.com/programs (HTML scrape — no public JSON API).

### 3. Cantina (Spearbit) — high-value onchain
- **Coinbase**: LIVE, up to **$5M** (Tier 0 = Base/core contracts). ← TOP PRIORITY, Base-native.
- Perena up to $25k. Deployed mainnet SC focus. RADAR STATUS: ✅ covered.

### 4. Sherlock — insurance-backed contests
- Active mid-June: DRE App dreUSD **$48k** (~Jun 17 end), TipRun **$15k**, Tokenize.it,
  DART DualDefense, 0xMarkets **$30k**. RADAR STATUS: ✅ covered.

### 5. Code4rena — time-boxed competitive audits
- Recent in judging/mitigation: K2, Monetrix, Jupiter Lend, Rujira.
- Fewer brand-new active now; launches regularly. Solidity + Rust. RADAR STATUS: ✅ covered.

### Other
- LayerZero, Uniswap — high max on Immunefi/Cantina.
- Solana (Rust), Cosmos/THORChain, Move chains, bridges, infra.
- Self-hosted: check GitHub SECURITY.md files per-project.

## Tracking New Launches — competition lowest right after launch
- **Bountyhunt.xyz** (launched 2026-06-17) — ⚠️ NOT YET IN RADAR. HIGH PRIORITY INTEGRATION.
  Aggregates Immunefi/Sherlock/Cantina/HackenProof/HackerOne. Telegram alerts on new
  bounties + code changes (commits/PRs/releases) + fresh-program flags. **API/webhooks** for automation.
- Platform X accounts (@immunefi), Discord, announcement channels.
- Immunefi audit-competition section + Sherlock for attackathons (1–4 week cycles).

## Success Requirements
- Almost all: detailed **PoC**, impact assessment, often **KYC** for payout. Strict responsible disclosure.
- Check vault TVL for pledged funds. Start lower-severity/well-scoped to build rep.
- ALWAYS verify latest scope on official program page — scope changes.

## RADAR UPGRADE — SHIPPED 2026-06-18
1. [x] HackenProof coverage — solved via Bountyhunt aggregator (direct site is Cloudflare-403).
       324 HackenProof programs now flow in, incl. Arcadia $25k + $360k recovery, SmarDex $500k,
       TETU $1M, MetaMask Staking $700k, DeXe $500k, Citrea $250k.
2. [x] Bountyhunt.xyz integration — `fetch_bountyhunt()` consumes the FREE auth-less catalog
       `api.bountyhunt.xyz/v1/programs` (cursor-paginated). Brings HackenProof + HackerOne +
       AgentArena (AI-agent bounties) + self-hosted — the rails we can't scrape directly.
       Dedup: SKIPS immunefi/cantina/sherlock/code4rena (our dedicated fetchers stay authoritative).
       Radar grew ~264 -> 875 opportunities. AgentArena AI-agent bounties get a +18 fit floor (HACK's turf).
3. [x] AgentArena/AI-agent fit-boost added; EVM/Base scoring already in place.

### Bountyhunt API notes (for future Pro upgrade)
- FREE: full program + asset catalog, last-24h activity. `/v1/programs` (cursor-paginated), auth-free.
- PRO (API key): full activity history, higher rate limits, **Webhooks** (push events to our endpoint),
  **MCP** tool access (`api.bountyhunt.xyz/mcp`, returns 401 without key), **Telegram alerts**.
- NEXT LEVERAGE IF WE GO PRO: webhook -> push new-bounty + scope-change (commit/PR/release) events
  straight to a VAPE endpoint or Telegram, replacing poll-based detection. Operated by Cecuro, Inc.
- Auth endpoint: `/v1/auth/get-session`. Provision a key via operator if/when Pro is justified.
