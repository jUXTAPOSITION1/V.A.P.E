/**
 * VAPE x402 payment worker — pay-per-call access to the 6 "auto" ACP
 * offerings (see docs/ACP_PROTOCOL.md / data/reputation.json for the full
 * 14-offering catalog; the other 8 need the SKILLFORGE tool tier and are
 * hired via a real ACP job instead). Also hosts a few free, unpaid Alchemy-
 * backed reliability endpoints (/portfolio, /nfts, /network-status) that the
 * site's wallet profile and metrics strip prefer over direct public-RPC
 * calls when this worker is deployed and configured.
 *
 * Runs on Deno Deploy, against Base mainnet + Coinbase Developer Platform's
 * hosted x402 facilitator (real funds) — see worker/README.md for the
 * network/facilitator config and required environment variables.
 */
import { Hono } from "hono";
import { cors } from "hono/cors";
import { cache } from "hono/cache";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { declareDiscoveryExtension, bazaarResourceServerExtension, withBazaar } from "@x402/extensions/bazaar";
import { fulfill, type HandlerName } from "./handlers";
import { generateCdpJwt } from "./lib/cdpAuth";
import { getPortfolio, getNftsForOwner, getNetworkStatus } from "./lib/alchemy";
import { getCurrentPrices } from "./lib/coingecko";
import { estimateCostBasis } from "./lib/costBasis";
import { dispatchDeepDiveAudit } from "./lib/githubDispatch";

// CAIP-2 chain identifier, e.g. "eip155:8453" (Base) or "eip155:84532" (Base Sepolia).
type Caip2Network = `${string}:${string}`;

export interface Env {
  ETHERSCAN_API_KEY?: string;
  CDP_API_KEY_ID?: string;
  CDP_API_KEY_SECRET?: string;
  ALCHEMY_API_KEY?: string;
  COINGECKO_API_KEY?: string;
  // Fine-grained PAT (Actions: write, Contents: read) for triggering the
  // bounty_deep_dive offering's async job — see worker/src/lib/githubDispatch.ts.
  GH_DISPATCH_TOKEN?: string;
  PAY_TO_ADDRESS: string;
  X402_NETWORK: Caip2Network;
  X402_FACILITATOR_URL: string;
}

const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;

/**
 * Builds the facilitator's `createAuthHeaders` callback. Only CDP's hosted
 * facilitator (api.cdp.coinbase.com) needs Bearer JWT auth; the public
 * testnet facilitator (facilitator.x402.org) needs none, so this is a no-op
 * unless both CDP secrets are configured as Deno Deploy environment variables.
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
  safety_preflight: "$0.05",
  market_intel: "$0.15",
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
  safety_preflight: {
    description: "Combined token safety + contract verification preflight verdict.",
    output: { address: "0x...", token_verdict: "PROCEED", verified: true, combined: "PROCEED" },
  },
  market_intel: {
    description: "Base TVL, top protocols, prices, and rule-based anomaly flags.",
    output: { base_tvl: 4100000000, top_protocols: ["Morpho", "Aerodrome"], anomaly_flags: [] },
  },
};

// The 24h-SLA premium tier — genuinely can't complete inside a Worker's request
// window (real recon + Slither + a frontier-model source review takes minutes,
// not milliseconds), so this route pays, then dispatches a GitHub Actions job
// (agents/deep_dive_audit.py via .github/workflows/deep-dive-bounty.yml) and
// returns immediately with delivery info instead of a synchronous result —
// unlike every other route below. Priced far above the rest of the catalog to
// match the real analysis depth: full recon, real Slither output when
// available, and a frontier LLM (Gemini 2.5 Pro, Groq fallback) reading the
// actual verified source.
const BOUNTY_DEEP_DIVE_PRICE = "$50.00";
const BOUNTY_DEEP_DIVE_DISCOVERY = {
  description: "24h-SLA premium audit: full recon + Slither + frontier-model line-by-line "
    + "source review, delivered as a real committed report — VAPE's deepest automated pass.",
  output: {
    status: "accepted",
    address: "0x...",
    message: "Deep-dive audit queued — report lands in intel/audits/poc-reports/ within 24h.",
  },
};

const app = new Hono<{ Bindings: Env }>();

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
// responses hide by default unless explicitly exposed.
app.use("*", cors({
  origin: "*",
  allowMethods: ["GET", "OPTIONS"],
  allowHeaders: ["Content-Type", "X-PAYMENT", "PAYMENT-SIGNATURE", "Access-Control-Expose-Headers"],
  exposeHeaders: ["PAYMENT-REQUIRED", "PAYMENT-RESPONSE", "X-PAYMENT-RESPONSE"],
}));

app.get("/", (c) =>
  c.json({
    agent: "VAPE",
    erc8004: 54988,
    protocol: "x402",
    offerings: [
      ...Object.entries(OFFERING_PRICES).map(([name, price]) => ({ name, price, route: `/scan/${name}` })),
      { name: "bounty_deep_dive", price: BOUNTY_DEEP_DIVE_PRICE, route: "/scan/bounty_deep_dive", sla: "24h (async)" },
    ],
    docs: "https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md",
  })
);

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
app.get("/portfolio", cache({ cacheName: "vape-portfolio", cacheControl: "max-age=20" }), async (c) => {
  const address = c.req.query("address") || "";
  if (!ADDRESS_RE.test(address)) return c.json({ error: "invalid address" }, 400);
  if (!c.env.ALCHEMY_API_KEY) return c.json({ error: "portfolio lookup not configured" }, 503);
  try {
    const portfolio = await getPortfolio(c.env, address);
    return c.json({ address, ...portfolio });
  } catch (e) {
    return c.json({ error: "upstream lookup failed" }, 502);
  }
});

app.get("/nfts", cache({ cacheName: "vape-nfts", cacheControl: "max-age=60" }), async (c) => {
  const address = c.req.query("address") || "";
  if (!ADDRESS_RE.test(address)) return c.json({ error: "invalid address" }, 400);
  if (!c.env.ALCHEMY_API_KEY) return c.json({ error: "nft lookup not configured" }, 503);
  try {
    const nfts = await getNftsForOwner(c.env, address);
    return c.json({ address, nfts });
  } catch (e) {
    return c.json({ error: "upstream lookup failed" }, 502);
  }
});

app.get("/network-status", cache({ cacheName: "vape-network-status", cacheControl: "max-age=20" }), async (c) => {
  if (!c.env.ALCHEMY_API_KEY) return c.json({ error: "network status not configured" }, 503);
  try {
    const status = await getNetworkStatus(c.env);
    return c.json(status);
  } catch (e) {
    return c.json({ error: "upstream lookup failed" }, 502);
  }
});

// CoinGecko current-price proxy — same data the site's client-side JS can
// already fetch directly and unauthenticated, but attaching COINGECKO_API_KEY
// server-side gets the Demo tier's higher/guaranteed rate limit instead of
// the fully anonymous tier's. 503s (not 500s) so callers fall back to their
// existing direct CoinGecko call, same pattern as the Alchemy routes above.
app.get("/prices", async (c) => {
  const addresses = (c.req.query("addresses") || "").split(",").map((a) => a.trim().toLowerCase()).filter(Boolean);
  if (!addresses.length || !addresses.every((a) => ADDRESS_RE.test(a))) return c.json({ error: "invalid addresses" }, 400);
  try {
    const prices = await getCurrentPrices(c.env, addresses);
    return c.json(prices);
  } catch (e) {
    return c.json({ error: "upstream lookup failed" }, 502);
  }
});

// Estimated cost-basis P&L — needs both ALCHEMY_API_KEY (to find each
// token's earliest incoming transfer) and COINGECKO_API_KEY (historical
// price by contract, which CoinGecko gates behind at least its free Demo
// key). See lib/costBasis.ts for exactly what this does and doesn't compute
// — it's a single-acquisition-point estimate, not full accounting.
app.get("/cost-basis", async (c) => {
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
    return c.json({ error: "upstream lookup failed" }, 502);
  }
});

app.use("*", async (c, next) => {
  // withBazaar() extends the facilitator client so its getSupported()/
  // settle responses carry the EXTENSION-RESPONSES metadata the Bazaar
  // discovery index reads — without this wrapper, registerExtension() below
  // declares the route metadata but the facilitator has no signal to
  // actually catalog it.
  const facilitatorClient = withBazaar(new HTTPFacilitatorClient({
    url: c.env.X402_FACILITATOR_URL,
    createAuthHeaders: buildCreateAuthHeaders(c.env),
  }));
  const resourceServer = new x402ResourceServer(facilitatorClient)
    .register(c.env.X402_NETWORK, new ExactEvmScheme())
    .registerExtension(bazaarResourceServerExtension);

  const routes: Record<string, unknown> = {};
  for (const [name, price] of Object.entries(OFFERING_PRICES)) {
    const meta = OFFERING_DISCOVERY[name as HandlerName];
    routes[`GET /scan/${name}`] = {
      accepts: { scheme: "exact", price, network: c.env.X402_NETWORK, payTo: c.env.PAY_TO_ADDRESS },
      description: `VAPE ${name} — ${meta.description} Real GoPlus/DexScreener/DefiLlama data, no simulation.`,
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

  return paymentMiddleware(routes as any, resourceServer)(c, next);
});

for (const name of Object.keys(OFFERING_PRICES) as HandlerName[]) {
  app.get(`/scan/${name}`, async (c) => {
    const address = c.req.query("address") || "";
    const chain = c.req.query("chain");
    const req = { address, ...(chain ? { chain_id: Number(chain) } : {}) };
    const result = await fulfill(name, req, c.env);
    return c.json(result);
  });
}

// bounty_deep_dive: payment has already settled by the time this handler runs (the
// x402 middleware above gates it) — this just kicks off the real async job and
// returns immediately. The actual audit runs in GitHub Actions
// (.github/workflows/deep-dive-bounty.yml -> agents/deep_dive_audit.py), not here.
app.get("/scan/bounty_deep_dive", async (c) => {
  const address = c.req.query("address") || "";
  const chain = c.req.query("chain") || "8453";
  const callbackUrl = c.req.query("callback_url") || undefined;

  if (!ADDRESS_RE.test(address)) {
    return c.json({ offering: "bounty_deep_dive", status: "error", error: "invalid or missing address" }, 400);
  }
  if (!c.env.GH_DISPATCH_TOKEN) {
    // Payment already settled — this is a real config gap, not a client error, so 503
    // (not 400/402) tells the buyer to retry rather than re-check their request.
    return c.json({
      offering: "bounty_deep_dive", status: "error",
      error: "deep-dive dispatch not configured (GH_DISPATCH_TOKEN unset) — contact VAPE via ACP instead",
    }, 503);
  }

  const dispatch = await dispatchDeepDiveAudit(c.env.GH_DISPATCH_TOKEN, address, chain, callbackUrl);
  if (!dispatch.ok) {
    return c.json({
      offering: "bounty_deep_dive", status: "error",
      error: `job dispatch failed (HTTP ${dispatch.status})`, detail: dispatch.body.slice(0, 300),
    }, 502);
  }

  return c.json({
    offering: "bounty_deep_dive", status: "accepted", address, chain,
    message: "Deep-dive audit queued — report lands in intel/audits/poc-reports/ within 24h."
      + (callbackUrl ? " Will also POST the result to your callback_url." : ""),
    track: "https://github.com/jUXTAPOSITION1/V.A.P.E/tree/main/intel/audits/poc-reports",
    source: "vape-real-data", disclaimer: "Real on-chain data. Not investment advice.",
  });
});

export default app;
