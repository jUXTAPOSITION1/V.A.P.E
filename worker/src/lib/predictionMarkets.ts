/**
 * TypeScript port of agents/prediction_markets.py — VAPE's prediction-markets
 * data layer (Polymarket's free, keyless Gamma API + Kalshi's free, keyless
 * markets API), made available to the x402 market-data tool tier.
 *
 * Field-for-field faithful to the Python module so the x402 result and the
 * ACP deliverable never disagree. Same design law: every function returns
 * real data or an `{ error }` object and NEVER throws.
 *
 * Scope is deliberately narrow: crypto/Base-ecosystem-relevant markets only
 * (keyword-filtered), not general politics/sports/macro markets — see the
 * Python module's docstring for why.
 *
 * Hosts: gamma-api.polymarket.com, trading-api.kalshi.com. Neither host is
 * reachable from this dev sandbox (same constraint as every other external
 * API in this repo) — spot-check the first real response in production.
 */
const POLYMARKET_GAMMA = "https://gamma-api.polymarket.com";
const KALSHI_API = "https://trading-api.kalshi.com/trade-api/v2";
const UA = "VAPE/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)";

export type PmResult = Record<string, unknown> & { error?: string };

// Same keyword list as agents/prediction_markets.py's _CRYPTO_RE.
const CRYPTO_RE = new RegExp(
  "\\b(crypto|bitcoin|btc|ethereum|eth|base|solana|sol|xrp|defi|" +
  "stablecoin|usdc|usdt|coinbase|binance|token|blockchain|web3|nft|" +
  "altcoin|memecoin|hack|exploit|rug ?pull|depeg)\\b",
  "i",
);

function nowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function isErr(x: unknown): x is { error: string } {
  return Boolean(x && typeof x === "object" && (x as Record<string, unknown>).error);
}

function isCryptoRelevant(...texts: Array<string | undefined | null>): boolean {
  return texts.some((t) => t && CRYPTO_RE.test(String(t)));
}

function toFloat(v: unknown): number | null {
  if (v === null || v === undefined || v === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function parseJsonField(v: unknown): unknown[] | null {
  if (Array.isArray(v)) return v;
  if (typeof v === "string") {
    try {
      const parsed = JSON.parse(v);
      return Array.isArray(parsed) ? parsed : null;
    } catch {
      return null;
    }
  }
  return null;
}

async function pmGet(url: string): Promise<any> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
    if (!r.ok) return { error: `HTTP ${r.status}`, url };
    return await r.json();
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e), url };
  }
}

interface NormalizedMarket {
  platform: string;
  id: unknown;
  question: string;
  volume: number | null;
  url: string | null;
  [k: string]: unknown;
}

export async function polymarketCryptoMarkets(limit = 20): Promise<PmResult> {
  const d = await pmGet(`${POLYMARKET_GAMMA}/markets?active=true&closed=false&limit=200` +
    "&order=volume&ascending=false");
  if (isErr(d)) return d;
  if (!Array.isArray(d)) return { error: "unexpected response shape (expected a list)" };
  const out: NormalizedMarket[] = [];
  for (const m of d) {
    const question: string = m.question || m.title || "";
    if (!isCryptoRelevant(question, m.category)) continue;
    const prices = parseJsonField(m.outcomePrices);
    const outcomes = parseJsonField(m.outcomes);
    out.push({
      platform: "polymarket",
      id: m.id,
      question,
      outcomes,
      prices: prices ? prices.map((p) => Number(p)) : null,
      volume: toFloat(m.volume),
      liquidity: toFloat(m.liquidity),
      end_date: m.endDate ?? null,
      url: m.slug ? `https://polymarket.com/event/${m.slug}` : null,
    });
    if (out.length >= limit) break;
  }
  return { ts: nowIso(), count: out.length, markets: out };
}

export async function kalshiCryptoMarkets(limit = 20): Promise<PmResult> {
  const d = await pmGet(`${KALSHI_API}/markets?status=open&limit=200`);
  if (isErr(d)) return d;
  const markets = d && Array.isArray(d.markets) ? d.markets : null;
  if (!markets) return { error: "unexpected response shape (expected a 'markets' list)" };
  const out: NormalizedMarket[] = [];
  for (const m of markets) {
    const title: string = m.title || m.subtitle || "";
    if (!isCryptoRelevant(title)) continue;
    out.push({
      platform: "kalshi",
      id: m.ticker,
      question: title,
      yes_bid_cents: m.yes_bid ?? null,
      yes_ask_cents: m.yes_ask ?? null,
      volume: toFloat(m.volume),
      end_date: m.close_time ?? null,
      url: m.ticker ? `https://kalshi.com/markets/${m.ticker}` : null,
    });
    if (out.length >= limit) break;
  }
  return { ts: nowIso(), count: out.length, markets: out };
}

export async function cryptoPredictionMarkets(limit = 20): Promise<PmResult> {
  const [pm, kl] = await Promise.all([polymarketCryptoMarkets(limit), kalshiCryptoMarkets(limit)]);
  const markets: NormalizedMarket[] = [];
  if (!isErr(pm)) markets.push(...((pm.markets as NormalizedMarket[]) || []));
  if (!isErr(kl)) markets.push(...((kl.markets as NormalizedMarket[]) || []));
  markets.sort((a, b) => (b.volume ?? 0) - (a.volume ?? 0));
  return {
    ts: nowIso(),
    count: markets.length,
    markets: markets.slice(0, limit),
    sources: {
      polymarket: isErr(pm) ? pm.error : "ok",
      kalshi: isErr(kl) ? kl.error : "ok",
    },
  };
}
