/**
 * OpenAPI 3.1 discovery document for VAPE's x402 offerings.
 *
 * Why this exists: x402scan.com's discovery spec (https://www.x402scan.com/discovery/spec)
 * states plainly that "OpenAPI is the canonical discovery contract. Publish your
 * spec at /openapi.json." Before this module, VAPE served neither /openapi.json
 * nor the RFC 8288 `Link: <...>; rel="service-desc"` header pointing at one, so
 * x402scan's "Add your API" probe reported "No discovery document found" for
 * every VAPE route — despite each route serving a complete, spec-correct x402 v2
 * PAYMENT-REQUIRED challenge. The gap was purely the missing static contract,
 * not the runtime payment gate.
 *
 * The same doc is what x402scan's POST /api/x402/registry/register-origin reads
 * to discover and register every resource from an origin in one call, instead of
 * a human pasting 27 URLs into the single-URL "Add" form one at a time.
 *
 * Two rules from that spec are load-bearing here and easy to get wrong:
 *
 *  1. "Runtime 402 behavior is authoritative over static metadata." So this
 *     document is generated from the SAME PaidRoute catalog that builds the
 *     paymentMiddleware() route config in index.ts — never a hand-maintained
 *     second copy that could silently drift out of agreement with the real gate.
 *
 *  2. "OpenAPI x-payment-info.price.amount is decimal USD; runtime x402 v2
 *     accepts[].amount is token atomic units (for USDC, 0.01 => '10000')." The
 *     two are deliberately different units — priceToDecimalUsd() below produces
 *     the decimal-USD form for this document only; the atomic-unit conversion
 *     stays where it already was, inside the x402 middleware.
 */

/** One x402-gated route, as both the payment middleware and this doc see it. */
export type PaidRoute = {
  /** Offering name, e.g. "exploit_check" — also the OpenAPI operationId stem. */
  name: string;
  /** Path on this origin, e.g. "/scan/exploit_check". */
  path: string;
  /** Price in the "$0.01" display form the x402 middleware already uses. */
  price: string;
  /** Human/agent-readable description, shared with the x402 discovery extension. */
  description: string;
  tags: string[];
  /** JSON-Schema-ish property bag, shared with declareDiscoveryExtension(). */
  inputSchema: { properties: Record<string, unknown>; required?: string[] };
};

/**
 * "$0.01" -> "0.01". x402scan's spec requires x-payment-info.price.amount to be
 * decimal USD, while the middleware's own price strings carry a leading "$".
 * Anything without a "$" is passed through unchanged so a already-decimal value
 * stays valid rather than being mangled.
 */
export function priceToDecimalUsd(price: string): string {
  return price.trim().replace(/^\$/, "");
}

/**
 * Query parameters for one route, derived from the route's own input schema so
 * the documented inputs can't drift from what the handler actually reads.
 * x402scan's spec calls an input schema per invocable route "required for
 * reliable agent invocation and robust listing behavior."
 */
function parametersFor(route: PaidRoute): Record<string, unknown>[] {
  const required = new Set(route.inputSchema.required ?? []);
  return Object.entries(route.inputSchema.properties).map(([name, schema]) => {
    const s = (schema ?? {}) as Record<string, unknown>;
    const param: Record<string, unknown> = {
      in: "query",
      name,
      schema: { type: s.type ?? "string", ...(s.description ? { description: s.description } : {}) },
    };
    if (s.description) param.description = s.description;
    if (required.has(name)) param.required = true;
    return param;
  });
}

/**
 * Agent-facing overview. x402scan's spec: "Add high-level guidance in
 * info.x-guidance for user-friendly discovery. This document should explain to
 * an agent how to use your API at a high level."
 */
export function guidance(origin: string): string {
  return [
    "VAPE is an autonomous on-chain security detective for Base (ERC-8004 identity #59900).",
    "Every endpoint below is a single x402-gated GET returning real data from live sources —",
    "no simulated or placeholder responses. When a source is unavailable the response says so",
    "rather than inventing a result.",
    "",
    "## Paying",
    "- All routes settle in USDC on Base (eip155:8453) via the x402 protocol, v2.",
    "- Request the URL with no payment to receive a 402 and the PAYMENT-REQUIRED challenge header,",
    "  then retry with the X-PAYMENT header. Prices below are per-call and flat.",
    "",
    "## Security scans (/scan/*)",
    "- exploit_check ($0.01) — contract verification + proxy-swap surface.",
    "- token_safety_check ($0.02) — token-safety + liquidity scan with a weighted 0-100 score.",
    "- liquidity_check ($0.02) — liquidity depth and top pair DEX.",
    "- rug_pull_alert ($0.03) — owner-power and rug-risk flags.",
    "- market_intel ($0.07) — Base TVL trend, per-protocol share/category breakdown, "
      + "concentration risk, DEX volume, gainers/losers, prices, sentiment, and a narrative summary.",
    "- dossier_check ($0.10) — VAPE's deepest instant verdict; score, meme-factory-template",
    "  detection, recent-hack correlation, web-reputation and declared-socials checks, plus a",
    "  frontier-LLM read of the verified source.",
    "- tx_decode ($0.05) — plain-language decode + risk flags for any Base/EVM tx hash.",
    "- community_intel_broadcast ($0.10) — VAPE's latest 6-hourly consolidated intel broadcast.",
    "- bulk_safety_bundle ($0.50) — token_safety_check batched over 5-25 tokens, flat-priced.",
    "- website_review ($0.15) — phishing/scam-page red-flag read of a plain website URL.",
    "- bounty_deep_dive / deep_contract_audit ($1.00) — asynchronous. Payment queues a real",
    "  Slither/Halmos/Mythril/Aderyn + frontier-LLM audit and returns a job id immediately;",
    "  the finished report is delivered privately by polling or an optional callback_url,",
    "  never published publicly.",
    "",
    "## Market data (/data/*)",
    "Keyless, mostly $0.01 each: token price-oracle intel and charts, protocol TVL/fees/",
    "unlocks/treasury, chain overviews, DEX volumes, yields, stablecoin depeg, and bridge",
    "volumes. wallet_pnl_deepdive ($0.25) returns real Base-mainnet wallet",
    "balances with a per-holding unrealized-P&L estimate.",
    "",
    `Free, unpaid context endpoints: ${origin}/ (offering catalog) and ${origin}/x402/feed`,
    "(VAPE's own settled-job ledger, useful for verifying this service's real usage history).",
  ].join("\n");
}

/**
 * Builds the full OpenAPI 3.1 document.
 *
 * @param origin - This worker's own origin, taken from the live request rather
 *   than hardcoded, so a preview/staging deployment documents itself correctly.
 * @param routes - The same catalog the x402 payment middleware is built from.
 * @param contactEmail - Published in info.contact.email. Per x402scan's spec this
 *   "lets them verify ownership of their origin, allows users to contact them,
 *   and lets them customize their merchant pages."
 */
export function buildOpenApiDocument(
  origin: string,
  routes: PaidRoute[],
  contactEmail: string,
): Record<string, unknown> {
  const paths: Record<string, unknown> = {};
  for (const route of routes) {
    paths[route.path] = {
      get: {
        operationId: `vape_${route.name}`,
        summary: route.description,
        tags: route.tags,
        // Required per-operation by the Agentcash Discovery v1 profile, which
        // lists "an effective OpenAPI `security` declaration" alongside
        // summary and responses. Payment is declared separately via
        // x-payment-info: "Authentication MUST use OpenAPI `security`. Use
        // `security: []` to explicitly declare that an operation has no API
        // authentication requirement."
        //
        // Empty array is correct and load-bearing, not a placeholder: VAPE has
        // no API keys or SIWX login: paying the 402 is the only gate. The
        // spec's auth-hint table maps (security `[]` + x-payment-info present)
        // to the `paid` hint, which is exactly how these routes should list.
        // Omitting the field leaves that derivation undefined.
        security: [],
        "x-payment-info": {
          price: { mode: "fixed", currency: "USD", amount: priceToDecimalUsd(route.price) },
          protocols: [{ x402: {} }],
        },
        parameters: parametersFor(route),
        responses: {
          "200": { description: "Successful response" },
          "402": { description: "Payment Required" },
        },
      },
    };
  }

  return {
    openapi: "3.1.0",
    info: {
      title: "VAPE",
      // Kept short on purpose: directory cards (e.g. x402scan.com's server
      // page) truncate info.description at roughly 100 characters with an
      // ellipsis and no "show more" — confirmed live, where the previous
      // 153-char version cut off mid-list after "token safety scans,". The
      // full offering list already lives in x-guidance/llms.txt below, which
      // isn't subject to that card's width limit.
      description:
        "Autonomous on-chain security detective for Base — pay-per-call audits and safety scans.",
      version: "1.0.0",
      "x-guidance": guidance(origin),
      contact: {
        name: "VAPE",
        email: contactEmail,
        url: "https://github.com/jUXTAPOSITION1/V.A.P.E",
      },
    },
    servers: [{ url: origin }],
    // Canonical optional extension from the Agentcash Discovery v1 profile:
    // "OpenAPI carries machine metadata. Freeform agent guidance is fetched
    // separately, typically from llms.txt." info.x-guidance above stays as the
    // short inline form the same spec recommends; this points at the full text
    // for clients that fetch guidance on demand instead of inline.
    "x-agentcash-guidance": { llmsTxtUrl: `${origin}/llms.txt` },
    tags: [
      { name: "security", description: "Contract, token, and website security analysis" },
      { name: "market-data", description: "Keyless on-chain market and protocol data" },
    ],
    paths,
  };
}
