/**
 * VAPE's market-data tool tier — one x402 endpoint per tool. Most are priced
 * at $0.01 and backed by lib/defillama.ts (keyless); prediction_market_odds
 * is also $0.01 but backed by lib/predictionMarkets.ts (also keyless);
 * wallet_pnl_deepdive is priced separately at $0.25 and backed by
 * lib/codex.ts (needs a server-side CODEX_API_KEY, hence the `env`
 * parameter on `run` below — every other offering here ignores it).
 *
 * Token logos + rich data: every protocol/chain/fee/dex tool carries a real
 * hosted `logo` URL; token-level tools (intel, chart) are enriched here with
 * the token's real DexScreener image, so a buyer always gets an icon
 * alongside the numbers. Nothing is fabricated — a missing logo is simply
 * absent.
 *
 * Each offering is defined once in DL_OFFERINGS; index.ts derives the x402
 * routes, the Bazaar discovery metadata, and the root listing from that single
 * array, exactly the way the 6 security offerings work.
 */
import * as dl from "./lib/defillama";
import * as predictionMarkets from "./lib/predictionMarkets";
import { getPortfolio } from "./lib/alchemy";
import { getCurrentPrices } from "./lib/coingecko";
import { estimateCostBasis } from "./lib/costBasis";

// Structural subset of worker/src/index.ts's `Env` — avoids a circular
// import (index.ts imports this file) while still typechecking `c.env`
// (a superset) at every call site.
export interface DlEnv {
  ALCHEMY_API_KEY?: string;
  COINGECKO_API_KEY?: string;
}

export interface DlQuery {
  address?: string;
  chain?: string;
  slug?: string;
  span?: number;
  project?: string;
  symbol?: string;
  limit?: number;
}

// Real token logo from DexScreener's token endpoint (info.imageUrl) — the same
// hosted image the site already renders for tokens. Best-effort: null on any
// miss, never throws, so it can only ADD a logo, never break a paid result.
async function tokenLogo(address: string): Promise<string | null> {
  try {
    const r = await fetch(`https://api.dexscreener.com/latest/dex/tokens/${address}`,
      { headers: { "User-Agent": "VAPE/1.0", Accept: "application/json" } });
    if (!r.ok) return null;
    const data: any = await r.json();
    const pairs: any[] = Array.isArray(data?.pairs) ? data.pairs : [];
    for (const p of pairs) {
      const img = p?.info?.imageUrl;
      if (img) return img;
    }
    return null;
  } catch {
    return null;
  }
}

function requireAddress(q: DlQuery): string {
  const a = (q.address || "").trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(a)) throw new Error("valid 'address' required (0x-prefixed 40-hex)");
  return a;
}

function requireSlug(q: DlQuery): string {
  const s = (q.slug || "").trim();
  if (!s) throw new Error("'slug' required (protocol slug, e.g. 'aave')");
  return s;
}

export interface DlOffering {
  name: string;
  price: string;
  description: string;
  tags: string[];
  inputSchema: { properties: Record<string, unknown>; required: string[] };
  inputExample: Record<string, unknown>;
  output: Record<string, unknown>;
  run: (q: DlQuery, env: DlEnv) => Promise<Record<string, unknown>>;
}

// Chain-slug conventions differ by host: the coins/price oracle and the
// fees/dexs overviews use lowercase slugs ("base"), while the TVL
// protocols/chains endpoints use display names ("Base"). Each offering below
// documents and defaults the right one.
export const DL_OFFERINGS: DlOffering[] = [
  {
    name: "token_intel",
    price: "$0.01",
    description: "A full independent read on one token: current price + a 0-1 confidence "
      + "score, first-ever-recorded price (an oracle-derived age signal harder to spoof than "
      + "a DEX pair timestamp), the token's real logo, and — when a protocol slug is given — "
      + "fees/revenue, the next unlock event, and treasury own-token share.",
    tags: ["price-oracle", "token", "base"],
    inputSchema: {
      properties: {
        address: { type: "string", description: "token contract address" },
        chain: { type: "string", description: "chain slug, default 'base'" },
        slug: { type: "string", description: "optional protocol slug to add fees/unlocks/treasury" },
      },
      required: ["address"],
    },
    inputExample: { address: "0x0000000000000000000000000000000000000000", chain: "base" },
    output: {
      address: "0x...", logo: "https://...", price: { price: 1.23, confidence: 0.99, symbol: "TKN" },
      first_price: { age_days: 210.5, first_seen_iso: "2025-01-01T00:00:00Z" },
    },
    run: async (q) => {
      const a = requireAddress(q);
      const chain = q.chain || "base";
      const [intel, logo] = await Promise.all([dl.tokenIntel(chain, a, q.slug), tokenLogo(a)]);
      return { ...intel, logo };
    },
  },
  {
    name: "token_chart",
    price: "$0.01",
    description: "Daily price series for a token (default 30d), plus the token's real logo — "
      + "feeds sparklines and a rule-based volatility read.",
    tags: ["price-oracle", "chart", "base"],
    inputSchema: {
      properties: {
        address: { type: "string", description: "token contract address" },
        chain: { type: "string", description: "chain slug, default 'base'" },
        span: { type: "number", description: "days of history, default 30" },
      },
      required: ["address"],
    },
    inputExample: { address: "0x0000000000000000000000000000000000000000", chain: "base", span: 30 },
    output: { address: "0x...", logo: "https://...", symbol: "TKN", prices: [{ timestamp: 0, price: 1.2 }] },
    run: async (q) => {
      const a = requireAddress(q);
      const [chart, logo] = await Promise.all([dl.tokenPriceChart(q.chain || "base", a, q.span || 30), tokenLogo(a)]);
      return { ...chart, logo };
    },
  },
  {
    name: "protocol",
    price: "$0.01",
    description: "Full protocol record: per-chain TVL, category, audits, the official logo, "
      + "Twitter, and description — the 'who is this protocol' snapshot.",
    tags: ["tvl", "protocol"],
    inputSchema: { properties: { slug: { type: "string", description: "protocol slug, e.g. 'aerodrome'" } }, required: ["slug"] },
    inputExample: { slug: "aerodrome" },
    output: { slug: "aerodrome", name: "Aerodrome", logo: "https://...", tvl: { Base: 900000000 }, audits: "2" },
    run: async (q) => dl.protocol(requireSlug(q)),
  },
  {
    name: "protocol_fees",
    price: "$0.01",
    description: "A protocol's real earned fees + revenue (24h/7d/30d/1y/all-time) with its logo — 'does this "
      + "actually make money, or is it just parked TVL?', a legitimacy signal raw TVL misses.",
    tags: ["fees", "revenue", "protocol"],
    inputSchema: { properties: { slug: { type: "string", description: "protocol slug" } }, required: ["slug"] },
    inputExample: { slug: "aave" },
    output: { slug: "aave", name: "AAVE", logo: "https://...", fees_24h: 500000, revenue_24h: 90000 },
    run: async (q) => dl.protocolFees(requireSlug(q)),
  },
  {
    name: "unlocks",
    price: "$0.01",
    description: "Token unlock / emission schedule for a protocol — surfaces the next upcoming "
      + "unlock event (a concrete dump-risk an investigator must flag) and how many days out it is.",
    tags: ["unlocks", "emissions", "risk"],
    inputSchema: { properties: { slug: { type: "string", description: "protocol slug" } }, required: ["slug"] },
    inputExample: { slug: "aptos" },
    output: { slug: "aptos", next_unlock: { in_days: 9.5, description: "cliff", amount: 1000000 }, tracked_events: 42 },
    run: async (q) => dl.unlocks(requireSlug(q)),
  },
  {
    name: "treasury",
    price: "$0.01",
    description: "A protocol's on-chain treasury composition — total USD, own-token USD, and the "
      + "own-token share (a treasury that's ~all its own token is a fragility signal).",
    tags: ["treasury", "risk"],
    inputSchema: { properties: { slug: { type: "string", description: "protocol slug" } }, required: ["slug"] },
    inputExample: { slug: "uniswap" },
    output: { slug: "uniswap", treasury_usd: 4000000000, own_token_usd: 3800000000, own_token_share: 0.95 },
    run: async (q) => dl.treasury(requireSlug(q)),
  },
  {
    name: "chain_protocols",
    price: "$0.01",
    description: "Top protocols on a chain by TVL (default Base), each with its real logo, category, "
      + "and 24h/7d change — the chain-ecosystem view.",
    tags: ["tvl", "chain", "base"],
    inputSchema: {
      properties: {
        chain: { type: "string", description: "chain display name, default 'Base'" },
        limit: { type: "number", description: "how many protocols, default 20" },
      },
      required: [],
    },
    inputExample: { chain: "Base", limit: 20 },
    output: { chain: "Base", count: 120, protocols: [{ name: "Aerodrome", logo: "https://...", tvl_usd: 900000000 }] },
    run: async (q) => dl.protocolsOnChain(q.chain || "Base", q.limit || 20),
  },
  {
    name: "chain_overview",
    price: "$0.01",
    description: "A chain's headline TVL and its rank among all tracked chains (default Base).",
    tags: ["tvl", "chain", "base"],
    inputSchema: { properties: { chain: { type: "string", description: "chain display name, default 'Base'" } }, required: [] },
    inputExample: { chain: "Base" },
    output: { chain: "Base", tvl_usd: 4100000000, rank: 7, total_chains: 300 },
    run: async (q) => dl.chainOverview(q.chain || "Base"),
  },
  {
    name: "chain_fees",
    price: "$0.01",
    description: "Fee-earning protocols on a chain, ranked, each with its logo (default Base) — the "
      + "chain's real economic activity, not just parked capital.",
    tags: ["fees", "chain", "base"],
    inputSchema: { properties: { chain: { type: "string", description: "chain slug, default 'base'" } }, required: [] },
    inputExample: { chain: "base" },
    output: { chain: "base", total_fees_24h: 300000, protocols: [{ name: "Aerodrome", logo: "https://...", fees_24h: 120000 }] },
    run: async (q) => dl.chainFees(q.chain || "base"),
  },
  {
    name: "dex_volumes",
    price: "$0.01",
    description: "DEX trading volume on a chain by venue, each with its logo (default Base) — real "
      + "trading activity across the chain's exchanges.",
    tags: ["dex", "volume", "base"],
    inputSchema: { properties: { chain: { type: "string", description: "chain slug, default 'base'" } }, required: [] },
    inputExample: { chain: "base" },
    output: { chain: "base", total_vol_24h: 200000000, dexs: [{ name: "Aerodrome", logo: "https://...", vol_24h: 150000000 }] },
    run: async (q) => dl.dexVolumes(q.chain || "base"),
  },
  {
    name: "yields",
    price: "$0.01",
    description: "Yield pools filtered by chain/project/symbol, ranked by TVL, with apy/apyBase/"
      + "ilRisk/exposure — enough to tell a real yield venue from a trap (huge APY + tiny TVL = red flag).",
    tags: ["yields", "apy"],
    inputSchema: {
      properties: {
        chain: { type: "string", description: "chain filter, e.g. 'Base'" },
        project: { type: "string", description: "project filter, e.g. 'aave-v3'" },
        symbol: { type: "string", description: "symbol filter, e.g. 'USDC'" },
      },
      required: [],
    },
    inputExample: { chain: "Base", symbol: "USDC" },
    output: { count: 12, pools: [{ project: "aave-v3", symbol: "USDC", tvl_usd: 5000000, apy: 4.2, il_risk: "no" }] },
    run: async (q) => dl.yieldPools({ chain: q.chain, project: q.project, symbol: q.symbol }),
  },
  {
    name: "stablecoins",
    price: "$0.01",
    description: "Stablecoins by circulating supply with live peg price and a computed depeg amount "
      + "— a de-pegging stablecoin is a live systemic threat signal.",
    tags: ["stablecoins", "depeg", "risk"],
    inputSchema: { properties: {}, required: [] },
    inputExample: {},
    output: { count: 25, stablecoins: [{ symbol: "USDC", circulating_usd: 3e10, price: 1.0, depeg: 0.0 }] },
    run: async () => dl.stablecoins(),
  },
  {
    name: "bridges",
    price: "$0.01",
    description: "Tracked bridges ranked by recent daily volume — bridge exploits are a top attack "
      + "class, and this is the capital-flow data that category needs a source for.",
    tags: ["bridges", "volume", "threat"],
    inputSchema: { properties: {}, required: [] },
    inputExample: {},
    output: { count: 25, bridges: [{ name: "Across", last_daily_volume: 5000000, chains: ["Base"] }] },
    run: async () => dl.bridges(),
  },
  {
    // Originally Codex-backed (walletBalances/detailedWalletStats/walletChart),
    // rebuilt on Alchemy + CoinGecko after Codex's own API rejected every one
    // of those three fields with "Not authorized: please upgrade your plan" —
    // real wallet-level analytics is gated behind a paid Codex plan, unlike
    // the free token-market-data queries (filterTokens/holders) the trending/
    // new-launches/virtuals-snapshot routes use. Two real buyers were charged
    // $0.25 for a failure before this was caught (see worker's settlement fix
    // in the same PR — a handler failure no longer settles payment either
    // way, but this rebuild is what actually makes the offering deliver).
    // Reuses the exact same free-tier pipeline /cost-basis already runs in
    // production: getPortfolio() (Alchemy) for current holdings,
    // getCurrentPrices() (CoinGecko) for USD value, estimateCostBasis() for
    // a per-token first-acquisition-price P&L estimate — see lib/costBasis.ts
    // for exactly what this does and doesn't compute. This is UNREALIZED P&L
    // on current holdings (current value vs. price when first received),
    // not REALIZED profit from actual sells — a materially smaller claim
    // than Codex's realizedProfitUsd would have been, stated honestly rather
    // than implied. Base mainnet only (Alchemy's setup here is Base-only).
    name: "wallet_pnl_deepdive",
    price: "$0.25",
    description: "A real wallet holdings + P&L estimate via Alchemy + CoinGecko: current token "
      + "balances with USD values, and an unrealized-P&L estimate per holding (current value vs. "
      + "price at first incoming transfer) — an approximation, not full trade-by-trade accounting. "
      + "Base mainnet only.",
    tags: ["wallet", "pnl", "portfolio", "base"],
    inputSchema: {
      properties: { address: { type: "string", description: "wallet address" } },
      required: ["address"],
    },
    inputExample: { address: "0x0000000000000000000000000000000000000000" },
    output: {
      address: "0x...",
      eth_balance: 0.42,
      balances: { items: [{ symbol: "AERO", contractAddress: "0x...", balance: 120.5, valueUsd: 45.6 }] },
      pnl_estimate: {
        method: "first-acquisition-estimate",
        total_current_value_usd: 45.6,
        total_pnl_usd: 12.3,
        tokens_priced: 3,
        per_token: [{ symbol: "AERO", acquiredAt: "2026-01-01T00:00:00.000Z", costBasisUsd: 33.3, currentValueUsd: 45.6, pnlUsd: 12.3, pnlPct: 36.9 }],
      },
    },
    run: async (q, env) => {
      const a = requireAddress(q);
      if (!env.ALCHEMY_API_KEY || !env.COINGECKO_API_KEY) {
        throw new Error("wallet P&L estimate requires ALCHEMY_API_KEY and COINGECKO_API_KEY to be configured");
      }
      const portfolio = await getPortfolio(env, a);
      const priced = await getCurrentPrices(env, portfolio.tokens.map((t) => t.contractAddress.toLowerCase()));
      const balanceItems = portfolio.tokens
        .map((t) => ({
          symbol: t.symbol,
          contractAddress: t.contractAddress,
          balance: t.balance,
          valueUsd: t.balance * (priced[t.contractAddress.toLowerCase()]?.usd ?? 0),
        }))
        .filter((t) => t.balance > 0);
      const tokensForEstimate = portfolio.tokens
        .map((t) => ({ contractAddress: t.contractAddress, symbol: t.symbol, currentBalance: t.balance, currentPriceUsd: priced[t.contractAddress.toLowerCase()]?.usd ?? 0 }))
        .filter((t) => t.currentBalance > 0 && t.currentPriceUsd > 0);
      const perToken = await estimateCostBasis(env, a, tokensForEstimate);
      const priceable = perToken.filter((r) => r.pnlUsd != null);
      return {
        address: a,
        eth_balance: portfolio.ethBalance,
        balances: { items: balanceItems },
        pnl_estimate: {
          method: "first-acquisition-estimate",
          total_current_value_usd: priceable.reduce((s, r) => s + r.currentValueUsd, 0),
          total_pnl_usd: priceable.length ? priceable.reduce((s, r) => s + (r.pnlUsd ?? 0), 0) : null,
          tokens_priced: priceable.length,
          per_token: perToken,
        },
      };
    },
  },
  {
    name: "prediction_market_odds",
    price: "$0.01",
    description: "Live crypto/Base-relevant prediction-market odds from Polymarket and Kalshi — "
      + "market-implied probabilities on hacks, depegs, price thresholds, and protocol milestones, "
      + "ranked by volume. Keyless, free-source data — no API key required either side.",
    tags: ["prediction-markets", "odds", "sentiment", "crypto"],
    inputSchema: {
      properties: { limit: { type: "number", description: "max markets to return, default 20" } },
      required: [],
    },
    inputExample: { limit: 10 },
    output: {
      count: 5,
      markets: [{ platform: "polymarket", question: "Will Bitcoin hit $150k by end of 2026?",
        outcomes: ["Yes", "No"], prices: [0.62, 0.38], volume: 125000.5, url: "https://polymarket.com/event/..." }],
      sources: { polymarket: "ok", kalshi: "ok" },
    },
    run: async (q) => predictionMarkets.cryptoPredictionMarkets(
      q.limit && q.limit > 0 ? Math.min(q.limit, 50) : 20),
  },
];

export const DL_OFFERINGS_BY_NAME: Record<string, DlOffering> =
  Object.fromEntries(DL_OFFERINGS.map((o) => [o.name, o]));

// Uniform envelope matching handlers.ts::fulfill() so a market-data result and
// a security-scan result look identical to a client. Never throws — a bad
// param or an upstream miss comes back as status:"error" with a real message.
export async function fulfillData(name: string, q: DlQuery, env: DlEnv) {
  const off = DL_OFFERINGS_BY_NAME[name];
  if (!off) return { offering: name, status: "error", error: "unknown offering" };
  try {
    const deliverable = await off.run(q, env);
    return {
      offering: name, status: "ok", deliverable,
      source: "vape-real-data", disclaimer: "Real on-chain data. Not investment advice.",
    };
  } catch (e: any) {
    return { offering: name, status: "error", error: String(e?.message || e) };
  }
}
