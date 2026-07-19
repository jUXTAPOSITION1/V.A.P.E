/**
 * TypeScript port of agents/codex_data.py — VAPE's Codex.io GraphQL data
 * layer, server-side only. Codex requires a bearer API key that can never
 * ship to the browser, unlike the keyless DefiLlama/CoinGecko calls the
 * site makes directly — so unlike lib/defillama.ts, nothing here is ever
 * called client-side; it's only reachable through the worker's own routes
 * (see index.ts's /virtuals-snapshot and /trending-base).
 *
 * Same design law as every other lib/*.ts here: every function returns real
 * data or an `{ error }` object and NEVER throws. Per-route HTTP caching +
 * rate limiting is handled by Hono's `cache` + `rateLimiter` middleware in
 * index.ts (same pattern as /portfolio, /nfts) — this layer is a thin
 * fetch+parse, no separate request-count cap needed (the edge cache already
 * bounds how often a shared public route actually reaches Codex).
 *
 * Field names below are sourced from Codex's public SDK examples
 * (github.com/Codex-Data/sdk) — confirmed: filterTokens(filters, networks,
 * limit) -> results{priceUSD, volume24, token{name,symbol}}; holders(input)
 * -> {count, top10HoldersPercent, items}; token(address, networkId) exists
 * as a singular lookup. Not independently verified against a live response
 * (Codex's host is unreachable from this dev sandbox, same constraint as
 * every other external API in this repo) — spot-check the first real
 * response in production the way every other sweep here does.
 */
const GRAPHQL_URL = "https://graph.codex.io/graphql";
const UA = "VAPE/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)";

export type CodexResult = Record<string, unknown> & { error?: string };

function isErr(x: unknown): x is { error: string } {
  return Boolean(x && typeof x === "object" && (x as Record<string, unknown>).error);
}

async function codexQuery(
  apiKey: string | undefined,
  query: string,
  variables: Record<string, unknown> = {},
): Promise<any> {
  if (!apiKey) return { error: "no_key", note: "CODEX_API_KEY not configured" };
  try {
    const r = await fetch(GRAPHQL_URL, {
      method: "POST",
      headers: { "User-Agent": UA, "Content-Type": "application/json", Authorization: apiKey },
      body: JSON.stringify({ query, variables }),
    });
    if (!r.ok) return { error: `HTTP ${r.status}` };
    const body: any = await r.json();
    if (body.errors) return { error: (body.errors as any[]).map((e) => e.message || String(e)).join("; ") };
    return body.data || {};
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}

// Base mainnet's Codex network id — Codex's ids are plain EVM chain ids.
export const BASE_NETWORK_ID = 8453;

export interface TrendingTokenRow {
  priceUSD?: number;
  volume24?: number;
  liquidity?: number;
  marketCap?: number;
  change24?: number;
  token: { name?: string; symbol?: string; address?: string; networkId?: number };
}

export async function trendingTokens(
  apiKey: string | undefined,
  networkIds: number[] | undefined,
  limit = 20,
): Promise<CodexResult> {
  const query = `
    query TrendingTokens($limit: Int!, $networkFilter: [Int!]) {
      filterTokens(limit: $limit, filters: {network: $networkFilter}) {
        results {
          priceUSD
          volume24
          liquidity
          marketCap
          change24
          token { name symbol address networkId }
        }
      }
    }`;
  const d = await codexQuery(apiKey, query, { limit, networkFilter: networkIds });
  if (isErr(d)) return d;
  const results: TrendingTokenRow[] = (d.filterTokens && d.filterTokens.results) || [];
  return { ts: new Date().toISOString(), tokens: results };
}

export async function tokenDetail(
  apiKey: string | undefined,
  address: string,
  networkId: number,
): Promise<CodexResult> {
  const query = `
    query TokenDetail($address: String!, $networkId: Int!) {
      token(address: $address, networkId: $networkId) {
        priceUSD
        volume24
        liquidity
        marketCap
        change24
        name
        symbol
      }
    }`;
  const d = await codexQuery(apiKey, query, { address, networkId });
  if (isErr(d)) return d;
  return { address, networkId, ...(d.token || {}) };
}

export async function tokenHolders(
  apiKey: string | undefined,
  tokenId: string,
  networkId: number,
  limit = 10,
): Promise<CodexResult> {
  const query = `
    query TokenHolders($input: HoldersInput!) {
      holders(input: $input) { count top10HoldersPercent items { address balance } }
    }`;
  const d = await codexQuery(apiKey, query, { input: { tokenId, networkId, limit } });
  if (isErr(d)) return d;
  const h = d.holders || {};
  return { tokenId, count: h.count, top10HoldersPercent: h.top10HoldersPercent, items: h.items || [] };
}

export async function walletBalances(
  apiKey: string | undefined,
  walletAddress: string,
  networkIds: number[] | undefined,
): Promise<CodexResult> {
  const query = `
    query WalletBalances($wallet: String!, $networks: [Int!]) {
      balances(input: {walletAddress: $wallet, networks: $networks, includeNative: true, removeScams: true, limit: 100}) {
        items { shiftedBalance balanceUsd token { name symbol networkId } }
      }
    }`;
  const d = await codexQuery(apiKey, query, { wallet: walletAddress, networks: networkIds });
  if (isErr(d)) return d;
  return { wallet: walletAddress, items: (d.balances && d.balances.items) || [] };
}

export async function walletPnlStats(
  apiKey: string | undefined,
  walletAddress: string,
  networkId: number,
): Promise<CodexResult> {
  const query = `
    query WalletStats($wallet: String!, $networkId: Int!) {
      detailedWalletStats(input: {walletAddress: $wallet, networkId: $networkId}) {
        statsUsd { realizedProfitUsd realizedProfitPercentage volume tokensTraded }
      }
    }`;
  const d = await codexQuery(apiKey, query, { wallet: walletAddress, networkId });
  if (isErr(d)) return d;
  const stats = (d.detailedWalletStats && d.detailedWalletStats.statsUsd) || {};
  // snake_case to match agents/codex_data.py::wallet_pnl_stats() field-for-field
  // (this repo's established Python/TS parity convention — see protocol_fees()).
  return {
    wallet: walletAddress,
    network_id: networkId,
    realized_profit_usd: stats.realizedProfitUsd,
    realized_profit_pct: stats.realizedProfitPercentage,
    volume_usd: stats.volume,
    tokens_traded: stats.tokensTraded,
  };
}

export async function walletPnlChart(
  apiKey: string | undefined,
  walletAddress: string,
  networkId: number,
  resolution = "1D",
): Promise<CodexResult> {
  const query = `
    query WalletChart($wallet: String!, $networkId: Int!, $resolution: String!) {
      walletChart(input: {walletAddress: $wallet, networkId: $networkId, resolution: $resolution}) {
        points { timestamp realizedProfitUsd }
      }
    }`;
  const d = await codexQuery(apiKey, query, { wallet: walletAddress, networkId, resolution });
  if (isErr(d)) return d;
  return { wallet: walletAddress, points: (d.walletChart && d.walletChart.points) || [] };
}

// Best-effort "is this a Virtuals-launched agent token" tag for the trending
// list — Codex's filterTokens/token queries don't expose a confirmed
// deployer/launchpad filter, so this cross-checks DexScreener's own pair
// index instead (the same host dataHandlers.ts's tokenLogo() already calls
// successfully in production). Virtuals' bonding-curve trading is indexed
// under its own dexId there; a miss just means "not tagged", never a
// fabricated positive.
export async function isVirtualsToken(address: string): Promise<boolean> {
  try {
    const r = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${address}`, {
      headers: { "User-Agent": UA, Accept: "application/json" },
    });
    if (!r.ok) return false;
    const data: any = await r.json();
    const pairs: any[] = Array.isArray(data?.pairs) ? data.pairs : [];
    return pairs.some((p) => String(p?.dexId || "").toLowerCase().includes("virtuals"));
  } catch {
    return false;
  }
}
