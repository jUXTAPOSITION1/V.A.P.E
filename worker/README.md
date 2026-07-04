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
```

### Deploy

```bash
npx wrangler deploy
```

Ships on your `*.workers.dev` subdomain by default — no custom domain needed to start.

## Testnet first, then mainnet

`wrangler.toml` defaults to **Base Sepolia** (`eip155:84532`) and the free public facilitator (`facilitator.x402.org`) — no Coinbase account needed to prove the full loop with test funds. To go live on Base mainnet:

1. Get [Coinbase Developer Platform](https://portal.cdp.coinbase.com) credentials.
2. Change `X402_NETWORK` in `wrangler.toml` to `"eip155:8453"`.
3. Change `X402_FACILITATOR_URL` to your CDP-hosted facilitator endpoint.
4. If that facilitator needs auth headers, wire them via `HTTPFacilitatorClient`'s `createAuthHeaders` option in `src/index.ts`, backed by `wrangler secret put` — never a plaintext var.

## CI

`.github/workflows/deploy-worker.yml` deploys on push to `main` when `worker/**` changes. It needs two repo secrets before it can run: `CLOUDFLARE_API_TOKEN` (Workers Scripts: Edit permission) and `CLOUDFLARE_ACCOUNT_ID`.

## Keeping scan logic in sync

`src/scan.ts` and `src/handlers.ts` are a field-for-field TypeScript port of `agents/token_scan.py` and `agents/acp_fulfill.py` — same GoPlus/DexScreener calls, same flag thresholds, same verdict logic, so the paid result, the real ACP deliverable, and the free browser preview (`docs/assets/app.js`'s `App.hunt()`) never disagree. If you change the Python, mirror the change here.
