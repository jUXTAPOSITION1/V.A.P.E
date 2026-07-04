# vape-x402

Pay-per-call access to VAPE's 6 automatable ACP offerings over Coinbase's [x402](https://www.x402.org/) HTTP payment protocol. The other 8 offerings (deep audits, forensics, wallet recon, etc.) need the SKILLFORGE tool tier and are hired through a real [ACP job](../docs/ACP_PROTOCOL.md) instead — this worker doesn't duplicate that.

## What's actually verified vs. what needs your setup

Verified in this session, without any live Cloudflare/Coinbase account:
- `npm install` resolves the real, current, published packages (`@x402/hono`, `@x402/core`, `@x402/evm`, `hono` — not `x402-hono` v1, which is deprecated).
- `npx tsc --noEmit` passes cleanly against the real published types.
- `npx wrangler deploy --dry-run` bundles the whole worker successfully and correctly reads `wrangler.toml`'s bindings.
- `npx wrangler dev --local` actually runs the worker: `GET /` returns the real offering catalog; `GET /scan/<offering>` correctly triggers the x402 middleware's facilitator handshake (it fails here only because this sandbox blocks outbound DNS to `facilitator.x402.org` — the same network policy that blocks CoinGecko/DexScreener elsewhere in this repo's dev sandbox).

**Not yet verified** (needs your accounts): an actual end-to-end payment (sign → 402 → resubmit → settle) against a real wallet, and a live Cloudflare deployment.

## Setup

```bash
cd worker
npm install
npx wrangler login          # opens a browser, needs your Cloudflare account
npx wrangler dev            # local dev server, real network this time
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
npx wrangler secret put ETHERSCAN_API_KEY   # optional — only exploit_check/safety_preflight use it
npx wrangler secret put CDP_API_KEY_ID      # required for real mainnet settlement — see below
npx wrangler secret put CDP_API_KEY_SECRET
npx wrangler secret put ALCHEMY_API_KEY     # optional — powers /portfolio, /nfts, /network-status
npx wrangler secret put COINGECKO_API_KEY   # optional — powers /prices, and required for /cost-basis
```

### Deploy

```bash
npx wrangler deploy
```

Ships on your `*.workers.dev` subdomain by default — no custom domain needed to start. **One manual one-time step**: Cloudflare requires you to register a `workers.dev` subdomain from the dashboard before the first deploy of any Worker on a fresh account will actually publish; `wrangler deploy` will tell you if this is still pending.

## Alternative: Deno Deploy (no subdomain registration step)

The Cloudflare path above needs a one-time `workers.dev` subdomain registration on your account before the first deploy will actually publish — on at least one real account this hit a Cloudflare-side bug where that registration silently never completed (dashboard showed no way to fix it: the per-Worker URL stayed `*-null` even with the toggle on, `/workers/onboarding` 404'd, and three separate deploy paths — Wrangler, Cloudflare's own Git integration, and its "Create Application" wizard — all failed identically). If you hit the same wall, `worker/` also runs unmodified on [Deno Deploy](https://deno.com/deploy), which assigns a working `https://<project>.deno.dev` URL automatically on first deploy — no manual step.

This works because `src/index.ts`'s Hono `app` object has zero Cloudflare-specific code — the only Workers-specific things are `wrangler.toml` and how `c.env` gets populated. `deno/deno-entry.ts` is the Deno equivalent of that: it builds the same `Env` shape from `Deno.env.get(...)` and calls `app.fetch(req, env)` directly (Hono's documented pattern for feeding `c.env` on any non-Workers runtime).

`deno/deno.json` (its own directory, deliberately **not** next to `package.json`) holds the import map aliasing the same npm packages `worker/package.json` uses — `hono`, `@x402/hono`, `@x402/core`, `@x402/evm`, `@x402/extensions`, `jose` — to their `npm:` specifiers Deno resolves natively, plus `"nodeModulesDir": "none"`. Both matter: a `deno.json` sitting next to a `package.json` makes Deno auto-detect a Node "workspace" and try to resolve *every* dependency in `package.json` — including unrelated devDependencies like `tsx`/`wrangler`/`typescript` that the Deno runtime never imports — which failed in an actual Deno Deploy build with an unrelated npm version-resolution error before this was separated out.

Verified locally in this session (via `npm install deno` — Deno ships as an npm package too):
- `deno check deno-entry.ts` (run from `worker/deno/`) passes cleanly.
- `deno task start` runs the real server: `GET /` returns the same offering catalog as the Cloudflare version, `GET /portfolio` and `GET /network-status` correctly 503 without `ALCHEMY_API_KEY`, and `GET /scan/<offering>` correctly reaches the x402 middleware's facilitator handshake (fails only on outbound network access to `api.cdp.coinbase.com` in this dev sandbox — the same block that affects `wrangler dev` and the Cloudflare API from here).
- A live Deno Deploy build with the entry point pointed at `worker/src/deno-entry.ts` (its original location) failed with `Could not find "@x402/core" in a node_modules folder` — Deno Deploy's remote build runs `npm install` first and switches to strict "bring your own node_modules" resolution when it sees a sibling `package.json`, which doesn't consult the import map for scoped-package subpaths the way local `deno check`/`run` does. Moving the Deno-only files into their own `worker/deno/` directory (no `package.json` there) avoids this entirely — confirmed via a second local `deno check` run with `worker/node_modules` present the whole time, matching what Deno Deploy's build environment sees.

To deploy:
```bash
npm install deno    # or the standalone installer at deno.com/deploy — either works
cd worker/deno
deno task start     # local smoke test first; needs env vars set (see below)
```

Then at [dash.deno.com](https://dash.deno.com):
1. **New Project → GitHub → jUXTAPOSITION1/V.A.P.E**.
2. Set the **entry point** to `worker/deno/deno-entry.ts` (not `worker/src/deno-entry.ts` — see above).
3. Add the same environment variables as the Cloudflare secrets above (`PAY_TO_ADDRESS`, `X402_NETWORK`, `X402_FACILITATOR_URL`, `CDP_API_KEY_ID`, `CDP_API_KEY_SECRET`, `ALCHEMY_API_KEY`, `ETHERSCAN_API_KEY`) — Deno Deploy's project settings support marking these as secrets (hidden after save, same as `wrangler secret put`).
4. Deploy. You get `https://<project-name>.deno.dev` immediately — update `docs/assets/app.js`'s and `docs/assets/profile.js`'s `WORKER_BASE` constant to that URL.

If you go this route instead of Cloudflare, `.github/workflows/deploy-worker.yml` and the `wrangler.toml`-based secrets above become unused — Deno Deploy's own GitHub integration handles CI on every push, so that workflow file can be deleted (or left inert; it only runs on `worker/**` changes and no-ops without `CLOUDFLARE_API_TOKEN`).

## Base mainnet + Coinbase Developer Platform

`wrangler.toml` is pointed at **Base mainnet** (`eip155:8453`) and CDP's hosted facilitator (`https://api.cdp.coinbase.com/platform/v2/x402`) — real funds move through this. The pay → verify → settle loop was proven first against Base Sepolia + the free public `facilitator.x402.org` facilitator before this switch (see git history on `wrangler.toml`/`src/index.ts` for the testnet config if you need to reproduce that).

To actually settle payments you need a [CDP Secret API Key](https://portal.cdp.coinbase.com) (`CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` above) — `src/lib/cdpAuth.ts` mints a Bearer JWT from it for every `/verify`, `/settle`, and `/supported` call to the facilitator (`src/index.ts`'s `buildCreateAuthHeaders()`). Without both secrets set, those calls go out unauthenticated and the facilitator returns 401.

## x402 Bazaar discovery + third-party directory listings

Every `/scan/<offering>` route declares Bazaar discovery metadata (`@x402/extensions/bazaar`'s `declareDiscoveryExtension`, registered via `resourceServer.registerExtension(bazaarResourceServerExtension)`, with the facilitator client wrapped in `withBazaar(...)`) — `iconUrl` points at VAPE's real favicon (`docs/assets/favicon-32.png`), and `serviceName`/`tags`/per-offering `output.example` match the real handler output shapes in `src/handlers.ts`.

**This is a best-effort announcement, not a guaranteed listing.** As of this writing Bazaar indexing has a live, unresolved bug ([x402-foundation/x402#2112](https://github.com/x402-foundation/x402/issues/2112)) where correctly-implemented services following this exact pattern still don't get indexed, and one open theory is that it may require a CDP-provisioned payout wallet rather than an external EOA — VAPE's `PAY_TO_ADDRESS` is its existing ACP wallet (an external EOA), so indexing may simply not happen regardless of how correct this wiring is. Settlement is unaffected either way; this only touches discovery metadata.

`agents/x402_directory_register.py` (run via `.github/workflows/x402-directory.yml`, `workflow_dispatch` only — not scheduled, since repeated calls to an unfamiliar directory's register endpoint with unknown dedup behavior risk creating duplicate listings) separately registers VAPE's 6 offerings with [402 Index](https://402index.io) (documented `POST /api/v1/register` API) and prints a ready-to-paste manifest for [x402 List](https://x402-list.com) (no documented public submission API — manual web-form only).

## Free reliability + pricing endpoints

Unpaid, no-x402-gate routes back the site's wallet profile ("Your Case File") and metrics strip:

- `GET /portfolio?address=0x…` — full auto-discovered native ETH + ERC-20 balances via Alchemy's `alchemy_getTokenBalances`/`alchemy_getTokenMetadata`, superseding the site's curated `docs/assets/base-tokens.json` fallback list. Needs `ALCHEMY_API_KEY`.
- `GET /nfts?address=0x…` — NFT holdings via Alchemy's NFT v3 API. Needs `ALCHEMY_API_KEY`.
- `GET /network-status` — current block number + gas price, more reliable than a direct call to the public `mainnet.base.org` RPC. Needs `ALCHEMY_API_KEY`.
- `GET /prices?addresses=0x…,0x…` — current USD price + 24h change for a batch of Base contract addresses, proxying CoinGecko with `COINGECKO_API_KEY` attached for better rate-limit headroom than the fully anonymous public tier (which the site's client-side JS falls back to directly if this route isn't available).
- `GET /cost-basis?address=0x…` — estimated cost-basis P&L per token (see `src/lib/costBasis.ts` for exactly what it computes — a single first-acquisition price point per token via Alchemy transfer history + CoinGecko's historical-price-by-contract endpoint, not full weighted-average accounting). Needs **both** `ALCHEMY_API_KEY` and `COINGECKO_API_KEY` — the historical-price endpoint specifically requires a CoinGecko key even on their free Demo tier (confirmed by testing it unauthenticated and getting rejected), unlike `/prices`' current-price lookup which works either way.

Alchemy-backed routes need `ALCHEMY_API_KEY` (a free-tier [Alchemy](https://dashboard.alchemy.com) app scoped to Base Mainnet); CoinGecko-backed routes need `COINGECKO_API_KEY` (a free [CoinGecko Demo API key](https://www.coingecko.com/en/api) — signup required, no payment). Every route here returns `503` if its required key(s) aren't set — the site (`docs/assets/app.js`/`profile.js`) treats that as "not deployed/configured yet" and transparently falls back to its direct public-API path (except `/cost-basis`, which has no keyless equivalent and just shows as unavailable), so the site works with or without this worker running.

## CI

`.github/workflows/deploy-worker.yml` deploys on push to `main` when `worker/**` changes. It needs two repo secrets before it can run: `CLOUDFLARE_API_TOKEN` (Workers Scripts: Edit permission) and `CLOUDFLARE_ACCOUNT_ID`.

## Keeping scan logic in sync

`src/scan.ts` and `src/handlers.ts` are a field-for-field TypeScript port of `agents/token_scan.py` and `agents/acp_fulfill.py` — same GoPlus/DexScreener calls, same flag thresholds, same verdict logic, so the paid result, the real ACP deliverable, and the free browser preview (`docs/assets/app.js`'s `App.hunt()`) never disagree. If you change the Python, mirror the change here.
