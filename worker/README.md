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
```

### Deploy

```bash
npx wrangler deploy
```

Ships on your `*.workers.dev` subdomain by default — no custom domain needed to start. **One manual one-time step**: Cloudflare requires you to register a `workers.dev` subdomain from the dashboard before the first deploy of any Worker on a fresh account will actually publish; `wrangler deploy` will tell you if this is still pending.

## Base mainnet + Coinbase Developer Platform

`wrangler.toml` is pointed at **Base mainnet** (`eip155:8453`) and CDP's hosted facilitator (`https://api.cdp.coinbase.com/platform/v2/x402`) — real funds move through this. The pay → verify → settle loop was proven first against Base Sepolia + the free public `facilitator.x402.org` facilitator before this switch (see git history on `wrangler.toml`/`src/index.ts` for the testnet config if you need to reproduce that).

To actually settle payments you need a [CDP Secret API Key](https://portal.cdp.coinbase.com) (`CDP_API_KEY_ID` / `CDP_API_KEY_SECRET` above) — `src/lib/cdpAuth.ts` mints a Bearer JWT from it for every `/verify`, `/settle`, and `/supported` call to the facilitator (`src/index.ts`'s `buildCreateAuthHeaders()`). Without both secrets set, those calls go out unauthenticated and the facilitator returns 401.

## Free Alchemy-backed reliability endpoints

Three unpaid, no-x402-gate routes back the site's wallet profile ("Your Case File") and metrics strip:

- `GET /portfolio?address=0x…` — full auto-discovered native ETH + ERC-20 balances via Alchemy's `alchemy_getTokenBalances`/`alchemy_getTokenMetadata`, superseding the site's curated `docs/assets/base-tokens.json` fallback list.
- `GET /nfts?address=0x…` — NFT holdings via Alchemy's NFT v3 API.
- `GET /network-status` — current block number + gas price, more reliable than a direct call to the public `mainnet.base.org` RPC.

All three need `ALCHEMY_API_KEY` (a free-tier [Alchemy](https://dashboard.alchemy.com) app scoped to Base Mainnet) and return `503` if it isn't set — the site (`docs/assets/app.js`/`profile.js`) treats that as "not deployed yet" and transparently falls back to its direct public-API path, so the site works identically with or without this worker running.

## CI

`.github/workflows/deploy-worker.yml` deploys on push to `main` when `worker/**` changes. It needs two repo secrets before it can run: `CLOUDFLARE_API_TOKEN` (Workers Scripts: Edit permission) and `CLOUDFLARE_ACCOUNT_ID`.

## Keeping scan logic in sync

`src/scan.ts` and `src/handlers.ts` are a field-for-field TypeScript port of `agents/token_scan.py` and `agents/acp_fulfill.py` — same GoPlus/DexScreener calls, same flag thresholds, same verdict logic, so the paid result, the real ACP deliverable, and the free browser preview (`docs/assets/app.js`'s `App.hunt()`) never disagree. If you change the Python, mirror the change here.
