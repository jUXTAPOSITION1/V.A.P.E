/**
 * Deno Deploy entry point — this repo's only worker deployment target.
 * `src/index.ts`'s Hono `app` was originally written for Cloudflare Workers
 * and still reads that way (fed its `Env` here via Deno.env instead of a
 * Workers binding) because it has zero Cloudflare-specific code either way;
 * see worker/README.md's "Why Deno Deploy, not Cloudflare" for why this
 * repo moved off Cloudflare entirely. Deno assigns a public *.deno.dev URL
 * automatically on deploy, with no manual subdomain registration step.
 */
import app, { type Env } from "../src/index.ts";

const env: Env = {
  ETHERSCAN_API_KEY: Deno.env.get("ETHERSCAN_API_KEY"),
  CDP_API_KEY_ID: Deno.env.get("CDP_API_KEY_ID"),
  CDP_API_KEY_SECRET: Deno.env.get("CDP_API_KEY_SECRET"),
  ALCHEMY_API_KEY: Deno.env.get("ALCHEMY_API_KEY"),
  COINGECKO_API_KEY: Deno.env.get("COINGECKO_API_KEY"),
  GH_DISPATCH_TOKEN: Deno.env.get("GH_DISPATCH_TOKEN"),
  PAY_TO_ADDRESS: Deno.env.get("PAY_TO_ADDRESS") ?? "",
  X402_NETWORK: (Deno.env.get("X402_NETWORK") ?? "eip155:8453") as Env["X402_NETWORK"],
  X402_FACILITATOR_URL: Deno.env.get("X402_FACILITATOR_URL") ?? "https://api.cdp.coinbase.com/platform/v2/x402",
};

Deno.serve((req) => app.fetch(req, env));
