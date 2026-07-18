# vape-x402

Pay-per-call access to 21 of VAPE's 29 automatable ACP offerings over Coinbase's [x402](https://www.x402.org/) HTTP payment protocol. The other 8 offerings (deep audits, forensics, wallet recon, etc.) need the SKILLFORGE tool tier and are hired through a real [ACP job](../docs/ACP_PROTOCOL.md) instead — this worker doesn't duplicate that.

## Setup

```bash
cd worker
npm install
npx wrangler login          # opens a browser, needs your Cloudflare account
npx wrangler dev            # local dev server
```

Try the unpaid route first:
```bash
curl http://localhost:8787/
```

Then a paid one (expect a real `402` with payment requirements, since you have no payment header yet):
```bash
curl -i "http://localhost:8787/scan/token_safety_check?address=0x2b601d7fc4705361F0c0249a005a714b7A3EdaFE"
```

### Secrets

```bash
npx wrangler secret put ETHERSCAN_API_KEY   # optional — only exploit_check/dossier_check use it
npx wrangler secret put CDP_API_KEY_ID      # required for real mainnet settlement — see below
npx wrangler secret put CDP_API_KEY_SECRET
npx wrangler secret put ALCHEMY_API_KEY     # optional — powers /portfolio, /nfts, /network-status
npx wrangler secret put COINGECKO_API_KEY   # optional — powers /prices, and required for /cost-basis
npx wrangler secret put GH_DISPATCH_TOKEN   # optional — powers /scan/bounty_deep_dive (see below)
npx wrangler secret put TAVILY_API_KEY      # optional — dossier_check's web-reputation search (falls back to keyless DDG)
npx wrangler secret put BRAVE_API_KEY       # optional — dossier_check's web-reputation search, 2nd choice after Tavily
npx wrangler secret put FIRECRAWL_API_KEY   # optional — dossier_check's declared-socials scrape (falls back to a keyless fetch)
npx wrangler secret put GEMINI_API_KEY      # optional — dossier_check's frontier-LLM quick source read (falls back to Groq)
npx wrangler secret put GROQ_API_KEY        # optional — dossier_check's LLM fallback if Gemini has no key/errors
```

### Deploy

```bash
npx wrangler deploy
```

Ships on your `*.workers.dev` subdomain by default. **One manual one-time step**: Cloudflare requires you to claim a `workers.dev` subdomain from the dashboard (Workers & Pages → Overview) before the first deploy on a fresh account will actually publish — do this once, confirm it shows an active value (not blank), *then* deploy. `.github/workflows/deploy-worker.yml` does this same deploy on every push to `main` that touches `worker/**`, and needs `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` repo secrets to run live (it still typechecks and no-ops without them, rather than failing).

## Cloudflare + Deno Deploy

Cloudflare Workers is the primary deploy target. `worker/deno/` runs the exact same Hono `app` (`src/index.ts`) on [Deno Deploy](https://deno.com/deploy) as a documented fallback — see `deno/deno-entry.ts` and `deno/deno.json`. This exists because one real Cloudflare account previously hit an account-level bug where `workers.dev` subdomain registration silently never completed (the per-Worker URL stayed `*-null` even with the toggle on, `/workers/onboarding` 404'd, and Wrangler/Cloudflare's Git integration/its "Create Application" wizard all failed identically) — if that ever recurs, this repo can switch `WORKER_BASE` in `docs/assets/app.js`/`profile.js` to the Deno URL without any code changes, since `src/index.ts` has zero Cloudflare-specific code.

To deploy the Deno fallback: at [dash.deno.com](https://dash.deno.com), **New Project → GitHub → jUXTAPOSITION1/V.A.P.E**, entry point `worker/deno/deno-entry.ts`, add the same environment variables as the Cloudflare secrets above (as Deno Deploy project settings, marked secret). Deno assigns a working `https://<project>.deno.dev` URL immediately, auto-deploying on every push to `main` via its own GitHub integration — no workflow file needed for that side.

`deno/deno.json` (its own directory, deliberately **not** next to `package.json`) holds the import map aliasing the same npm packages `worker/package.json` uses — `hono`, `@x402/hono`, `@x402/core`, `@x402/evm`, `@x402/extensions`, `jose` — to their `npm:` specifiers Deno resolves natively, plus `"nodeModulesDir": "none"`. Both matter: a `deno.json` sitting next to a `package.json` makes Deno auto-detect a Node "workspace" and try to resolve *every* dependency in `package.json` — including unrelated devDependencies like `wrangler`/`typescript` that the Deno runtime never imports — which failed in an actual Deno Deploy build with an unrelated npm version-resolution error before this was separated out. The entry point must stay at `worker/deno/deno-entry.ts` for the same reason: Deno Deploy's remote build runs `npm install` first and switches to strict "bring your own node_modules" resolution when it sees a sibling `package.json`, which a copy sitting next to `package.json` would trigger.

`.github/workflows/worker-typecheck.yml` independently runs `deno check` against `deno/deno-entry.ts` on every push/PR touching `worker/**`, so the Deno path stays typechecked even though its actual deploys aren't CI-driven.

The repo root's `package.json`/`package-lock.json` are an intentionally empty placeholder (no dependencies, no scripts, `"private": true`) — Deno Deploy's dashboard build for this project runs from the repo root and its framework auto-detection needs *some* `package.json` to exist there, even though the real entry point lives entirely under `worker/deno/`. Don't add real dependencies/scripts to it; if it's ever deleted, the Deno Deploy build for this project starts failing (`deploy/juxtaposition1/vape` status check) even though nothing in `worker/` changed.

## Base mainnet + Coinbase Developer Platform

`wrangler.toml` is pointed at **Base mainnet** (`eip155:8453`) and CDP's hosted facilitator (`https://api.cdp.coinbase.com/platform/v2/x402`) — real funds move through this. The pay → verify → settle loop was proven first against Base Sepolia + the free public `facilitator.x402.org` facilitator before this switch (see git history on `wrangler.toml`/`src/index.ts` for the testnet config if you need to reproduce that).

To actually settle payments you need a [CDP Secret API Key](https://portal.cdp.coinbase.com) (`CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` above) — `src/lib/cdpAuth.ts` mints a Bearer JWT from it for every `/verify`, `/settle`, and `/supported` call to the facilitator (`src/index.ts`'s `buildCreateAuthHeaders()`). Without both secrets set, those calls go out unauthenticated and the facilitator returns 401.

### 50/50 hybrid: VAPOR + CDP

When `VAPOR_FACILITATOR_URL` is set, every request picks VAPOR (our own facilitator, [jUXTAPOSITION1/VAPOR](https://github.com/jUXTAPOSITION1/VAPOR)) or CDP as its primary facilitator with even odds (see `lib/facilitatorClient.ts`), falling back to the other on any infrastructure failure so an outage on either side never takes real revenue down with it. Traffic is pinned away from the coin flip via the `X-VAPE-Client` header in three cases: a real human paying in-browser through the site's wallet-connect flow (`docs/assets/hire.js`, tagged `site`) always gets CDP as primary, since Basescan's manually-curated "x402 payment" labels are tied to CDP's known relayer addresses and a person is the traffic class most likely to go check; `agents/data_agent.py`'s self-hires (tagged `data-agent`) always get CDP; `agents/data_agent_vapor.py`'s self-hires (tagged `data-agent-vapor`) always get VAPOR. Two explicitly-pinned agents replaced an earlier single agent that tried to alternate 50/50 via a KV-persisted toggle (`lib/dataAgentAlternator.ts`, removed) — that added a shared-state dependency for no real benefit over just running two independent, deterministic agents. Every other automated/agent route keeps the plain random 50/50 split. `lib/jobLog.ts` records which facilitator *actually* settled each job (accounting for a fallback having occurred, not just which one was picked as primary) — `GET /x402/stats`'s `by_facilitator` totals show the real achieved ratio.

## x402 Bazaar discovery + third-party directory listings

Every `/scan/<offering>` route declares Bazaar discovery metadata (`@x402/extensions/bazaar`'s `declareDiscoveryExtension`, registered via `resourceServer.registerExtension(bazaarResourceServerExtension)`, with the facilitator client wrapped in `withBazaar(...)`) — `iconUrl` points at VAPE's real favicon (`docs/assets/favicon-32.png`), and `serviceName`/`tags`/per-offering `output.example` match the real handler output shapes in `src/handlers.ts`.

**This is a best-effort announcement, not a guaranteed listing.** Read the actual x402 protocol spec directly ([coinbase/x402](https://github.com/coinbase/x402)'s `docs/extensions/bazaar.mdx`, since docs.cdp.coinbase.com is unreachable from this repo's dev sandbox) to confirm exactly what's required: a correctly-declared `bazaar` extension (which every route here has) plus a real settlement, after which the facilitator is supposed to echo an `EXTENSION-RESPONSES` header (`{"bazaar":{"status":"success"|"processing"|"rejected", "rejectedReason"?}}`) confirming the outcome. CDP's facilitator never emits that header at all — confirmed via network-level packet capture in [x402-foundation/x402#2112](https://github.com/x402-foundation/x402/issues/2112), **still open as of 2026-07-14** — so a fully spec-compliant integration (this one) has zero visibility into whether CDP actually indexed anything. A theory floated in that same issue thread (that indexing requires a CDP-provisioned payout wallet rather than an external EOA) does **not** appear anywhere in the official spec doc — unconfirmed speculation, not a documented requirement, so this repo isn't chasing it or changing `PAY_TO_ADDRESS`'s custody.

Since CDP won't tell us the outcome, `GET /admin/bazaar-status` checks it ourselves: queries CDP's own discovery catalog directly (JWT-authed, filtered by `PAY_TO_ADDRESS` so it never needs to paginate CDP's full ~20k-item catalog) and diffs it against VAPE's real offering list. `agents/cdp_bazaar_check.py` (`.github/workflows/cdp-bazaar-check.yml`, weekly) calls this route and logs a Memory finding only when the indexed count actually changes — not every run, since "still not indexed" every week is noise, not new information.

`agents/x402_directory_register.py` (run via `.github/workflows/x402-directory.yml`, `workflow_dispatch` only — not scheduled, since repeated calls to an unfamiliar directory's register endpoint with unknown dedup behavior risk creating duplicate listings) separately registers all 19 x402-routed offerings (6 `/scan/*` + 13 `/data/*`) with [402 Index](https://402index.io) (documented `POST /api/v1/register` API), VAPOR's own Bazaar-compatible discovery endpoint (a real registration contract, not a broken auto-listing one — see [jUXTAPOSITION1/VAPOR](https://github.com/jUXTAPOSITION1/VAPOR)'s docs/API.md), and prints ready-to-paste listing info for the directories that only take manual submissions: [x402 List](https://x402-list.com), [x402scan](https://www.x402scan.com/resources/register) (a real, independently-built ecosystem explorer that auto-validates a submitted URL's x402 schema, but has no documented POST API), [x402.study](https://x402.study), and [awesome-x402](https://github.com/xpaysh/awesome-x402) (a real, actively-curated list that takes PRs, not API calls).

Deliberately **not** wired up, each for a real, specific reason:
- **the402.ai** — a real marketplace, but its self-service registration (`POST /v1/register`) itself costs a real $0.01 x402 payment, meaning a CI job would need a funded, signing-capable wallet. That's a materially bigger, more sensitive lift than a plain POST and needs an explicit decision first.
- **402index.io domain verification** (`POST /api/v1/claim` → publish the returned hash at `/.well-known/402index-verify.txt` → `POST /api/v1/claim/verify`) would upgrade our listings from "pending review" to instantly-approved. Real, documented, and free, but the claim returns an ongoing edit credential (`verification_token`) that has to be stored as a real secret, and nothing in this repo's automation can write a new encrypted GitHub Actions secret — that step needs a human.
- **`_x402` DNS TXT record discovery** — a real IETF draft (`draft-jeftovic-x402-dns-discovery-00`), but still an early-stage draft, not a ratified standard, and would need a DNS record added in the Cloudflare dashboard.
- A `.well-known/x402.json` static manifest is a real, documented pattern too, but its exact schema comes from Coinbase's docs/example repo, both of which returned 403/404 when checked — rather than guess at a schema and ship something no real consumer can parse, this is left for whenever that can be confirmed against a primary source.

## `/scan/bounty_deep_dive` — the 24h-SLA premium offering ($50)

Unlike every other `/scan/*` route (synchronous — pay, get a JSON result, done in well under a second), this one genuinely can't complete inside a Worker's request window: the real work (`agents/deep_dive_audit.py` — recon + Slither + a frontier-model line-by-line source review) takes minutes, not milliseconds. So the route:

1. Gates payment exactly like the other 6 (x402, same middleware).
2. On settlement, calls `src/lib/githubDispatch.ts`'s `dispatchDeepDiveAudit()` — a `workflow_dispatch` REST call to `.github/workflows/deep-dive-bounty.yml`, passing `address`/`chain`/an optional `callback_url`.
3. Returns immediately with `{"status": "accepted", ...}` and where the report will land (`intel/audits/poc-reports/`) — never a synchronous result.

Needs `GH_DISPATCH_TOKEN` (a fine-grained PAT scoped to this repo, `Actions: write` + `Contents: read` — Workers have no equivalent of the `GITHUB_TOKEN` Actions injects into its own runs). Without it, the route still gates payment correctly but returns a `503` after settlement telling the buyer to use ACP instead — set this secret before advertising the x402 path for this offering. The ACP path (`scripts/acp-monitor/HANDLER_BRIEF.md`) doesn't need it — the host-side reasoning handler just runs `agents/deep_dive_audit.py` directly.

## Free reliability + pricing endpoints

Unpaid, no-x402-gate routes back the site's wallet profile ("Your Case File") and metrics strip:

- `GET /portfolio?address=0x…` — full auto-discovered native ETH + ERC-20 balances via Alchemy's `alchemy_getTokenBalances`/`alchemy_getTokenMetadata`, superseding the site's curated `docs/assets/base-tokens.json` fallback list. Needs `ALCHEMY_API_KEY`.
- `GET /nfts?address=0x…` — NFT holdings via Alchemy's NFT v3 API. Needs `ALCHEMY_API_KEY`.
- `GET /network-status` — current block number + gas price, more reliable than a direct call to the public `mainnet.base.org` RPC. Needs `ALCHEMY_API_KEY`.
- `GET /prices?addresses=0x…,0x…` — current USD price + 24h change for a batch of Base contract addresses, proxying CoinGecko with `COINGECKO_API_KEY` attached for better rate-limit headroom than the fully anonymous public tier (which the site's client-side JS falls back to directly if this route isn't available).
- `GET /cost-basis?address=0x…` — estimated cost-basis P&L per token (see `src/lib/costBasis.ts` for exactly what it computes — a single first-acquisition price point per token via Alchemy transfer history + CoinGecko's historical-price-by-contract endpoint, not full weighted-average accounting). Needs **both** `ALCHEMY_API_KEY` and `COINGECKO_API_KEY` — the historical-price endpoint specifically requires a CoinGecko key even on their free Demo tier (confirmed by testing it unauthenticated and getting rejected), unlike `/prices`' current-price lookup which works either way.

`/portfolio`, `/nfts`, and `/network-status` are cached at the edge for 20–60s (the Web Cache API, via Hono's built-in `cache` middleware — Cloudflare's `caches.open()` on Workers, Deno's own on the fallback) — Alchemy usage is metered, and `/network-status` in particular is identical for every visitor at a given moment, so this absorbs repeat requests instead of burning a fresh Alchemy call each time. Error responses (400/502/503) are never cached.

Alchemy-backed routes need `ALCHEMY_API_KEY` (a free-tier [Alchemy](https://dashboard.alchemy.com) app scoped to Base Mainnet); CoinGecko-backed routes need `COINGECKO_API_KEY` (a free [CoinGecko Demo API key](https://www.coingecko.com/en/api) — signup required, no payment). Every route here returns `503` if its required key(s) aren't set — the site (`docs/assets/app.js`/`profile.js`) treats that as "not deployed/configured yet" and transparently falls back to its direct public-API path (except `/cost-basis`, which has no keyless equivalent and just shows as unavailable), so the site works with or without this worker running.

## `dossier_check` — VAPE's deepest instant offering ($0.10)

Every other `/scan/*` route is a thin wrapper over `scan.ts`/`contractSource.ts`. `dossier_check` is the exception: it runs the real heuristic engine `agents/investigate.py` uses for every FREE VAPE investigation (`src/lib/investigateLite.ts`'s `score()` — a weighted CertiK-style rubric, meme-factory-template detection, recent-hack correlation), plus two things nothing else in the catalog does:

- **Public web-reputation search** (`src/lib/webResearch.ts`) — a real search for `"{symbol}" {address} rug pull OR scam OR honeypot OR exploit`, Tavily → Brave → keyless DuckDuckGo fallback, escalating the first unambiguous hit to a real page scrape (Firecrawl → keyless fetch fallback).
- **A live check of the project's own declared socials** — actually visits (scrapes) the website/Telegram/X URLs DexScreener reports, instead of only checking the array is non-empty like every other offering's `has_declared_socials` boolean. This is reachability, not a follower-count/account-age check — X's/Telegram's real metrics need an official paid API this repo doesn't hold.
- **A frontier-LLM quick read of the actual verified source** (`src/lib/llm.ts`) — Gemini 2.5 Pro, Groq fallback, same framing as the $50 `bounty_deep_dive` audit but a much smaller prompt/output budget matched to this offering's synchronous, instant-tier nature.

All three degrade gracefully exactly like `ETHERSCAN_API_KEY` above — without `TAVILY_API_KEY`/`BRAVE_API_KEY`, `FIRECRAWL_API_KEY`, and `GEMINI_API_KEY`/`GROQ_API_KEY` set, the corresponding section of the response reports `available: false` / `checked: 0` with an honest note rather than a fabricated result, and the score/verdict still reflects real GoPlus/DexScreener/Etherscan/Base-RPC data either way.

`agents/acp_fulfill.py::_dossier_check()` (via `agents/investigate.py::quick_assess()`) is the source of truth this mirrors field-for-field — see that module's docstrings for the exact same pipeline on the ACP side.

## Live x402 job ledger — `/x402/feed`, `/x402/stats`

Every real paid `/scan/*` call (any offering, settled or errored) gets logged in-house — `src/lib/jobLog.ts`, backed by a Cloudflare KV namespace (binding `VAPE_JOBS`). The site's live transaction feed (`docs/assets/x402feed.js`) reads these two free, unpaid endpoints:

- `GET /x402/feed?limit=50` — the most recent jobs (newest first): offering, token symbol/name, verdict, cost, latency, status, and — this is the part that makes it independently checkable, not just VAPE's word — the **real on-chain settlement transaction hash** (`tx_hash`) and payer address, captured from the x402 facilitator's own settlement response (`src/index.ts`'s `onAfterSettle` hook, not something this repo asserts on its own). The site links every entry straight to Basescan.
- `GET /x402/stats?days=30` — running totals (jobs, revenue, error count, per-offering breakdown) plus a daily time series for the site's revenue/volume chart.

**Setup (one-time, KV can't be a `wrangler secret`)**:
```bash
npx wrangler kv namespace create VAPE_JOBS
# -> copy the returned id into a new GitHub repo secret named VAPE_JOBS_KV_ID
```
`.github/workflows/deploy-worker.yml` appends the `[[kv_namespaces]]` binding to `wrangler.toml` at deploy time from that secret — never committed as a static value, since a placeholder id would fail `wrangler deploy` outright (see `wrangler.toml`'s `VAPE_JOBS` comment). Until `VAPE_JOBS_KV_ID` is set, every `/scan/*` route works exactly as before; `/x402/feed`/`/x402/stats` just 503 with `"job feed not configured"`.

**Honest framing, not fabricated precision**: "profit" isn't reported anywhere here — VAPE's real marginal cost per job is ~$0 (GoPlus/DexScreener/Etherscan are keyless; `dossier_check`'s optional Gemini/Groq calls run on their free tiers), so a manufactured cost-and-margin breakdown would just be theater. Revenue and job counts are the real, checkable numbers; the tx hash lets anyone verify a given job actually settled on Base rather than trusting this log alone.

## CI

`.github/workflows/deploy-worker.yml` deploys to Cloudflare on push to `main` when `worker/**` changes — needs `CLOUDFLARE_API_TOKEN` (Workers Scripts: Edit permission) and `CLOUDFLARE_ACCOUNT_ID` repo secrets; typechecks and no-ops without them rather than failing. `.github/workflows/worker-typecheck.yml` separately runs `deno check` on the same paths, so the Deno fallback path stays typechecked too. Deno Deploy's actual deployment is handled by its own GitHub integration, not a workflow file in this repo.

## Keeping scan logic in sync

`src/scan.ts` and `src/handlers.ts` are a field-for-field TypeScript port of `agents/token_scan.py` and `agents/acp_fulfill.py` — same GoPlus/DexScreener calls, same flag thresholds, same verdict logic, so the paid result, the real ACP deliverable, and the free browser preview (`docs/assets/app.js`'s `App.hunt()`) never disagree. If you change the Python, mirror the change here.
