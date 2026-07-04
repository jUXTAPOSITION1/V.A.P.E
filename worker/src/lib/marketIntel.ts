/**
 * Scoped port of agents/data_fetchers.py::get_base_tvl_and_protocols() +
 * the price portion of build_market_context(), matching what
 * agents/acp_fulfill.py::_market_intel() actually returns (base_tvl,
 * top_protocols, prices). The full build_market_context() also correlates
 * hacks/stablecoins/fear-greed into anomaly_flags for the daily narrative
 * report (agents/run.py) — out of scope for a single paid x402 call.
 */
export interface MarketIntel {
  base_tvl: number | null;
  top_protocols: string[];
  prices: { ethereum?: number; bitcoin?: number };
}

interface CoinGeckoSimplePrice {
  ethereum?: { usd: number };
  bitcoin?: { usd: number };
}

export async function marketIntel(): Promise<MarketIntel> {
  const [chains, protocols, prices] = await Promise.all([
    fetch("https://api.llama.fi/v2/chains").then(r => r.json()).catch(() => null) as Promise<any[] | null>,
    fetch("https://api.llama.fi/protocols").then(r => r.json()).catch(() => null) as Promise<any[] | null>,
    fetch("https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd").then(r => r.json()).catch(() => null) as Promise<CoinGeckoSimplePrice | null>,
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

  return {
    base_tvl: base?.tvl ?? null,
    top_protocols: topProtocols,
    prices: { ethereum: prices?.ethereum?.usd, bitcoin: prices?.bitcoin?.usd },
  };
}
