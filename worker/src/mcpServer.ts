/**
 * VAPE's x402-paid, agent-to-agent MCP surface.
 *
 * Every tool here is a THIN wrapper around the exact same handler functions
 * the existing HTTP paid routes already call (handlers.ts's fulfill(),
 * dataHandlers.ts's fulfillData()) -- there is no second implementation of
 * any offering to drift out of sync, and each tool's price/description/
 * inputSchema is read directly off HANDLERS/DL_OFFERINGS (the same objects
 * index.ts's PAID_ROUTES/data routes are themselves built from) rather than
 * hand-duplicated here, so a future price or schema change on the HTTP side
 * propagates to the MCP side with zero edits to this file.
 *
 * Settlement is the SAME CDP facilitator + PAY_TO_ADDRESS/SOLANA_PAY_TO_ADDRESS
 * already proven end-to-end by the HTTP paid routes: this file receives an
 * already-built x402ResourceServer (constructed once in index.ts, with
 * ExactEvmScheme/ExactSvmScheme already registered) rather than constructing
 * its own -- one facilitator client, one set of registered schemes, one
 * settlement path for the whole Worker, HTTP or MCP.
 *
 * Stateless by design: buildMcpServer() is called fresh per request (see
 * index.ts's /mcp route), never reused across requests as a module-level
 * singleton -- deliberately avoiding the "cross-client data leak via shared
 * server/transport instance reuse" CVE class the MCP TypeScript SDK has
 * previously shipped (GHSA-345p-7cg4-v4c7), and matching the SDK's own
 * documented stateless-mode pattern for serverless runtimes.
 *
 * Known cost of that statelessness (confirmed via a real local wrangler-dev
 * run, not speculation): buildPaymentRequirementsFromOptions() requires
 * resourceServer.initialize() to have already fetched the facilitator's real
 * supported-kinds list (one CDP GET /supported round-trip) -- unlike
 * index.ts's HTTP routes, whose `accepts` are plain PaymentOption literals
 * and never call initialize() at all. Since a fresh resourceServer is built
 * per /mcp request, that means every connection (even a bare tools/list,
 * which needs no payment) pays one CDP round-trip before this file can
 * finish registering tools. Accepted for now as the correct, spec-compliant
 * use of @x402/mcp's own documented API (its example does the same
 * buildPaymentRequirements() call) rather than forking payment-wrapper
 * internals to defer it -- if CDP latency/reliability on tools/list becomes
 * a real problem, the fix is caching getSupportedKind()'s result in KV with
 * a short TTL, not avoiding initialize() altogether.
 */
import { z, type ZodTypeAny } from "zod";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { createPaymentWrapper } from "@x402/mcp";
import type { x402ResourceServer } from "@x402/core/server";
import { HANDLERS, fulfill, type HandlerName, type Requirement } from "./handlers";
import { DL_OFFERINGS, fulfillData, type DlEnv, type DlQuery } from "./dataHandlers";
import { logJob, type JobRecord, type KVLike } from "./lib/jobLog";

type Caip2Network = `${string}:${string}`;

export interface McpWorkerEnv extends DlEnv {
  PAY_TO_ADDRESS: string;
  X402_NETWORK: Caip2Network;
  SOLANA_PAY_TO_ADDRESS?: string;
  SOLANA_NETWORK?: Caip2Network;
  VAPE_JOBS?: KVLike;
  ETHERSCAN_API_KEY?: string;
  COINGECKO_API_KEY?: string;
  [key: string]: unknown;
}

interface JsonSchemaProp { type?: string; description?: string }
interface JsonInputSchema { properties: Record<string, unknown>; required: string[] }

// Every offering's inputSchema here is a flat bag of string/number leaves
// (address, chain, slug, span, limit, ...) -- no nesting anywhere in
// HANDLERS'/DL_OFFERINGS' schemas -- so a direct type->Zod mapping covers all
// of them with no per-tool hand-written schema.
function zodShapeFor(schema: JsonInputSchema): Record<string, ZodTypeAny> {
  const shape: Record<string, ZodTypeAny> = {};
  for (const [key, raw] of Object.entries(schema.properties || {})) {
    const prop = (raw || {}) as JsonSchemaProp;
    let field: ZodTypeAny = prop.type === "number" ? z.number() : z.string();
    if (prop.description) field = field.describe(prop.description);
    if (!schema.required?.includes(key)) field = field.optional();
    shape[key] = field;
  }
  return shape;
}

async function buildAccepts(resourceServer: x402ResourceServer, env: McpWorkerEnv, price: string) {
  const options: Array<{ scheme: string; payTo: string; price: string; network: Caip2Network }> = [
    { scheme: "exact", payTo: env.PAY_TO_ADDRESS, price, network: env.X402_NETWORK },
  ];
  if (env.SOLANA_PAY_TO_ADDRESS && env.SOLANA_NETWORK) {
    options.push({ scheme: "exact", payTo: env.SOLANA_PAY_TO_ADDRESS, price, network: env.SOLANA_NETWORK });
  }
  return resourceServer.buildPaymentRequirementsFromOptions(options as any, {});
}

// Best-effort mirror of index.ts's onAfterSettle -> logJob() so MCP-settled
// revenue shows up in the same /x402/feed and /x402/stats dashboards as
// HTTP-settled revenue, not a second, invisible ledger. Never throws --
// logging must never break an already-settled, already-paid tool call.
async function logMcpSettlement(
  env: McpWorkerEnv,
  toolName: string,
  priceUsd: number,
  args: Record<string, unknown>,
  settlement: { transaction?: string | null; network?: string | null; payer?: string | null } | null | undefined,
): Promise<void> {
  if (!env.VAPE_JOBS) return;
  try {
    const record: JobRecord = {
      id: `mcp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      ts: new Date().toISOString(),
      offering: toolName,
      address: typeof args.address === "string" ? args.address : null,
      chain_id: Number(args.chain_id ?? args.chain ?? 8453) || 8453,
      symbol: null,
      name: null,
      verdict: null,
      status: "settled",
      amount_usd: priceUsd,
      latency_ms: null,
      payer: settlement?.payer ?? null,
      tx_hash: settlement?.transaction ?? null,
      network: settlement?.network ?? null,
      error: null,
      facilitator: "cdp",
    };
    await logJob(env.VAPE_JOBS, record);
  } catch {
    // best-effort only
  }
}

function toolResult(payload: unknown) {
  return { content: [{ type: "text" as const, text: JSON.stringify(payload) }] };
}

// Same 6 offerings + prices/descriptions as index.ts's OFFERING_PRICES/
// OFFERING_DISCOVERY (not imported directly -- importing from index.ts here
// would create a circular import back into this file, since index.ts is the
// one that calls buildMcpServer()). Kept in sync by hand, same as every
// other place in this repo that duplicates a small constant table across a
// would-be circular import boundary (e.g. investigateLite.ts's own
// CATEGORY_WEIGHTS mirroring investigate.py's).
const SECURITY_PRICES: Record<HandlerName, string> = {
  exploit_check: "$0.01",
  token_safety_check: "$0.02",
  liquidity_check: "$0.02",
  rug_pull_alert: "$0.03",
  market_intel: "$0.07",
  dossier_check: "$0.10",
};
const SECURITY_DESCRIPTIONS: Record<HandlerName, string> = {
  token_safety_check: "Fast honeypot/tax/owner-power + liquidity safety scan for a token.",
  liquidity_check: "Liquidity depth, lock status, and rug/illiquidity risk for a token.",
  rug_pull_alert: "Mint/owner-power rug-pull risk flags for a token.",
  exploit_check: "Contract-recon-based exploit/vulnerability risk flags.",
  market_intel: "Base TVL/DEX-volume/price narrative: per-protocol share, concentration risk, sentiment.",
  dossier_check: "Full weighted-score investigation (security/liquidity/holders/transparency/narrative/longevity) with verdict.",
};
const SECURITY_INPUT_SCHEMA: JsonInputSchema = {
  properties: {
    address: { type: "string", description: "contract/token address to analyze" },
    chain: { type: "string", description: "optional chain id override, defaults to 8453 (Base)" },
  },
  required: ["address"],
};

/**
 * Builds a fresh McpServer wired to VAPE's real offerings. Call once per
 * request (see index.ts's /mcp route) -- never cache/reuse across requests.
 */
export async function buildMcpServer(resourceServer: x402ResourceServer, env: McpWorkerEnv): Promise<McpServer> {
  // Real, confirmed requirement (not optional/best-effort): buildPaymentRequirementsFromOptions()
  // below throws "Facilitator does not support exact on <network>... call
  // initialize()" without this -- unlike index.ts's own HTTP routes, which
  // build their `accepts` as plain PaymentOption object literals (bypassing
  // buildPaymentRequirementsFromOptions entirely) and so never needed this
  // call. initialize() fetches the facilitator's real supported-kinds list
  // (one CDP /supported round-trip) so the resourceServer actually knows the
  // "exact" scheme on eip155:8453/solana:mainnet is real and payable.
  await resourceServer.initialize();

  const server = new McpServer({ name: "vape-detective", version: "1.0.0" });

  // ── Security suite (6 offerings, same fulfill() dispatch the /scan/<name>
  // routes use) ───────────────────────────────────────────────────────────
  for (const name of Object.keys(HANDLERS) as HandlerName[]) {
    const price = SECURITY_PRICES[name];
    const accepts = await buildAccepts(resourceServer, env, price);
    const paid = createPaymentWrapper(resourceServer, {
      accepts,
      resource: {
        url: `mcp://vape-detective/tool/${name}`,
        description: SECURITY_DESCRIPTIONS[name],
        serviceName: "VAPE",
      },
      hooks: {
        onAfterSettlement: async (ctx) => {
          await logMcpSettlement(env, name, Number(price.replace("$", "")), ctx.arguments, ctx.settlement as any);
        },
      },
    });
    server.registerTool(
      name,
      {
        description: `VAPE ${name} ($${price.replace("$", "")} USDC) — ${SECURITY_DESCRIPTIONS[name]} Real on-chain/market data, no simulation.`,
        inputSchema: zodShapeFor(SECURITY_INPUT_SCHEMA),
      },
      paid(async (args: Requirement) => {
        const result = await fulfill(name, args, env);
        return toolResult(result);
      }) as any,
    );
  }

  // ── Market-data suite (14 offerings, same fulfillData() dispatch the
  // /data/<name> routes use — driven directly off DL_OFFERINGS so a future
  // offering added there needs zero changes here) ───────────────────────
  for (const off of DL_OFFERINGS) {
    const accepts = await buildAccepts(resourceServer, env, off.price);
    const paid = createPaymentWrapper(resourceServer, {
      accepts,
      resource: {
        url: `mcp://vape-detective/tool/${off.name}`,
        description: off.description,
        serviceName: "VAPE",
        tags: off.tags,
      },
      hooks: {
        onAfterSettlement: async (ctx) => {
          await logMcpSettlement(env, off.name, Number(off.price.replace("$", "")), ctx.arguments, ctx.settlement as any);
        },
      },
    });
    server.registerTool(
      off.name,
      {
        description: `VAPE ${off.name} (${off.price} USDC) — ${off.description}`,
        inputSchema: zodShapeFor(off.inputSchema),
      },
      paid(async (args: DlQuery) => {
        const result = await fulfillData(off.name, args, env);
        return toolResult(result);
      }) as any,
    );
  }

  return server;
}
