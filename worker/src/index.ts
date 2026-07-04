/**
 * VAPE x402 payment worker — pay-per-call access to the 6 "auto" ACP
 * offerings (see docs/ACP_PROTOCOL.md / data/reputation.json for the full
 * 14-offering catalog; the other 8 need the SKILLFORGE tool tier and are
 * hired via a real ACP job instead).
 *
 * Ships pointed at Base Sepolia + the public x402.org testnet facilitator
 * (no account needed) so the full 402 -> sign -> resubmit -> settle loop can
 * be proven with no real funds at risk. Switching to Base mainnet is a
 * wrangler.toml var change (X402_NETWORK, X402_FACILITATOR_URL) once you
 * have Coinbase Developer Platform credentials — see wrangler.toml.
 */
import { Hono } from "hono";
import { paymentMiddleware, x402ResourceServer } from "@x402/hono";
import { ExactEvmScheme } from "@x402/evm/exact/server";
import { HTTPFacilitatorClient } from "@x402/core/server";
import { fulfill, type HandlerName } from "./handlers";
import { generateCdpJwt } from "./lib/cdpAuth";

// CAIP-2 chain identifier, e.g. "eip155:8453" (Base) or "eip155:84532" (Base Sepolia).
type Caip2Network = `${string}:${string}`;

export interface Env {
  ETHERSCAN_API_KEY?: string;
  CDP_API_KEY_ID?: string;
  CDP_API_KEY_SECRET?: string;
  PAY_TO_ADDRESS: string;
  X402_NETWORK: Caip2Network;
  X402_FACILITATOR_URL: string;
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
  safety_preflight: "$0.05",
  market_intel: "$0.15",
};

const app = new Hono<{ Bindings: Env }>();

app.get("/", (c) =>
  c.json({
    agent: "VAPE",
    erc8004: 54988,
    protocol: "x402",
    offerings: Object.entries(OFFERING_PRICES).map(([name, price]) => ({ name, price, route: `/scan/${name}` })),
    docs: "https://github.com/jUXTAPOSITION1/V.A.P.E/blob/main/docs/ACP_PROTOCOL.md",
  })
);

app.use("*", async (c, next) => {
  const facilitatorClient = new HTTPFacilitatorClient({
    url: c.env.X402_FACILITATOR_URL,
    createAuthHeaders: buildCreateAuthHeaders(c.env),
  });
  const resourceServer = new x402ResourceServer(facilitatorClient).register(c.env.X402_NETWORK, new ExactEvmScheme());

  const routes: Record<string, unknown> = {};
  for (const [name, price] of Object.entries(OFFERING_PRICES)) {
    routes[`GET /scan/${name}`] = {
      accepts: { scheme: "exact", price, network: c.env.X402_NETWORK, payTo: c.env.PAY_TO_ADDRESS },
      description: `VAPE ${name} — real GoPlus/DexScreener/DefiLlama data, no simulation.`,
    };
  }
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

export default app;
