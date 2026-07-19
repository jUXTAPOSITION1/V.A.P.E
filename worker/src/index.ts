/**
 * VAPE x402 payment worker — pay-per-call access to 21 of the 29 "auto" ACP
 * offerings (see docs/ACP_PROTOCOL.md / data/reputation.json for the full
 * 29-offering catalog; the other 8 need the SKILLFORGE tool tier and are
 * hired via a real ACP job instead). Also hosts a few free, unpaid Alchemy-
 * backed reliability endpoints (/portfolio, /nfts, /network-status, /prices,
 * /cost-basis) that the site's wallet profile and metrics strip prefer over
 * direct public-RPC calls when this worker is deployed and configured, plus
 * two free Codex.io-backed routes (/virtuals-snapshot, /trending-base) for
 * the Live Intelligence Feed's Virtuals Protocol panel and trending-tokens
 * list — Codex needs a bearer key that can't ship to the browser, so these
 * can't be a direct client-side fetch the way DefiLlama/CoinGecko are — and
 * one free, fully keyless Polymarket/Kalshi-backed route (/prediction-markets).
 *
 * Runs on Base mainnet, real funds, against a 50/50 hybrid of VAPOR (our own
 * facilitator) and Coinbase Developer Platform's hosted one — see
 * wrangler.toml for the network/facilitator config and required secrets,
 * and lib/facilitatorClient.ts for the hybrid routing itself.
 */
import { Hono } from "hono";
import { cors } from "hono/cors";
import { cache } from "hono/cache";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { declareDiscoveryExtension, bazaarResourceServerExtension, withBazaar } from "@x402/extensions/bazaar";
import { fulfill, type HandlerName } from "./handlers";
import { DL_OFFERINGS, fulfillData, type DlQuery } from "./dataHandlers";
import { generateCdpJwt } from "./lib/cdpAuth";
import { getPortfolio, getNftsForOwner, getNetworkStatus } from "./lib/alchemy";
import { getCurrentPrices } from "./lib/coingecko";
import { estimateCostBasis } from "./lib/costBasis";
import * as codex from "./lib/codex";
import * as predictionMarkets from "./lib/predictionMarkets";
import { dispatchDeepDiveAudit, dispatchExternalBountyAudit } from "./lib/githubDispatch";
import { logJob, getFeed, getStats, type KVLike, type JobRecord } from "./lib/jobLog";
import { FallbackFacilitatorClient } from "./lib/facilitatorClient";
import type { Context } from "hono";

// CAIP-2 chain identifier, e.g. "eip155:8453" (Base) or "eip155:84532" (Base Sepolia).
type Caip2Network = `${string}:${string}`;

export interface Env {
  ETHERSCAN_API_KEY?: string;
  CDP_API_KEY_ID?: string;
  CDP_API_KEY_SECRET?: string;
  ALCHEMY_API_KEY?: string;
  COINGECKO_API_KEY?: string;
  // Codex.io GraphQL data (trending tokens, holders, wallet PnL) — see
  // lib/codex.ts. Server-side only; Codex requires a bearer key that can
  // never be shipped to the browser, unlike the keyless DefiLlama/CoinGecko
  // calls the site makes directly.
  CODEX_API_KEY?: string;
  // Fine-grained PAT (Actions: write, Contents: read) for triggering the
  // bounty_deep_dive offering's async job — see worker/src/lib/githubDispatch.ts.
  GH_DISPATCH_TOKEN?: string;
  // dossier_check's web-reputation search + declared-social scrape +
  // frontier-LLM quick read — all optional, degrade gracefully exactly like
  // ETHERSCAN_API_KEY above. See lib/webResearch.ts / lib/llm.ts.
  TAVILY_API_KEY?: string;
  BRAVE_API_KEY?: string;
  FIRECRAWL_API_KEY?: string;
  GEMINI_API_KEY?: string;
  GROQ_API_KEY?: string;
  PAY_TO_ADDRESS: string;
  X402_NETWORK: Caip2Network;
  // CDP's hosted facilitator — one half of the real 50/50 hybrid split with
  // VAPOR (see lib/facilitatorClient.ts). Kept as the required var since
  // every existing deployment already has it configured; it's also the sole
  // facilitator whenever VAPOR_FACILITATOR_URL isn't set.
  X402_FACILITATOR_URL: string;
  // VAPOR (our own facilitator, x402.duckdns.org) — the other half of the
  // hybrid split when set. Each request picks VAPOR or CDP as primary with
  // even odds, falling back to the other on any error so an outage on
  // either side never takes real revenue down with it.
  VAPOR_FACILITATOR_URL?: string;
  // In-house x402 job ledger (see lib/jobLog.ts) — optional exactly like the
  // API keys above: wire it once `VAPE_JOBS_KV_ID` is set (see
  // worker/README.md), and until then every /scan/* route still works
  // exactly as before, it just isn't logged to the live feed.
  VAPE_JOBS?: KVLike;
}

// Per-request Hono variable used to hand the job's real result (offering
// output, latency) from the route handler up to the payment middleware's
// onAfterSettle hook, which is the only place the real settlement facts
// (payer, on-chain tx hash, network) actually exist. @x402/hono settles
// strictly AFTER the route handler resolves (see paymentMiddlewareFromHTTPServer:
// `await next()` runs the handler, THEN `processSettlement()` fires
// onAfterSettle) — so the handler can never see its own settlement, only the
// hook can. jobLog.logJob() is therefore called from onAfterSettle, not the
// handler, once both halves are available.
type Variables = {
  vapeJobDraft?: Omit<JobRecord, "payer" | "tx_hash" | "network">;
};

const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

// Alchemy/CoinGecko URLs embed the API key as a path/query segment, so any
// thrown error whose message echoes the request URL (e.g. a generic fetch
// failure) could otherwise leak it into a public API response. Strip both
// known key env vars out of the message before surfacing it — this is
// deliberately not swallowed to a generic string, matching exploit_check/
// dossier_check's "surface real failures" fix: a vague "upstream lookup
// failed" with no detail looks identical whether the key is wrong, Alchemy
// rate-limited us, or the address just has too many token balances to batch.
function errDetail(e: unknown, env: Env): string {
  let msg = e instanceof Error ? e.message : String(e);
  if (env.ALCHEMY_API_KEY) msg = msg.split(env.ALCHEMY_API_KEY).join("***");
  if (env.COINGECKO_API_KEY) msg = msg.split(env.COINGECKO_API_KEY).join("***");
  if (env.CDP_API_KEY_SECRET) msg = msg.split(env.CDP_API_KEY_SECRET).join("***");
  return msg;
}

/**
 * Builds the facilitator's `createAuthHeaders` callback. Only CDP's hosted
 * facilitator (api.cdp.coinbase.com) needs Bearer JWT auth; the public
 * testnet facilitator (facilitator.x402.org) needs none, so this is a no-op
 * unless both CDP secrets are configured (`wrangler secret put`).
 *
 * The callback signature takes no arguments — the client picks the right
 * header set (verify/settle/supported) out of the returned object — so a
 * fresh, correctly-scoped JWT is minted for each of the three endpoints on
 * every call rather than reused across them (CDP JWTs bind `uris` to one
 * exact method+path and expire after 120s, so they're not reusable anyway).
 */
function buildCreateAuthHeaders(env: Env) {
  if (!env.CDP_API_KEY_ID || !env.CDP_API_KEY_SECRET) return undefined;
  const apiKeyId = env.CDP_API_KEY_ID;
  const apiKeySecret = env.CDP_API_KEY_SECRET;
  const host = new URL(env.X402_FACILITATOR_URL).host;
  const basePath = new URL(env.X402_FACILITATOR_URL).pathname;

  const jwtFor = async (method: string, subPath: string) => {
    const jwt = await generateCdpJwt({
      apiKeyId,
      apiKeySecret,
      requestMethod: method,
      requestHost: host,
      requestPath: `${basePath}${subPath}`,
    });
    return { Authorization: `Bearer ${jwt}` };
  };

  return async () => ({
    verify: await jwtFor("POST", "/verify"),
    settle: await jwtFor("POST", "/settle"),
    supported: await jwtFor("GET", "/supported"),
  });
}

// Prices match data/reputation.json exactly — this file is the payment
// surface, not a second source of truth; if prices change there, update here.
const OFFERING_PRICES: Record<HandlerName, string> = {
  exploit_check: "$0.01",
  token_safety_check: "$0.02",
  liquidity_check: "$0.02",
  rug_pull_alert: "$0.03",
  market_intel: "$0.07",
  dossier_check: "$0.10",
};

// Literally VAPE's favicon (docs/index.html's <link rel="icon">), reused
// here so the x402 Bazaar listing shows the same icon a human sees in their
// browser tab, not a separate logo asset.
const ICON_URL = "https://juxtaposition1.github.io/V.A.P.E/assets/favicon-32.png";

// Per-offering discovery metadata for the x402 Bazaar (see
// x402-foundation/x402#2112 — Bazaar indexing has open, unresolved bugs even
// for correctly-implemented services, and may require a CDP-provisioned
// payout wallet rather than VAPE's external ACP EOA; this is a best-effort
// announcement, not a guaranteed listing). Mirrors the real output shape of
// each agents/acp_fulfill.py / worker/src/handlers.ts handler exactly — no
// invented fields.
const OFFERING_DISCOVERY: Record<HandlerName, { description: string; output: Record<string, unknown> }> = {
  exploit_check: {
    description: "Contract verification + proxy-swap surface check.",
    output: { address: "0x...", verified: true, contract_name: "Token", proxy: false },
  },
  token_safety_check: {
    description: "Full GoPlus + DexScreener token safety scan with CertiK-style scoring.",
    output: { address: "0x...", verdict: "PROCEED", score: 82, flags: [] },
  },
  liquidity_check: {
    description: "Liquidity depth + top pair DEX for a Base token.",
    output: { address: "0x...", liquidity_usd: 500000, top_pair_dex: "aerodrome", verdict: "PROCEED" },
  },
  rug_pull_alert: {
    description: "Owner-power / rug-risk flags (mint, blacklist, pausable transfers, LP concentration).",
    output: { address: "0x...", rug_risk: "LOW", owner_powers: [], verdict: "PROCEED" },
  },
  dossier_check: {
    description: "VAPE's deepest instant verdict: weighted CertiK-style score, meme-factory-template "
      + "detection, recent-hack correlation, public web-reputation search, a live check of the "
      + "project's declared socials, and a frontier-LLM quick read of the verified source.",
    output: { address: "0x...", symbol: "TOKEN", name: "Token Name", score: 82, verdict: "PROCEED", reasons: [], positive_signals: [],
              verified: true, meme_factory_template: false, hack_correlation: [],
              web_reputation: { checked: true, flagged: false }, social_verification: { declared_count: 2 },
              ai_review: { available: true, provider: "gemini", summary: "..." } },
  },
  market_intel: {
    description: "Base TVL, top protocols, prices, and rule-based anomaly flags.",
    output: { base_tvl: 4100000000, top_protocols: ["Morpho", "Aerodrome"], anomaly_flags: [] },
  },
};

// A premium audit tier that genuinely can't complete inside a Worker's request
// window (real recon + Slither + a frontier-model source review takes minutes,
// not milliseconds), so this route pays, then dispatches a GitHub Actions job
// — either agents/deep_dive_audit.py via .github/workflows/deep-dive-bounty.yml
// (address-based, Solidity/EVM on-chain targets) or agents/external_audit.py via
// .github/workflows/external-bounty-audit.yml (owner/repo-based, e.g. Move/Sui
// or any external bounty-program repo) — and returns immediately with delivery
// info instead of a synchronous result, unlike every other route below. No
// fixed turnaround is promised: the deliverable is a submission-ready PoC with
// full technical detail (full recon, real Slither/Mythril/Aderyn/Halmos output
// when applicable, and a frontier LLM reading the actual verified source).
const BOUNTY_DEEP_DIVE_PRICE = "$1.00";
const BOUNTY_DEEP_DIVE_DISCOVERY = {
  description: "Submission-ready PoC and full technical detail: real recon + Slither + "
    + "frontier-model line-by-line source review, delivered as a real committed report — "
    + "VAPE's deepest automated pass. Supply a contract address, or a GitHub owner/repo "
    + "to have VAPE audit a specific bounty program directly.",
  output: {
    status: "accepted",
    address: "0x...",
    message: "Audit queued — report lands in intel/audits/poc-reports/ (or external-bounties/ "
      + "for a repo-based target) as soon as it completes.",
  },
};

const app = new Hono<{ Bindings: Env; Variables: Variables }>();

// c.executionCtx throws (not just returns undefined) when no ExecutionContext
// was supplied to app.fetch() — true on the Deno fallback (worker/deno/deno-entry.ts
// calls app.fetch(req, env) with no third argument). Falling back to awaiting
// inline there still logs correctly, just without the "don't block the
// response" benefit Cloudflare gets from waitUntil().
function safeWaitUntil(c: Context, promise: Promise<unknown>): void {
  const settled = promise.catch(() => {});
  try {
    c.executionCtx.waitUntil(settled);
  } catch {
    void settled;
  }
}

// Applies to every route, including /scan/*: the site calls this worker
// browser-side from GitHub Pages (a different origin), and the x402 payment
// retry sends a custom `X-PAYMENT` header, which makes browsers preflight
// with OPTIONS — without allowHeaders covering it, that preflight (and thus
// the whole payment flow) fails before any wallet-signing code ever runs.
// `@x402/fetch`'s client also sets `Access-Control-Expose-Headers` as a
// *request* header on the retry (unusual — that header is normally
// response-only — but it's what the library actually sends), so it has to
// be allow-listed too or the browser blocks that specific retry while the
// unauthenticated first request still succeeds, which is exactly the
// signed-then-fails symptom this fixes. exposeHeaders makes the protocol's
// custom response headers readable by client JS, which cross-origin
// responses hide by default unless explicitly exposed. X-VAPE-Client is
// docs/assets/hire.js's own tag (see the facilitator-routing middleware
// below) — same preflight requirement as X-PAYMENT.
app.use("*", cors({
  origin: "*",
  allowMethods: ["GET", "OPTIONS"],
  allowHeaders: ["Content-Type", "X-PAYMENT", "PAYMENT-SIGNATURE", "Access-Control-Expose-Headers", "X-VAPE-Client"],
  exposeHeaders: ["PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "X-PAYMENT-RESPONSE"],
}));

app.get("/", (c) =>
  c.json({
    agent: "VAPE",
    erc8004: 54988,
    protocol: "x402",
    offerings: [
      ...Object.entries(OFFERING_PRICES).map(([name, price]) => ({ name, price, route: `/scan/${name}` })),
      { name: "bounty_deep_dive", price: BOUNTY_DEEP_DIVE_PRICE, route: "/scan/bounty_deep_dive", sla: "async — no fixed SLA" },
      // Keyless market-data micro-services — real data, $0.01 each.
      ...DL_OFFERINGS.map((o) => ({ name: o.name, price: o.price, route: `/data/${o.name}` })),
    ],
    docs: "https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md",
  })
);

// Domain-ownership proof for 402index.io's listing-claim flow (see
// agents/x402_index_claim.py) — must serve ONLY this hash, as plain text,
// with no redirect, for POST /api/v1/claim/verify to succeed. This is the
// real verification_hash returned by the 2026-07-05 `claim` run (safe to
// publish by design — 402index.io never exposes the raw token this hash
// was derived from).
const WELLKNOWN_402INDEX_HASH = "610bdcdbe9d823eca680314fecea7fcceb4a009dcf4458117d5711cd3c207084";
app.get("/.well-known/402index-verify.txt", (c) =>
  WELLKNOWN_402INDEX_HASH
    ? c.text(WELLKNOWN_402INDEX_HASH)
    : c.notFound()
);

// Per-IP fixed-window rate limiter for the free (unpaid) endpoints below,
// backed by the same optional VAPE_JOBS KV already used for the job ledger.
// Degrades to "never blocks" when that binding isn't configured — same
// graceful-degradation pattern as every other optional resource in this file
// — so it's safe to attach even before VAPE_JOBS_KV_ID is set up. This closes
// a real gap: /prices and /cost-basis had neither caching nor any limit, so
// a scripted loop varying the address/addresses param on every call bypassed
// Cloudflare's URL-keyed Cache API entirely and burned metered Alchemy/
// CoinGecko compute units with nothing to stop it. Not a true sliding
// window and not meant to survive a distributed-IP attacker — just enough
// to stop a single scripted client from draining quota, which is the actual
// threat here (these routes hold no funds and gate no priced offering).
function rateLimiter(routeName: string, limit: number, windowSeconds: number) {
  return async (c: Context<{ Bindings: Env }>, next: () => Promise<void>) => {
    const kv = c.env.VAPE_JOBS;
    if (!kv) return next();
    const ip = c.req.header("cf-connecting-ip") || "unknown";
    const bucket = Math.floor(Date.now() / (windowSeconds * 1000));
    const key = `ratelimit:${routeName}:${ip}:${bucket}`;
    let current = 0;
    try {
      current = Number(await kv.get(key)) || 0;
    } catch {
      return next(); // KV hiccup — fail open, never block a legitimate caller over it
    }
    if (current >= limit) {
      c.header("Retry-After", String(windowSeconds));
      return c.json({ error: "rate limited, try again shortly" }, 429);
    }
    try {
      await kv.put(key, String(current + 1), { expirationTtl: windowSeconds * 2 });
    } catch {
      // Best-effort counting — a failed increment just means this window
      // undercounts, never a reason to block the current request.
    }
    return next();
  };
}

// Free, unpaid Alchemy-backed endpoints — no x402 gate, since these back the
// site's read-only wallet profile and metrics strip rather than a priced
// offering. 503 (not 500) when ALCHEMY_API_KEY isn't configured, so callers
// can fall back to their direct public-RPC path instead of erroring.
//
// Alchemy usage is metered (compute units), unlike the public-data providers
// elsewhere in this file — a real per-visitor cost, not just a shared public
// rate limit. None of this had any caching, so a page reload, multiple open
// tabs, or the site's own periodic polling each burned a fresh Alchemy call
// for data that's identical within a short window. Cloudflare's Cache API
// (via Hono's built-in `cache` middleware) absorbs repeat requests to the
// same URL — `/network-status` takes no query params at all, so this also
// means every visitor now shares ONE cached Alchemy call instead of one each.
// Only 200 responses are cached by default, so the 400/502/503 error paths
// below are never cached.
app.get("/portfolio", rateLimiter("portfolio", 20, 60), cache({ cacheName: "vape-portfolio", cacheControl: "max-age=20" }), async (c) => {
  const address = c.req.query("address") || "";
  if (!ADDRESS_RE.test(address)) return c.json({ error: "invalid address" }, 400);
  if (!c.env.ALCHEMY_API_KEY) return c.json({ error: "portfolio lookup not configured" }, 503);
  try {
    const portfolio = await getPortfolio(c.env, address);
    return c.json({ address, ...portfolio });
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

app.get("/nfts", rateLimiter("nfts", 20, 60), cache({ cacheName: "vape-nfts", cacheControl: "max-age=60" }), async (c) => {
  const address = c.req.query("address") || "";
  if (!ADDRESS_RE.test(address)) return c.json({ error: "invalid address" }, 400);
  if (!c.env.ALCHEMY_API_KEY) return c.json({ error: "nft lookup not configured" }, 503);
  try {
    const nfts = await getNftsForOwner(c.env, address);
    return c.json({ address, nfts });
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

app.get("/network-status", cache({ cacheName: "vape-network-status", cacheControl: "max-age=20" }), async (c) => {
  if (!c.env.ALCHEMY_API_KEY) return c.json({ error: "network status not configured" }, 503);
  try {
    const status = await getNetworkStatus(c.env);
    return c.json(status);
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

// CoinGecko current-price proxy — same data the site's client-side JS can
// already fetch directly and unauthenticated, but attaching COINGECKO_API_KEY
// server-side gets the Demo tier's higher/guaranteed rate limit instead of
// the fully anonymous tier's. 503s (not 500s) so callers fall back to their
// existing direct CoinGecko call, same pattern as the Alchemy routes above.
app.get("/prices", rateLimiter("prices", 20, 60), cache({ cacheName: "vape-prices", cacheControl: "max-age=20" }), async (c) => {
  const addresses = (c.req.query("addresses") || "").split(",").map((a) => a.trim().toLowerCase()).filter(Boolean);
  if (!addresses.length || !addresses.every((a) => ADDRESS_RE.test(a))) return c.json({ error: "invalid addresses" }, 400);
  try {
    const prices = await getCurrentPrices(c.env, addresses);
    return c.json(prices);
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

// Estimated cost-basis P&L — needs both ALCHEMY_API_KEY (to find each
// token's earliest incoming transfer) and COINGECKO_API_KEY (historical
// price by contract, which CoinGecko gates behind at least its free Demo
// key). See lib/costBasis.ts for exactly what this does and doesn't compute
// — it's a single-acquisition-point estimate, not full accounting.
app.get("/cost-basis", rateLimiter("cost-basis", 10, 60), cache({ cacheName: "vape-cost-basis", cacheControl: "max-age=30" }), async (c) => {
  const address = c.req.query("address") || "";
  if (!ADDRESS_RE.test(address)) return c.json({ error: "invalid address" }, 400);
  if (!c.env.ALCHEMY_API_KEY || !c.env.COINGECKO_API_KEY) return c.json({ error: "cost basis estimate not configured" }, 503);
  try {
    const portfolio = await getPortfolio(c.env, address);
    const priced = await getCurrentPrices(c.env, portfolio.tokens.map((t) => t.contractAddress.toLowerCase()));
    const tokensForEstimate = portfolio.tokens
      .map((t) => ({ contractAddress: t.contractAddress, symbol: t.symbol, currentBalance: t.balance, currentPriceUsd: priced[t.contractAddress.toLowerCase()]?.usd ?? 0 }))
      .filter((t) => t.currentBalance > 0 && t.currentPriceUsd > 0);
    const results = await estimateCostBasis(c.env, address, tokensForEstimate);
    return c.json({ address, results });
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

// VIRTUAL token's own price/volume/liquidity + holder concentration, all
// via Codex.io (see lib/codex.ts) — replaces an earlier CoinGecko+DefiLlama
// version of this panel. Free, unpaid, same rate-limit+cache pattern as
// /portfolio above; 503s if CODEX_API_KEY isn't configured.
const VIRTUAL_TOKEN_ADDRESS = "0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b";
app.get("/virtuals-snapshot", rateLimiter("virtuals-snapshot", 20, 60), cache({ cacheName: "vape-virtuals-snapshot", cacheControl: "max-age=30" }), async (c) => {
  if (!c.env.CODEX_API_KEY) return c.json({ error: "virtuals snapshot not configured" }, 503);
  try {
    const [detail, holders] = await Promise.all([
      codex.tokenDetail(c.env.CODEX_API_KEY, VIRTUAL_TOKEN_ADDRESS, codex.BASE_NETWORK_ID),
      codex.tokenHolders(c.env.CODEX_API_KEY, VIRTUAL_TOKEN_ADDRESS, codex.BASE_NETWORK_ID, 10),
    ]);
    return c.json({ ts: new Date().toISOString(), address: VIRTUAL_TOKEN_ADDRESS, detail, holders });
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

// Trending Base tokens ranked by Codex's own volume/liquidity signal, each
// best-effort tagged `isVirtuals` (see lib/codex.ts::isVirtualsToken) —
// "trending on Base, tagged if Virtuals-launched", not a fabricated
// "Virtuals-only" feed dressed up as one.
app.get("/trending-base", rateLimiter("trending-base", 20, 60), cache({ cacheName: "vape-trending-base", cacheControl: "max-age=60" }), async (c) => {
  if (!c.env.CODEX_API_KEY) return c.json({ error: "trending tokens not configured" }, 503);
  try {
    const limit = Math.min(Number(c.req.query("limit")) || 20, 50);
    const trending = await codex.trendingTokens(c.env.CODEX_API_KEY, [codex.BASE_NETWORK_ID], limit);
    if (trending.error) return c.json(trending, 502);
    const tokens = (trending.tokens as codex.TrendingTokenRow[]) || [];
    const tagged = await Promise.all(tokens.map(async (t) => ({
      ...t,
      isVirtuals: t.token?.address ? await codex.isVirtualsToken(t.token.address) : false,
    })));
    return c.json({ ts: trending.ts, tokens: tagged });
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

// Crypto/Base-relevant prediction-market odds from Polymarket + Kalshi — both
// free and keyless, unlike the Codex-backed routes above, so this needs no
// env/secret check at all. Same free-display + paid-x402-tool dual pattern
// as everything else here: this route is the free site-panel counterpart to
// the /data/prediction_market_odds offering (worker/src/dataHandlers.ts).
app.get("/prediction-markets", rateLimiter("prediction-markets", 20, 60), cache({ cacheName: "vape-prediction-markets", cacheControl: "max-age=120" }), async (c) => {
  try {
    const limit = Math.min(Number(c.req.query("limit")) || 20, 50);
    const result = await predictionMarkets.cryptoPredictionMarkets(limit);
    return c.json(result);
  } catch (e) {
    return c.json({ error: "upstream lookup failed", detail: errDetail(e, c.env) }, 502);
  }
});

// Live x402 job ledger — free, unpaid (this is the showcase, not a priced
// offering). Backed by lib/jobLog.ts's KV-backed record; 503s exactly like
// /portfolio above when VAPE_JOBS isn't wired yet (see worker/README.md).
app.get("/x402/feed", cache({ cacheName: "vape-x402-feed", cacheControl: "max-age=10" }), async (c) => {
  if (!c.env.VAPE_JOBS) return c.json({ error: "job feed not configured" }, 503);
  const limit = Math.min(Number(c.req.query("limit")) || 50, 200);
  const jobs = await getFeed(c.env.VAPE_JOBS, limit);
  return c.json({ jobs });
});

app.get("/x402/stats", cache({ cacheName: "vape-x402-stats", cacheControl: "max-age=30" }), async (c) => {
  if (!c.env.VAPE_JOBS) return c.json({ error: "job feed not configured" }, 503);
  // 400-day cap matches jobLog.ts's DAILY_HISTORY_CAP — safe now that
  // getStats() reads one history record instead of one KV key per day.
  const days = Math.min(Number(c.req.query("days")) || 30, 400);
  const stats = await getStats(c.env.VAPE_JOBS, days);
  return c.json(stats);
});

// Real, read-side self-check for CDP's Bazaar discovery catalog. CDP's
// facilitator never emits the documented EXTENSION-RESPONSES header that's
// supposed to confirm a listing was accepted/rejected (confirmed via
// network-level packet capture in x402-foundation/x402#2112, still open),
// so declaring the bazaar extension correctly gives zero visibility into
// whether it actually got indexed. This queries CDP's own discovery
// catalog directly and diffs it against our real offering list — filtered
// by our own payTo (shared across every VAPE offering), so it never needs
// to paginate CDP's full ~20k-item catalog. Public and free: the result
// only reveals whether our ALREADY-public offerings are indexed, nothing
// sensitive, and it's rate-limited/cached like the other free routes.
app.get("/admin/bazaar-status", rateLimiter("bazaar-status", 6, 300), cache({ cacheName: "vape-bazaar-status", cacheControl: "max-age=300" }), async (c) => {
  if (!c.env.CDP_API_KEY_ID || !c.env.CDP_API_KEY_SECRET) {
    return c.json({ error: "CDP credentials not configured" }, 503);
  }
  const base = c.env.X402_FACILITATOR_URL;
  const host = new URL(base).host;
  const path = `${new URL(base).pathname}/discovery/resources`;

  let jwt: string;
  try {
    jwt = await generateCdpJwt({
      apiKeyId: c.env.CDP_API_KEY_ID,
      apiKeySecret: c.env.CDP_API_KEY_SECRET,
      requestMethod: "GET",
      requestHost: host,
      requestPath: path,
    });
  } catch (e) {
    return c.json({ error: `failed to build CDP auth: ${errDetail(e, c.env)}`, cdp_reachable: false }, 502);
  }

  let body: { items?: { resource?: string }[] };
  try {
    const r = await fetch(`${base}/discovery/resources?payTo=${c.env.PAY_TO_ADDRESS}&limit=200`, {
      headers: { Authorization: `Bearer ${jwt}`, Accept: "application/json" },
    });
    if (!r.ok) {
      return c.json({ error: `CDP discovery HTTP ${r.status}`, cdp_reachable: r.status < 500 }, 502);
    }
    body = await r.json();
  } catch (e) {
    return c.json({ error: `CDP discovery fetch failed: ${errDetail(e, c.env)}`, cdp_reachable: false }, 502);
  }

  const indexedUrls = new Set((body.items ?? []).map((it) => it.resource).filter(Boolean));
  const origin = new URL(c.req.url).origin;
  const allOfferings = [
    ...Object.keys(OFFERING_PRICES).map((name) => `${origin}/scan/${name}`),
    `${origin}/scan/bounty_deep_dive`,
    ...DL_OFFERINGS.map((o) => `${origin}/data/${o.name}`),
  ];
  const indexed = allOfferings.filter((u) => indexedUrls.has(u));
  const missing = allOfferings.filter((u) => !indexedUrls.has(u));

  return c.json({
    checked_at: new Date().toISOString(),
    cdp_reachable: true,
    total_offerings: allOfferings.length,
    indexed_count: indexed.length,
    indexed,
    missing,
  });
});

app.use("*", async (c, next) => {
  // withBazaar() extends the facilitator client so its getSupported()/
  // settle responses carry the EXTENSION-RESPONSES metadata the Bazaar
  // discovery index reads — without this wrapper, registerExtension() below
  // declares the route metadata but the facilitator has no signal to
  // actually catalog it. Bazaar discovery stays tied to CDP specifically
  // (withBazaar's .extensions.bazaar reads the wrapped client's own .url/
  // createAuthHeaders internally) — that's fine, discovery listing isn't on
  // the real-money verify/settle path the fallback below actually protects.
  const cdpClient = withBazaar(new HTTPFacilitatorClient({
    url: c.env.X402_FACILITATOR_URL,
    createAuthHeaders: buildCreateAuthHeaders(c.env),
  }));

  // Hybrid facilitator routing: real production traffic is deliberately
  // split ~50/50 between VAPOR (our own facilitator) and CDP's hosted one,
  // per request — not "prefer one, only touch the other on any failure".
  // VAPOR needs genuine, ongoing settlement volume to prove itself as a
  // real facilitator (not just a cold failover path); CDP stays
  // continuously exercised too, not relegated to an outage-only role.
  // Each request still falls back to the other facilitator if its
  // randomly-chosen primary throws — resilience isn't traded away for the
  // split (see lib/facilitatorClient.ts for why blind retry-on-fallback is
  // safe here even for settle). DATA AGENT's own hires (agents/data_agent.py)
  // go through these exact same routes, so they get the same 50/50 split
  // as any external buyer — there's no separate code path for them.
  //
  // One deliberate carve-out: a real human paying in-browser via the site's
  // own wallet-connect flow (docs/assets/hire.js) tags its request with
  // X-VAPE-Client: site. Basescan only recognizes/labels CDP's facilitator
  // addresses as "x402 payment" (its own manually-curated Name Tags, not
  // anything derived from the on-chain data) — VAPOR's settlement wallet has
  // no such label. A person paying through the site is the one traffic class
  // most likely to go check Basescan afterward and expect to see it
  // classified correctly, so that traffic always gets CDP as primary (VAPOR
  // still stands in as fallback if CDP itself throws — this narrows WHERE
  // the split applies, it doesn't remove the resilience).
  //
  // A second carve-out: DATA AGENT runs as two independent, explicitly-
  // pinned instances (agents/data_agent.py tags X-VAPE-Client: data-agent
  // for CDP, agents/data_agent_vapor.py tags data-agent-vapor for VAPOR)
  // rather than one instance alternating between the two. An earlier
  // version tried a persisted KV toggle (see git history on
  // lib/dataAgentAlternator.ts, now removed) meant to flip 50/50 from a
  // single agent — it turned out to be the wrong tool for proving VAPOR
  // out reliably: debugging it required adding temporary debug fields to
  // real job records to see what was actually happening call-to-call, and
  // by the time that was in place, two thin always-CDP / always-VAPOR
  // agents were simply less to get wrong than one agent coordinating state
  // through a shared, rarely-written toggle. Any other automated/agent
  // traffic keeps the random 50/50 split, since Basescan's label doesn't
  // matter to a script.
  const isSiteTraffic = c.req.header("X-VAPE-Client") === "site";
  const isDataAgentCdp = c.req.header("X-VAPE-Client") === "data-agent";
  const isDataAgentVapor = c.req.header("X-VAPE-Client") === "data-agent-vapor";
  const vaporClient = c.env.VAPOR_FACILITATOR_URL
    ? new HTTPFacilitatorClient({ url: c.env.VAPOR_FACILITATOR_URL })
    : null;
  let usesVaporPrimary = false;
  if (vaporClient !== null && !isSiteTraffic && !isDataAgentCdp) {
    usesVaporPrimary = isDataAgentVapor ? true : Math.random() < 0.5;
  }
  const hybridClient = vaporClient
    ? new FallbackFacilitatorClient(usesVaporPrimary ? vaporClient : cdpClient, usesVaporPrimary ? cdpClient : vaporClient)
    : null;
  const facilitatorClient = hybridClient
    ? Object.assign(hybridClient, { extensions: cdpClient.extensions })
    : cdpClient;
  // What ACTUALLY settled this request's payment, accounting for a
  // fallback having occurred — not just which one was picked as primary.
  // Read from lib/facilitatorClient.ts's lastUsed after the real
  // verify/settle calls happen below (onAfterSettle), never assumed here.
  const facilitatorUsed = (): "vapor" | "cdp" => {
    if (!hybridClient) return "cdp";
    const primaryWasVapor = usesVaporPrimary;
    return hybridClient.lastUsed === "primary"
      ? (primaryWasVapor ? "vapor" : "cdp")
      : (primaryWasVapor ? "cdp" : "vapor");
  };
  const resourceServer = new x402ResourceServer(facilitatorClient)
    .register(c.env.X402_NETWORK, new ExactEvmScheme())
    .registerExtension(bazaarResourceServerExtension)
    // Fires once the facilitator confirms settlement — AFTER the
    // /scan/:offering handler below has already run and stashed its result
    // via c.set("vapeJobDraft", ...). This is the ONLY place the real
    // on-chain tx hash + payer address are available, so the actual
    // jobLog.logJob() call happens here, merging the handler's draft with
    // the real settlement facts. See lib/jobLog.ts for why this is layered
    // with Basescan rather than trusted as VAPE's word alone.
    //
    // Previously this stashed settlement facts for the handler to read —
    // backwards, since @x402/hono settles strictly after next() resolves,
    // so the handler's c.get() always saw undefined and every logged job
    // showed a permanently null tx_hash ("unsettled" on the site) even
    // though the payment had genuinely settled moments later.
    .onAfterSettle(async (ctx) => {
      const draft = c.get("vapeJobDraft");
      if (!draft) return; // e.g. bounty_deep_dive, which doesn't log a job record
      const record: JobRecord = {
        ...draft,
        payer: ctx.result.payer ?? null,
        tx_hash: ctx.result.transaction ?? null,
        network: ctx.result.network ?? null,
        facilitator: facilitatorUsed(),
      };
      safeWaitUntil(c, logJob(c.env.VAPE_JOBS, record));
    });

  const routes: Record<string, unknown> = {};
  for (const [name, price] of Object.entries(OFFERING_PRICES)) {
    const meta = OFFERING_DISCOVERY[name as HandlerName];
    routes[`GET /scan/${name}`] = {
      accepts: { scheme: "exact", price, network: c.env.X402_NETWORK, payTo: c.env.PAY_TO_ADDRESS },
      description: `VAPE ${name} — ${meta.description} Real GoPlus/DexScreener data, no simulation.`,
      serviceName: "VAPE",
      iconUrl: ICON_URL,
      tags: ["security", "on-chain-forensics", "base"],
      extensions: declareDiscoveryExtension({
        input: { address: "0x0000000000000000000000000000000000dEaD" },
        inputSchema: {
          properties: {
            address: { type: "string", description: "Base (chain 8453) contract/token address to analyze" },
            chain: { type: "string", description: "optional chain id override, defaults to 8453" },
          },
          required: ["address"],
        },
        output: { example: meta.output },
      }),
    };
  }

  // bounty_deep_dive: same x402 gate, but its own price/metadata since it isn't part
  // of the synchronous OFFERING_PRICES/HandlerName set (see the handler below).
  routes["GET /scan/bounty_deep_dive"] = {
    accepts: { scheme: "exact", price: BOUNTY_DEEP_DIVE_PRICE, network: c.env.X402_NETWORK, payTo: c.env.PAY_TO_ADDRESS },
    description: `VAPE bounty_deep_dive — ${BOUNTY_DEEP_DIVE_DISCOVERY.description}`,
    serviceName: "VAPE",
    iconUrl: ICON_URL,
    tags: ["security", "on-chain-forensics", "base", "premium"],
    extensions: declareDiscoveryExtension({
      input: { address: "0x0000000000000000000000000000000000dEaD" },
      inputSchema: {
        properties: {
          address: { type: "string", description: "Base (chain 8453) contract/token address to audit" },
          chain: { type: "string", description: "optional chain id override, defaults to 8453" },
          callback_url: { type: "string", description: "optional webhook to POST the completed report to" },
        },
        required: ["address"],
      },
      output: { example: BOUNTY_DEEP_DIVE_DISCOVERY.output },
    }),
  };

  // Market-data micro-services — one $0.01 paid route per tool, same x402
  // gate and Bazaar discovery metadata as the security offerings above. Real
  // hosted token/protocol logos and rich data (see dataHandlers.ts).
  for (const o of DL_OFFERINGS) {
    routes[`GET /data/${o.name}`] = {
      accepts: { scheme: "exact", price: o.price, network: c.env.X402_NETWORK, payTo: c.env.PAY_TO_ADDRESS },
      description: `VAPE ${o.name} — ${o.description}`,
      serviceName: "VAPE",
      iconUrl: ICON_URL,
      tags: o.tags,
      extensions: declareDiscoveryExtension({
        input: o.inputExample,
        inputSchema: o.inputSchema,
        output: { example: o.output },
      }),
    };
  }

  return await paymentMiddleware(routes as any, resourceServer)(c, next);
});

for (const name of Object.keys(OFFERING_PRICES) as HandlerName[]) {
  app.get(`/scan/${name}`, async (c) => {
    const address = c.req.query("address") || "";
    const chain = c.req.query("chain");
    const chainId = chain ? Number(chain) : 8453;
    const req = { address, ...(chain ? { chain_id: chainId } : {}) };
    const t0 = Date.now();
    const result = await fulfill(name, req, c.env);
    const d = (result as { deliverable?: Record<string, unknown> }).deliverable ?? {};
    // Settlement facts (payer/tx_hash/network) aren't known yet at this point —
    // @x402/hono settles after this handler returns. Stash everything this
    // handler DOES know; the onAfterSettle hook above merges in the rest and
    // does the actual logJob() call once settlement completes.
    c.set("vapeJobDraft", {
      id: `${new Date().toISOString()}-${Math.random().toString(36).slice(2, 8)}`,
      ts: new Date().toISOString(),
      offering: name,
      address,
      chain_id: chainId,
      symbol: (d.symbol as string) ?? null,
      name: (d.name as string) ?? (d.contract_name as string) ?? null,
      verdict: (d.verdict as string) ?? (d.rug_risk as string) ?? null,
      status: result.status === "error" ? "error" : "settled",
      amount_usd: Number(OFFERING_PRICES[name].replace("$", "")),
      latency_ms: Date.now() - t0,
      error: result.status === "error" ? String((result as { error?: unknown }).error ?? "unknown error") : null,
    });
    return c.json(result);
  });
}

// Market-data micro-services — the paid handlers behind the /data/* routes
// registered in the middleware above. Same job-draft/onAfterSettle logging as
// /scan/* so these show up in the live x402 feed too. address is optional here
// (many of these tools are chain- or protocol-scoped, not token-scoped).
for (const o of DL_OFFERINGS) {
  app.get(`/data/${o.name}`, async (c) => {
    const q: DlQuery = {
      address: c.req.query("address") || undefined,
      chain: c.req.query("chain") || undefined,
      slug: c.req.query("slug") || undefined,
      project: c.req.query("project") || undefined,
      symbol: c.req.query("symbol") || undefined,
      span: c.req.query("span") ? Number(c.req.query("span")) : undefined,
      limit: c.req.query("limit") ? Number(c.req.query("limit")) : undefined,
    };
    const t0 = Date.now();
    const result = await fulfillData(o.name, q, c.env);
    const d = (result as { deliverable?: Record<string, unknown> }).deliverable ?? {};
    c.set("vapeJobDraft", {
      id: `${new Date().toISOString()}-${Math.random().toString(36).slice(2, 8)}`,
      ts: new Date().toISOString(),
      offering: o.name,
      address: q.address ?? null,
      chain_id: 8453,
      symbol: (d.symbol as string) ?? null,
      name: (d.name as string) ?? null,
      verdict: null,
      status: result.status === "error" ? "error" : "settled",
      amount_usd: Number(o.price.replace("$", "")),
      latency_ms: Date.now() - t0,
      error: result.status === "error" ? String((result as { error?: unknown }).error ?? "unknown error") : null,
    });
    return c.json(result);
  });
}

// A GitHub owner/repo is [A-Za-z0-9_.-]+ per GitHub's own naming rules — this
// is the gate before either value is threaded into a workflow_dispatch input.
const GH_SLUG_RE = /^[A-Za-z0-9_.-]+$/;

// bounty_deep_dive: gated by the same x402 middleware above — payment
// verification has already happened by the time this handler runs, but
// actual settlement still happens after (see the onAfterSettle hook above),
// and is cancelled automatically if this handler responds >= 400. This just
// kicks off the real async job and returns immediately — the actual audit
// runs in GitHub Actions, not here, so neither path logs an x402 job record
// (see lib/jobLog.ts) or appears in the live feed.
//
// Two fulfillment paths, chosen by which inputs the buyer supplies (the site's
// hire-from-Bounty-Ops flow picks the right one per program automatically,
// see docs/assets/hire.js::openBountyOps()):
//   - address (+ chain): on-chain Solidity/EVM target -> deep-dive-bounty.yml
//     -> agents/deep_dive_audit.py.
//   - owner + repo (+ ref/program_name/paths): a bounty program's own source
//     repo (Move/Sui or any other language) -> external-bounty-audit.yml ->
//     agents/external_audit.py.
app.get("/scan/bounty_deep_dive", async (c) => {
  const address = c.req.query("address") || "";
  const chain = c.req.query("chain") || "8453";
  const owner = c.req.query("owner") || "";
  const repo = c.req.query("repo") || "";
  const ref = c.req.query("ref") || undefined;
  const programName = c.req.query("program_name") || undefined;
  const paths = c.req.query("paths") || undefined;
  const callbackUrl = c.req.query("callback_url") || undefined;

  const hasAddress = ADDRESS_RE.test(address);
  const hasRepo = owner && repo && GH_SLUG_RE.test(owner) && GH_SLUG_RE.test(repo);

  if (!hasAddress && !hasRepo) {
    return c.json({
      offering: "bounty_deep_dive", status: "error",
      error: "provide either a contract address or a GitHub owner/repo",
    }, 400);
  }
  if (!c.env.GH_DISPATCH_TOKEN) {
    // Payment already settled — this is a real config gap, not a client error, so 503
    // (not 400/402) tells the buyer to retry rather than re-check their request.
    return c.json({
      offering: "bounty_deep_dive", status: "error",
      error: "audit dispatch not configured (GH_DISPATCH_TOKEN unset) — contact VAPE via ACP instead",
    }, 503);
  }

  if (hasAddress) {
    const dispatch = await dispatchDeepDiveAudit(c.env.GH_DISPATCH_TOKEN, address, chain, callbackUrl);
    if (!dispatch.ok) {
      return c.json({
        offering: "bounty_deep_dive", status: "error",
        error: `job dispatch failed (HTTP ${dispatch.status})`, detail: dispatch.body.slice(0, 300),
      }, 502);
    }
    return c.json({
      offering: "bounty_deep_dive", status: "accepted", address, chain,
      message: "Audit queued — a submission-ready PoC report lands in intel/audits/poc-reports/ "
        + "as soon as it completes."
        + (callbackUrl ? " Will also POST the result to your callback_url." : ""),
      track: "https://github.com/jUXTAPOSITION1/V.A.P.E/tree/main/intel/audits/poc-reports",
      source: "vape-real-data", disclaimer: "Real on-chain data. Not investment advice.",
    });
  }

  const dispatch = await dispatchExternalBountyAudit(c.env.GH_DISPATCH_TOKEN, {
    owner, repo, ref, programName, paths, callbackUrl,
  });
  if (!dispatch.ok) {
    return c.json({
      offering: "bounty_deep_dive", status: "error",
      error: `job dispatch failed (HTTP ${dispatch.status})`, detail: dispatch.body.slice(0, 300),
    }, 502);
  }
  return c.json({
    offering: "bounty_deep_dive", status: "accepted", owner, repo, ref: ref || "main",
    message: "Audit queued — a submission-ready PoC report lands in "
      + "intel/audits/external-bounties/ as soon as it completes."
      + (callbackUrl ? " Will also POST the result to your callback_url." : ""),
    track: "https://github.com/jUXTAPOSITION1/V.A.P.E/tree/main/intel/audits/external-bounties",
    source: "vape-real-data", disclaimer: "Real on-chain data. Not investment advice.",
  });
});

export default app;
