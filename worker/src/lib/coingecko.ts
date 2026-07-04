/**
 * CoinGecko price reads for Base-chain tokens. Two tiers:
 *  - Current price + 24h change (`getCurrentPrices`): works fully unkeyed
 *    against the public api.coingecko.com — the site's client-side JS
 *    already calls this directly; this worker-side copy exists so the free
 *    /prices route can attach the Demo API key for better rate-limit
 *    headroom than the fully anonymous tier gets.
 *  - Historical price by contract (`getHistoricalPrice`): CoinGecko now
 *    gates this behind at least a free Demo API key — confirmed by testing
 *    it unauthenticated and getting rejected. Only called when
 *    COINGECKO_API_KEY is configured; used for the cost-basis estimate
 *    (lib/costBasis.ts), which is out of reach without a key.
 */
interface CoingeckoEnv {
  COINGECKO_API_KEY?: string;
}

function authHeaders(env: CoingeckoEnv): Record<string, string> {
  return env.COINGECKO_API_KEY ? { "x-cg-demo-api-key": env.COINGECKO_API_KEY } : {};
}

export interface CoingeckoPriceEntry {
  usd?: number;
  usd_24h_change?: number;
}

/** Current USD price + 24h change for a batch of Base contract addresses. */
export async function getCurrentPrices(env: CoingeckoEnv, addresses: string[]): Promise<Record<string, CoingeckoPriceEntry>> {
  if (!addresses.length) return {};
  const url = `https://api.coingecko.com/api/v3/simple/token_price/base?contract_addresses=${addresses.join(",")}&vs_currencies=usd&include_24hr_change=true`;
  const res = await fetch(url, { headers: authHeaders(env) });
  if (!res.ok) throw new Error(`CoinGecko HTTP ${res.status}`);
  return res.json();
}

/**
 * Best-effort USD price of `contractAddress` at `unixSeconds`, picking the
 * closest sample CoinGecko has within a ±1 day window. Returns null (not
 * throws) if there's no key configured or no data in range — callers treat
 * that as "cost basis unavailable for this token" rather than a hard error.
 */
export async function getHistoricalPrice(env: CoingeckoEnv, contractAddress: string, unixSeconds: number): Promise<number | null> {
  if (!env.COINGECKO_API_KEY) return null;
  const from = unixSeconds - 43200;
  const to = unixSeconds + 43200;
  const url = `https://api.coingecko.com/api/v3/coins/base/contract/${contractAddress}/market_chart/range?vs_currency=usd&from=${from}&to=${to}`;
  const res = await fetch(url, { headers: authHeaders(env) });
  if (!res.ok) return null;
  const data = (await res.json()) as { prices?: [number, number][] };
  const prices = data.prices || [];
  if (!prices.length) return null;
  const targetMs = unixSeconds * 1000;
  let closest = prices[0];
  for (const p of prices) {
    if (Math.abs(p[0] - targetMs) < Math.abs(closest[0] - targetMs)) closest = p;
  }
  return closest[1];
}
