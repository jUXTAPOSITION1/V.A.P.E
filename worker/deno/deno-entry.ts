/**
 * Deno Deploy entry point — same Hono `app` (src/index.ts) as the Cloudflare
 * Worker, just fed its `Env` via Deno.env instead of a Workers binding.
 * Deno assigns a public *.deno.dev URL automatically on deploy, with no
 * manual subdomain registration step — kept live as a documented fallback
 * in case the Cloudflare account this repo runs on ever re-hits the
 * workers.dev subdomain-registration bug (see worker/README.md's
 * "Cloudflare + Deno Deploy" section).
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
  SOLANA_PAY_TO_ADDRESS: Deno.env.get("SOLANA_PAY_TO_ADDRESS"),
  SOLANA_NETWORK: Deno.env.get("SOLANA_NETWORK") as Env["SOLANA_NETWORK"],
  X402_FACILITATOR_URL: Deno.env.get("X402_FACILITATOR_URL") ?? "https://api.cdp.coinbase.com/platform/v2/x402",
};

Deno.serve((req) => app.fetch(req, env));
