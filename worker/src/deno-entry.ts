/**
 * Deno Deploy entry point — same Hono `app` (src/index.ts) as the Cloudflare
 * Worker, just fed its `Env` via Deno.env instead of a Workers binding.
 * Deno assigns a public *.deno.dev URL automatically on deploy, with no
 * manual subdomain registration step (unlike the Cloudflare account issue
 * this was built to route around).
 */
import app, { type Env } from "./index.ts";

const env: Env = {
  ETHERSCAN_API_KEY: Deno.env.get("ETHERSCAN_API_KEY"),
  CDP_API_KEY_ID: Deno.env.get("CDP_API_KEY_ID"),
  CDP_API_KEY_SECRET: Deno.env.get("CDP_API_KEY_SECRET"),
  ALCHEMY_API_KEY: Deno.env.get("ALCHEMY_API_KEY"),
  PAY_TO_ADDRESS: Deno.env.get("PAY_TO_ADDRESS") ?? "",
  X402_NETWORK: (Deno.env.get("X402_NETWORK") ?? "eip155:8453") as Env["X402_NETWORK"],
  X402_FACILITATOR_URL: Deno.env.get("X402_FACILITATOR_URL") ?? "https://api.cdp.coinbase.com/platform/v2/x402",
};

Deno.serve((req) => app.fetch(req, env));
