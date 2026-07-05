/**
 * Scoped port of agents/data_fetchers.py::get_base_tvl_and_protocols() +
 * the price/fear_greed/global_market portions of build_market_context(),
 * matching what agents/acp_fulfill.py::_market_intel() actually returns —
 * kept field-for-field identical so the x402 paid result and the real ACP
 * deliverable never disagree. The full build_market_context() also
 * correlates hacks/stablecoins/virtuals into anomaly_flags for the daily
 * narrative report (agents/run.py) — that rule-based scan is out of scope
 * for a single paid x402 call, so anomaly_flags is omitted here rather than
 * faked.
 */
export interface MarketIntel {
  base_tvl: number | null;
  base_tvl_24h_change_pct: number | null;
  top_protocols: string[];
  prices: { ethereum?: number; bitcoin?: number };
  fear_greed: number | null;
  fear_greed_classification: string | null;
  global_market_cap_usd: number | null;
  global_market_cap_change_24h_pct: number | null;
}

interface CoinGeckoSimplePrice {
  ethereum?: { usd: number };
  bitcoin?: { usd: number };
}

interface FearGreedResponse {
  data?: { value?: string; value_classification?: string }[];
}

interface CoinGeckoGlobalResponse {
  data?: {
    total_market_cap?: { usd?: number };
    market_cap_change_percentage_24h_usd?: number;
  };
}

export async function marketIntel(): Promise<MarketIntel> {
  const [chains, protocols, prices, fng, globalMkt] = await Promise.all([
    fetch("https://api.llama.fi/v2/chains").then(r => r.json()).catch(() => null) as Promise<any[] | null>,
    fetch("https://api.llama.fi/protocols").then(r => r.json()).catch(() => null) as Promise<any[] | null>,
    fetch("https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd").then(r => r.json()).catch(() => null) as Promise<CoinGeckoSimplePrice | null>,
    fetch("https://api.alternative.me/fng/?limit=1").then(r => r.json()).catch(() => null) as Promise<FearGreedResponse | null>,
    fetch("https://api.coingecko.com/api/v3/global").then(r => r.json()).catch(() => null) as Promise<CoinGeckoGlobalResponse | null>,
  ]);

  const base = Array.isArray(chains) ? chains.find((c: any) => String(c.name).toLowerCase() === "base") : null;

  let topProtocols: string[] = [];
  if (Array.isArray(protocols)) {
    topProtocols = protocols
      .filter((p: any) => (p.chains || []).includes("Base") && p.category !== "CEX" && (p.chainTvls?.Base || 0) > 0)
      .sort((a: any, b: any) => (b.chainTvls?.Base || 0) - (a.chainTvls?.Base || 0))
      .slice(0, 5)
      .map((p: any) => p.name);
  }

  const fngRow = fng?.data?.[0];
  const g = globalMkt?.data;

  return {
    base_tvl: base?.tvl ?? null,
    base_tvl_24h_change_pct: base?.change_1d ?? null,
    top_protocols: topProtocols,
    prices: { ethereum: prices?.ethereum?.usd, bitcoin: prices?.bitcoin?.usd },
    fear_greed: fngRow?.value != null ? parseInt(fngRow.value, 10) : null,
    fear_greed_classification: fngRow?.value_classification ?? null,
    global_market_cap_usd: g?.total_market_cap?.usd ?? null,
    global_market_cap_change_24h_pct:
      g?.market_cap_change_percentage_24h_usd != null ? Math.round(g.market_cap_change_percentage_24h_usd * 100) / 100 : null,
  };
}
