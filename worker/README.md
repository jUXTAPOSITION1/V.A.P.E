# vape-x402

Pay-per-call access to VAPE's 6 automatable ACP offerings over Coinbase's [x402](https://www.x402.org/) HTTP payment protocol. The other 8 offerings (deep audits, forensics, wallet recon, etc.) need the SKILLFORGE tool tier and are hired through a real [ACP job](../docs/ACP_PROTOCOL.md) instead — this worker doesn't duplicate that.

Runs on [Deno Deploy](https://deno.com/deploy), not Cloudflare Workers — see "Why Deno Deploy, not Cloudflare" below for the history, if you're wondering why `src/index.ts` still reads like Workers code.

## Setup

```bash
cd worker
npm install
npm run dev     # runs worker/deno/deno-entry.ts locally via `deno task start`
```

Try the unpaid route first:
```bash
curl http://localhost:8000/
```

Then a paid one (expect a real `402` with payment requirements, since you have no payment header yet):
```bash
curl -i "http://localhost:8000/scan/token_safety_check?address=0x2b601d7fc4705361F0c0249a005a714b7A3EdaFE"
```

### Environment variables

Set these as environment variables in the Deno Deploy project settings (mark them "secret" there — hidden after save, same idea as `wrangler secret put`):

| Variable | Required | Used for |
|---|---|---|
| `PAY_TO_ADDRESS` | [OK] | payout wallet for every settled x402 call — VAPE's existing ACP wallet |
| `X402_NETWORK` | [OK] | `eip155:8453` (Base mainnet) |
| `X402_FACILITATOR_URL` | [OK] | `https://api.cdp.coinbase.com/platform/v2/x402` |
| `CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` | required for real settlement | mints the Bearer JWT `src/lib/cdpAuth.ts` needs for every `/verify`/`/settle` call — see [CDP Secret API Key](https://portal.cdp.coinbase.com) |
| `ETHERSCAN_API_KEY` | optional | only `exploit_check`/`safety_preflight` use it |
| `ALCHEMY_API_KEY` | optional | powers `/portfolio`, `/nfts`, `/network-status` |
| `COINGECKO_API_KEY` | optional | powers `/prices`; required for `/cost-basis` |
| `GH_DISPATCH_TOKEN` | optional | powers `/scan/bounty_deep_dive` (see below) |

Locally, export these in your shell before `npm run dev`; `deno-entry.ts` reads them via `Deno.env.get(...)`.

### Deploy

At [dash.deno.com](https://dash.deno.com):
1. **New Project → GitHub → jUXTAPOSITION1/V.A.P.E**.
2. Set the **entry point** to `worker/deno/deno-entry.ts`.
3. Add the environment variables above in the project's settings.
4. Deploy. Deno assigns a working `https://<project>.deno.dev` URL immediately — no manual subdomain registration step. If you ever change the project name/URL, update `docs/assets/app.js`'s and `docs/assets/profile.js`'s `WORKER_BASE` constant to match.

Every push to `main` that touches `worker/**` auto-deploys via Deno Deploy's own GitHub integration — no workflow file, no token, nothing in this repo's CI drives it. `.github/workflows/worker-typecheck.yml` only runs `deno check` on PRs/pushes to catch type errors before merge; it never deploys anything.

### Why Deno Deploy, not Cloudflare

This started on Cloudflare Workers, and `src/index.ts` still reads like Workers code because the actual application logic has zero Cloudflare-specific dependencies — it's a plain Hono `app`, and `deno-entry.ts` just feeds it the same `Env` shape via `Deno.env.get(...)` instead of a Workers binding (Hono's documented pattern for any non-Workers runtime).

The move happened because one real Cloudflare account hit a subdomain-registration bug that never got resolved: `workers.dev` registration silently never completed (the per-Worker URL stayed `*-null` even with the toggle on, `/workers/onboarding` 404'd, and three separate deploy paths — Wrangler, Cloudflare's own Git integration, and its "Create Application" wizard — all failed identically). Deno Deploy assigns a working `*.deno.dev` URL automatically on first deploy, with no equivalent manual step, so this repo now runs there instead. There's no remaining Cloudflare dependency anywhere in this project — no `wrangler.toml`, no Cloudflare secrets, no Cloudflare Workers Builds Git integration should be connected to this repo (disconnect it from the Cloudflare dashboard if it still shows up posting build-status comments on PRs).

`deno/deno.json` (its own directory, deliberately **not** next to `package.json`) holds the import map aliasing the same npm packages `worker/package.json` uses — `hono`, `@x402/hono`, `@x402/core`, `@x402/evm`, `@x402/extensions`, `jose` — to their `npm:` specifiers Deno resolves natively, plus `"nodeModulesDir": "none"`. Both matter: a `deno.json` sitting next to a `package.json` makes Deno auto-detect a Node "workspace" and try to resolve *every* dependency in `package.json` — including devDependencies Deno never imports — which failed in an actual Deno Deploy build with an unrelated npm version-resolution error before this was separated out. Similarly, the entry point must be `worker/deno/deno-entry.ts`, not a copy sitting next to `package.json` — Deno Deploy's remote build runs `npm install` first and switches to strict "bring your own node_modules" resolution when it sees a sibling `package.json`, which doesn't consult the import map for scoped-package subpaths the way `deno check`/`deno run` do locally.

## Base mainnet + Coinbase Developer Platform

This runs against **Base mainnet** (`eip155:8453`) and CDP's hosted facilitator (`https://api.cdp.coinbase.com/platform/v2/x402`) — real funds move through this. The pay → verify → settle loop was proven first against Base Sepolia + the free public `facilitator.x402.org` facilitator before this switch (see git history on `src/index.ts` for the testnet config if you need to reproduce that).

To actually settle payments you need a [CDP Secret API Key](https://portal.cdp.coinbase.com) (`CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` above) — `src/lib/cdpAuth.ts` mints a Bearer JWT from it for every `/verify`, `/settle`, and `/supported` call to the facilitator (`src/index.ts`'s `buildCreateAuthHeaders()`). Without both secrets set, those calls go out unauthenticated and the facilitator returns 401.

## x402 Bazaar discovery + third-party directory listings

Every `/scan/<offering>` route declares Bazaar discovery metadata (`@x402/extensions/bazaar`'s `declareDiscoveryExtension`, registered via `resourceServer.registerExtension(bazaarResourceServerExtension)`, with the facilitator client wrapped in `withBazaar(...)`) — `iconUrl` points at VAPE's real favicon (`docs/assets/favicon-32.png`), and `serviceName`/`tags`/per-offering `output.example` match the real handler output shapes in `src/handlers.ts`.

**This is a best-effort announcement, not a guaranteed listing.** As of this writing Bazaar indexing has a live, unresolved bug ([x402-foundation/x402#2112](https://github.com/x402-foundation/x402/issues/2112)) where correctly-implemented services following this exact pattern still don't get indexed, and one open theory is that it may require a CDP-provisioned payout wallet rather than an external EOA — VAPE's `PAY_TO_ADDRESS` is its existing ACP wallet (an external EOA), so indexing may simply not happen regardless of how correct this wiring is. Settlement is unaffected either way; this only touches discovery metadata.

`agents/x402_directory_register.py` (run via `.github/workflows/x402-directory.yml`, `workflow_dispatch` only — not scheduled, since repeated calls to an unfamiliar directory's register endpoint with unknown dedup behavior risk creating duplicate listings) separately registers VAPE's 6 offerings with [402 Index](https://402index.io) (documented `POST /api/v1/register` API) and prints a ready-to-paste manifest for [x402 List](https://x402-list.com) (no documented public submission API — manual web-form only).

## `/scan/bounty_deep_dive` — the 24h-SLA premium offering ($50)

Unlike every other `/scan/*` route (synchronous — pay, get a JSON result, done in well under a second), this one genuinely can't complete inside a single request: the real work (`agents/deep_dive_audit.py` — recon + Slither + a frontier-model line-by-line source review) takes minutes, not milliseconds. So the route:

1. Gates payment exactly like the other 6 (x402, same middleware).
2. On settlement, calls `src/lib/githubDispatch.ts`'s `dispatchDeepDiveAudit()` — a `workflow_dispatch` REST call to `.github/workflows/deep-dive-bounty.yml`, passing `address`/`chain`/an optional `callback_url`.
3. Returns immediately with `{"status": "accepted", ...}` and where the report will land (`intel/audits/poc-reports/`) — never a synchronous result.

Needs `GH_DISPATCH_TOKEN` (a fine-grained PAT scoped to this repo, `Actions: write` + `Contents: read` — Deno Deploy has no equivalent of a CI-injected token). Without it, the route still gates and settles payment correctly but returns a `503` after settlement telling the buyer to use ACP instead — set this variable before advertising the x402 path for this offering. The ACP path (`scripts/acp-monitor/HANDLER_BRIEF.md`) doesn't need it — the host-side reasoning handler just runs `agents/deep_dive_audit.py` directly.

## Free reliability + pricing endpoints

Unpaid, no-x402-gate routes back the site's wallet profile ("Your Case File") and metrics strip:

- `GET /portfolio?address=0x…` — full auto-discovered native ETH + ERC-20 balances via Alchemy's `alchemy_getTokenBalances`/`alchemy_getTokenMetadata`, superseding the site's curated `docs/assets/base-tokens.json` fallback list. Needs `ALCHEMY_API_KEY`.
- `GET /nfts?address=0x…` — NFT holdings via Alchemy's NFT v3 API. Needs `ALCHEMY_API_KEY`.
- `GET /network-status` — current block number + gas price, more reliable than a direct call to the public `mainnet.base.org` RPC. Needs `ALCHEMY_API_KEY`.
- `GET /prices?addresses=0x…,0x…` — current USD price + 24h change for a batch of Base contract addresses, proxying CoinGecko with `COINGECKO_API_KEY` attached for better rate-limit headroom than the fully anonymous public tier (which the site's client-side JS falls back to directly if this route isn't available).
- `GET /cost-basis?address=0x…` — estimated cost-basis P&L per token (see `src/lib/costBasis.ts` for exactly what it computes — a single first-acquisition price point per token via Alchemy transfer history + CoinGecko's historical-price-by-contract endpoint, not full weighted-average accounting). Needs **both** `ALCHEMY_API_KEY` and `COINGECKO_API_KEY` — the historical-price endpoint specifically requires a CoinGecko key even on their free Demo tier (confirmed by testing it unauthenticated and getting rejected), unlike `/prices`' current-price lookup which works either way.

`/portfolio`, `/nfts`, and `/network-status` are cached at the edge for 20–60s (Deno's `caches.open()` Web Cache API, via Hono's built-in `cache` middleware) — Alchemy usage is metered, and `/network-status` in particular is identical for every visitor at a given moment, so this absorbs repeat requests instead of burning a fresh Alchemy call each time. Error responses (400/502/503) are never cached.

Alchemy-backed routes need `ALCHEMY_API_KEY` (a free-tier [Alchemy](https://dashboard.alchemy.com) app scoped to Base Mainnet); CoinGecko-backed routes need `COINGECKO_API_KEY` (a free [CoinGecko Demo API key](https://www.coingecko.com/en/api) — signup required, no payment). Every route here returns `503` if its required key(s) aren't set — the site (`docs/assets/app.js`/`profile.js`) treats that as "not deployed/configured yet" and transparently falls back to its direct public-API path (except `/cost-basis`, which has no keyless equivalent and just shows as unavailable), so the site works with or without this worker running.

## CI

`.github/workflows/worker-typecheck.yml` runs `deno check` against `worker/deno/deno-entry.ts` on every push/PR touching `worker/**` — no secrets, no `npm ci`, nothing to skip. It only catches type errors; it never deploys. Deployment is entirely Deno Deploy's own GitHub integration (see "Deploy" above).

## Keeping scan logic in sync

`src/scan.ts` and `src/handlers.ts` are a field-for-field TypeScript port of `agents/token_scan.py` and `agents/acp_fulfill.py` — same GoPlus/DexScreener calls, same flag thresholds, same verdict logic, so the paid result, the real ACP deliverable, and the free browser preview (`docs/assets/app.js`'s `App.hunt()`) never disagree. If you change the Python, mirror the change here.
