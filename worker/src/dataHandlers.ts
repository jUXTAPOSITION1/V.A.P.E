/**
 * DefiLlama x402 micro-service tier — one paid endpoint per DefiLlama tool,
 * all priced at $0.01 (the cheapest useful on-chain data a caller can buy from
 * VAPE). Backed by lib/defillama.ts (keyless free API), so the marginal cost
 * to VAPE is ~zero and the price is pure margin funding the agent.
 *
 * "Token logos, rich data": every protocol/chain/fee/dex tool already carries
 * DefiLlama's real hosted `logo` URLs; token-level tools (intel, chart) are
 * enriched here with the token's real DexScreener image, so a buyer always
 * gets an icon alongside the numbers. Nothing is fabricated — a missing logo
 * is simply absent.
 *
 * Each offering is defined once in DL_OFFERINGS; index.ts derives the x402
 * routes, the Bazaar discovery metadata, and the root listing from that single
 * array, exactly the way the 6 security offerings work.
 */
import * as dl from "./lib/defillama";

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
  if (!s) throw new Error("'slug' required (DefiLlama protocol slug, e.g. 'aave')");
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
  run: (q: DlQuery) => Promise<Record<string, unknown>>;
}

// Chain-slug conventions differ by DefiLlama host: the coins/price oracle and
// the fees/dexs overviews use lowercase slugs ("base"), while the TVL
// protocols/chains endpoints use display names ("Base"). Each offering below
// documents and defaults the right one.
export const DL_OFFERINGS: DlOffering[] = [
  {
    name: "dl_token_intel",
    price: "$0.01",
    description: "DefiLlama's full independent read on one token: current price + its own "
      + "0-1 confidence score, first-ever-recorded price (an oracle-derived age signal harder "
      + "to spoof than a DEX pair timestamp), the token's real logo, and — when a protocol slug "
      + "is given — fees/revenue, the next unlock event, and treasury own-token share.",
    tags: ["defillama", "price-oracle", "token", "base"],
    inputSchema: {
      properties: {
        address: { type: "string", description: "token contract address" },
        chain: { type: "string", description: "DefiLlama chain slug, default 'base'" },
        slug: { type: "string", description: "optional DefiLlama protocol slug to add fees/unlocks/treasury" },
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
    name: "dl_token_chart",
    price: "$0.01",
    description: "Daily price series for a token from DefiLlama's oracle (default 30d), plus the "
      + "token's real logo — feeds sparklines and a rule-based volatility read.",
    tags: ["defillama", "price-oracle", "chart", "base"],
    inputSchema: {
      properties: {
        address: { type: "string", description: "token contract address" },
        chain: { type: "string", description: "DefiLlama chain slug, default 'base'" },
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
    name: "dl_protocol",
    price: "$0.01",
    description: "Full DefiLlama protocol record: per-chain TVL, category, audits, the official "
      + "logo, Twitter, and description — the 'who is this protocol' snapshot.",
    tags: ["defillama", "tvl", "protocol"],
    inputSchema: { properties: { slug: { type: "string", description: "DefiLlama protocol slug, e.g. 'aerodrome'" } }, required: ["slug"] },
    inputExample: { slug: "aerodrome" },
    output: { slug: "aerodrome", name: "Aerodrome", logo: "https://...", tvl: { Base: 900000000 }, audits: "2" },
    run: async (q) => dl.protocol(requireSlug(q)),
  },
  {
    name: "dl_protocol_fees",
    price: "$0.01",
    description: "A protocol's real earned fees + revenue (24h/7d/30d) with its logo — 'does this "
      + "actually make money, or is it just parked TVL?', a legitimacy signal raw TVL misses.",
    tags: ["defillama", "fees", "revenue", "protocol"],
    inputSchema: { properties: { slug: { type: "string", description: "DefiLlama protocol slug" } }, required: ["slug"] },
    inputExample: { slug: "aave" },
    output: { slug: "aave", name: "AAVE", logo: "https://...", fees_24h: 500000, revenue_24h: 90000 },
    run: async (q) => dl.protocolFees(requireSlug(q)),
  },
  {
    name: "dl_unlocks",
    price: "$0.01",
    description: "Token unlock / emission schedule for a protocol — surfaces the next upcoming "
      + "unlock event (a concrete dump-risk an investigator must flag) and how many days out it is.",
    tags: ["defillama", "unlocks", "emissions", "risk"],
    inputSchema: { properties: { slug: { type: "string", description: "DefiLlama protocol slug" } }, required: ["slug"] },
    inputExample: { slug: "aptos" },
    output: { slug: "aptos", next_unlock: { in_days: 9.5, description: "cliff", amount: 1000000 }, tracked_events: 42 },
    run: async (q) => dl.unlocks(requireSlug(q)),
  },
  {
    name: "dl_treasury",
    price: "$0.01",
    description: "A protocol's on-chain treasury composition — total USD, own-token USD, and the "
      + "own-token share (a treasury that's ~all its own token is a fragility signal).",
    tags: ["defillama", "treasury", "risk"],
    inputSchema: { properties: { slug: { type: "string", description: "DefiLlama protocol slug" } }, required: ["slug"] },
    inputExample: { slug: "uniswap" },
    output: { slug: "uniswap", treasury_usd: 4000000000, own_token_usd: 3800000000, own_token_share: 0.95 },
    run: async (q) => dl.treasury(requireSlug(q)),
  },
  {
    name: "dl_chain_protocols",
    price: "$0.01",
    description: "Top protocols on a chain by TVL (default Base), each with its real logo, category, "
      + "and 24h/7d change — the chain-ecosystem view.",
    tags: ["defillama", "tvl", "chain", "base"],
    inputSchema: {
      properties: {
        chain: { type: "string", description: "DefiLlama chain display name, default 'Base'" },
        limit: { type: "number", description: "how many protocols, default 20" },
      },
      required: [],
    },
    inputExample: { chain: "Base", limit: 20 },
    output: { chain: "Base", count: 120, protocols: [{ name: "Aerodrome", logo: "https://...", tvl_usd: 900000000 }] },
    run: async (q) => dl.protocolsOnChain(q.chain || "Base", q.limit || 20),
  },
  {
    name: "dl_chain_overview",
    price: "$0.01",
    description: "A chain's headline TVL and its rank among all chains DefiLlama tracks (default Base).",
    tags: ["defillama", "tvl", "chain", "base"],
    inputSchema: { properties: { chain: { type: "string", description: "chain display name, default 'Base'" } }, required: [] },
    inputExample: { chain: "Base" },
    output: { chain: "Base", tvl_usd: 4100000000, rank: 7, total_chains: 300 },
    run: async (q) => dl.chainOverview(q.chain || "Base"),
  },
  {
    name: "dl_chain_fees",
    price: "$0.01",
    description: "Fee-earning protocols on a chain, ranked, each with its logo (default Base) — the "
      + "chain's real economic activity, not just parked capital.",
    tags: ["defillama", "fees", "chain", "base"],
    inputSchema: { properties: { chain: { type: "string", description: "DefiLlama chain slug, default 'base'" } }, required: [] },
    inputExample: { chain: "base" },
    output: { chain: "base", total_fees_24h: 300000, protocols: [{ name: "Aerodrome", logo: "https://...", fees_24h: 120000 }] },
    run: async (q) => dl.chainFees(q.chain || "base"),
  },
  {
    name: "dl_dex_volumes",
    price: "$0.01",
    description: "DEX trading volume on a chain by venue, each with its logo (default Base) — real "
      + "trading activity across the chain's exchanges.",
    tags: ["defillama", "dex", "volume", "base"],
    inputSchema: { properties: { chain: { type: "string", description: "DefiLlama chain slug, default 'base'" } }, required: [] },
    inputExample: { chain: "base" },
    output: { chain: "base", total_vol_24h: 200000000, dexs: [{ name: "Aerodrome", logo: "https://...", vol_24h: 150000000 }] },
    run: async (q) => dl.dexVolumes(q.chain || "base"),
  },
  {
    name: "dl_derivatives",
    price: "$0.01",
    description: "Perps / derivatives trading volume by venue, each with its logo — the derivatives "
      + "market's real activity across all tracked exchanges.",
    tags: ["defillama", "derivatives", "perps", "volume"],
    inputSchema: { properties: {}, required: [] },
    inputExample: {},
    output: { total_vol_24h: 5000000000, venues: [{ name: "Hyperliquid", logo: "https://...", vol_24h: 3000000000 }] },
    run: async () => dl.derivativesVolumes(),
  },
  {
    name: "dl_yields",
    price: "$0.01",
    description: "Yield pools filtered by chain/project/symbol, ranked by TVL, with apy/apyBase/"
      + "ilRisk/exposure — enough to tell a real yield venue from a trap (huge APY + tiny TVL = red flag).",
    tags: ["defillama", "yields", "apy"],
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
    name: "dl_stablecoins",
    price: "$0.01",
    description: "Stablecoins by circulating supply with live peg price and a computed depeg amount "
      + "— a de-pegging stablecoin is a live systemic threat signal.",
    tags: ["defillama", "stablecoins", "depeg", "risk"],
    inputSchema: { properties: {}, required: [] },
    inputExample: {},
    output: { count: 25, stablecoins: [{ symbol: "USDC", circulating_usd: 3e10, price: 1.0, depeg: 0.0 }] },
    run: async () => dl.stablecoins(),
  },
  {
    name: "dl_bridges",
    price: "$0.01",
    description: "Tracked bridges ranked by recent daily volume — bridge exploits are a top attack "
      + "class, and this is the capital-flow data that category needs a source for.",
    tags: ["defillama", "bridges", "volume", "threat"],
    inputSchema: { properties: {}, required: [] },
    inputExample: {},
    output: { count: 25, bridges: [{ name: "Across", last_daily_volume: 5000000, chains: ["Base"] }] },
    run: async () => dl.bridges(),
  },
];

export const DL_OFFERINGS_BY_NAME: Record<string, DlOffering> =
  Object.fromEntries(DL_OFFERINGS.map((o) => [o.name, o]));

// Uniform envelope matching handlers.ts::fulfill() so a DefiLlama result and a
// security-scan result look the same to a client. Never throws — a bad param
// or an upstream miss comes back as status:"error" with a real message.
export async function fulfillData(name: string, q: DlQuery) {
  const off = DL_OFFERINGS_BY_NAME[name];
  if (!off) return { offering: name, status: "error", error: "unknown offering" };
  try {
    const deliverable = await off.run(q);
    return {
      offering: name, status: "ok", deliverable,
      source: "defillama-free-api", disclaimer: "Real DefiLlama data. Not investment advice.",
    };
  } catch (e: any) {
    return { offering: name, status: "error", error: String(e?.message || e) };
  }
}
