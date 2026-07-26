/**
 * TypeScript port of agents/data_fetchers.py::get_base_tvl_and_protocols() +
 * get_base_dex_volume() + the price/fear_greed/global_market portions of
 * build_market_context() + _market_overview_narrative(), matching what
 * agents/acp_fulfill.py::_market_intel() actually returns — kept
 * field-for-field identical so the x402 paid result and the real ACP
 * deliverable never disagree.
 *
 * Real gap this closes (2026-07-26, direct user report against a live $0.07
 * purchase): this used to return only base_tvl/top_protocols(names-only)/
 * prices, with `prices` shipping outright EMPTY in production. Root cause:
 * `{ ethereum: prices?.ethereum?.usd, bitcoin: prices?.bitcoin?.usd }` sets
 * both keys to `undefined` on any CoinGecko failure (network error, rate
 * limit) — and `JSON.stringify()` silently drops `undefined` object values,
 * so the shipped deliverable had a bare `{}` with no error/reason visible
 * anywhere. Fixed with a real fallback (DefiLlama's coins.llama.fi, a
 * second independent free price oracle already used elsewhere in this
 * codebase) instead of letting a transient CoinGecko blip erase the field.
 *
 * The full build_market_context() also correlates hacks/stablecoins/
 * virtuals into anomaly_flags for the daily narrative report
 * (agents/run.py) — that rule-based scan is out of scope for a single paid
 * x402 call, so anomaly_flags is omitted here rather than faked.
 */
import { dexVolumes } from "./defillama";

export interface MarketIntelProtocol {
  name: string;
  tvl_usd: number | null;
  share_of_base_pct: number | null;
  category: string | null;
  change_24h_pct: number | null;
  change_7d_pct: number | null;
}

export interface MarketIntel {
  base_tvl_usd: number | null;
  base_tvl_24h_change_pct: number | null;
  base_tvl_7d_change_pct: number | null;
  dex_volume_24h_usd: number | null;
  top_protocols: MarketIntelProtocol[];
  category_breakdown_pct: Record<string, number> | null;
  concentration_risk: string | null;
  top_gainers_24h: { name: string; change_24h_pct: number }[];
  top_losers_24h: { name: string; change_24h_pct: number }[];
  prices: { ethereum?: number; bitcoin?: number };
  fear_greed: number | null;
  fear_greed_classification: string | null;
  global_market_cap_usd: number | null;
  global_market_cap_change_24h_pct: number | null;
  market_overview: string;
  generated_at: string;
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

interface RawProtocol {
  name: string;
  chains?: string[];
  category?: string;
  chainTvls?: Record<string, number>;
  change_1d?: number;
  change_7d?: number;
}

async function fetchNativePrices(): Promise<{ ethereum?: number; bitcoin?: number }> {
  let cg: CoinGeckoSimplePrice | null = null;
  try {
    cg = await fetch("https://api.coingecko.com/api/v3/simple/price?ids=ethereum,bitcoin&vs_currencies=usd")
      .then(r => (r.ok ? r.json() : null));
  } catch {
    cg = null;
  }
  const haveEth = typeof cg?.ethereum?.usd === "number";
  const haveBtc = typeof cg?.bitcoin?.usd === "number";
  if (haveEth && haveBtc) {
    return { ethereum: cg!.ethereum!.usd, bitcoin: cg!.bitcoin!.usd };
  }
  // Fallback for whichever id(s) CoinGecko didn't answer — DefiLlama's
  // coins.llama.fi, keyed by `coingecko:{id}`, never JSON.stringify-dropped
  // since it only ever contributes real numbers or is skipped entirely.
  let dl: { coins?: Record<string, { price?: number }> } | null = null;
  try {
    dl = await fetch("https://coins.llama.fi/prices/current/coingecko:ethereum,coingecko:bitcoin")
      .then(r => (r.ok ? r.json() : null));
  } catch {
    dl = null;
  }
  const out: { ethereum?: number; bitcoin?: number } = {};
  out.ethereum = haveEth ? cg!.ethereum!.usd : dl?.coins?.["coingecko:ethereum"]?.price;
  out.bitcoin = haveBtc ? cg!.bitcoin!.usd : dl?.coins?.["coingecko:bitcoin"]?.price;
  if (out.ethereum === undefined) delete out.ethereum;
  if (out.bitcoin === undefined) delete out.bitcoin;
  return out;
}

function buildOverviewNarrative(
  tvlUsd: number | null, tvlChangePct: number | null,
  topProtocols: MarketIntelProtocol[], categoryBreakdown: Record<string, number> | null,
  dexVol24h: number | null, fearGreed: number | null, fngClass: string | null,
  globalChangePct: number | null,
): string {
  const parts: string[] = [];
  if (typeof tvlUsd === "number") {
    const chgClause = typeof tvlChangePct === "number"
      ? `, ${tvlChangePct >= 0 ? "up" : "down"} ${Math.abs(tvlChangePct).toFixed(1)}% over 24h`
      : "";
    parts.push(`Base TVL sits at $${tvlUsd.toLocaleString(undefined, { maximumFractionDigits: 0 })}${chgClause}.`);
  }
  if (topProtocols.length && categoryBreakdown && Object.keys(categoryBreakdown).length) {
    const topCat = Object.entries(categoryBreakdown).sort((a, b) => b[1] - a[1])[0];
    const leader = topProtocols[0];
    parts.push(
      `${topCat[0]} leads the ecosystem at ${topCat[1].toFixed(1)}% of TVL, with ${leader.name} alone holding `
      + `${(leader.share_of_base_pct ?? 0).toFixed(1)}% of the chain's total.`
    );
  }
  if (typeof dexVol24h === "number") {
    parts.push(`24h DEX volume on Base is $${dexVol24h.toLocaleString(undefined, { maximumFractionDigits: 0 })}.`);
  }
  if (typeof fearGreed === "number") {
    parts.push(`Macro sentiment reads ${fearGreed} (${fngClass}).`);
  }
  if (typeof globalChangePct === "number") {
    parts.push(`Global crypto market cap is ${globalChangePct >= 0 ? "up" : "down"} ${Math.abs(globalChangePct).toFixed(1)}% over 24h.`);
  }
  return parts.length ? parts.join(" ") : "Insufficient real data this cycle to summarize.";
}

export async function marketIntel(): Promise<MarketIntel> {
  const [chains, protocols, prices, fng, globalMkt, dexVol] = await Promise.all([
    fetch("https://api.llama.fi/v2/chains").then(r => r.json()).catch(() => null) as Promise<any[] | null>,
    fetch("https://api.llama.fi/protocols").then(r => r.json()).catch(() => null) as Promise<RawProtocol[] | null>,
    fetchNativePrices(),
    fetch("https://api.alternative.me/fng/?limit=1").then(r => r.json()).catch(() => null) as Promise<FearGreedResponse | null>,
    fetch("https://api.coingecko.com/api/v3/global").then(r => r.json()).catch(() => null) as Promise<CoinGeckoGlobalResponse | null>,
    dexVolumes("base"),
  ]);

  const base = Array.isArray(chains) ? chains.find((c: any) => String(c.name).toLowerCase() === "base") : null;
  const tvlUsd: number | null = base?.tvl ?? null;

  let topProtocols: MarketIntelProtocol[] = [];
  let categoryBreakdown: Record<string, number> | null = null;
  let concentrationRisk: string | null = null;
  let gainers: { name: string; change_24h_pct: number }[] = [];
  let losers: { name: string; change_24h_pct: number }[] = [];

  if (Array.isArray(protocols)) {
    const baseTvlOf = (p: RawProtocol) => {
      const v = p.chainTvls?.Base;
      return typeof v === "number" ? v : 0;
    };
    const baseProtos = protocols
      .filter(p => (p.chains || []).includes("Base") && p.category !== "CEX" && baseTvlOf(p) > 0)
      .sort((a, b) => baseTvlOf(b) - baseTvlOf(a));

    const sharePct = (v: number) => (tvlUsd ? Math.round((v / tvlUsd) * 10000) / 100 : null);
    const top = baseProtos.slice(0, 10);
    topProtocols = top.slice(0, 5).map(p => ({
      name: p.name, tvl_usd: baseTvlOf(p), share_of_base_pct: sharePct(baseTvlOf(p)),
      category: p.category ?? null,
      change_24h_pct: typeof p.change_1d === "number" ? p.change_1d : null,
      change_7d_pct: typeof p.change_7d === "number" ? p.change_7d : null,
    }));

    const catTotals: Record<string, number> = {};
    for (const p of baseProtos) {
      const cat = p.category || "Other";
      catTotals[cat] = (catTotals[cat] || 0) + baseTvlOf(p);
    }
    if (tvlUsd) {
      categoryBreakdown = Object.fromEntries(
        Object.entries(catTotals)
          .sort((a, b) => b[1] - a[1])
          .map(([cat, v]) => [cat, Math.round((v / tvlUsd) * 10000) / 100])
      );
    }

    const top3Share = top.slice(0, 3).reduce((s, p) => s + (sharePct(baseTvlOf(p)) || 0), 0);
    const level = top3Share >= 60 ? "HIGH" : top3Share >= 40 ? "MEDIUM" : "LOW";
    concentrationRisk = `${level} — top 3 protocols hold ${top3Share.toFixed(1)}% of Base TVL`;

    const movers = top.filter(p => typeof p.change_1d === "number");
    gainers = movers.filter(p => (p.change_1d as number) > 0)
      .sort((a, b) => (b.change_1d as number) - (a.change_1d as number))
      .slice(0, 3).map(p => ({ name: p.name, change_24h_pct: p.change_1d as number }));
    losers = movers.filter(p => (p.change_1d as number) < 0)
      .sort((a, b) => (a.change_1d as number) - (b.change_1d as number))
      .slice(0, 3).map(p => ({ name: p.name, change_24h_pct: p.change_1d as number }));
  }

  const fngRow = fng?.data?.[0];
  const g = globalMkt?.data;
  const fearGreedValue = fngRow?.value != null ? parseInt(fngRow.value, 10) : null;
  const globalChangePct = g?.market_cap_change_percentage_24h_usd != null
    ? Math.round(g.market_cap_change_percentage_24h_usd * 100) / 100 : null;
  const dexVol24h = typeof dexVol.total_vol_24h === "number" ? dexVol.total_vol_24h : null;

  return {
    base_tvl_usd: tvlUsd,
    base_tvl_24h_change_pct: base?.change_1d ?? null,
    base_tvl_7d_change_pct: base?.change_7d ?? null,
    dex_volume_24h_usd: dexVol24h,
    top_protocols: topProtocols,
    category_breakdown_pct: categoryBreakdown,
    concentration_risk: concentrationRisk,
    top_gainers_24h: gainers,
    top_losers_24h: losers,
    prices,
    fear_greed: fearGreedValue,
    fear_greed_classification: fngRow?.value_classification ?? null,
    global_market_cap_usd: g?.total_market_cap?.usd ?? null,
    global_market_cap_change_24h_pct: globalChangePct,
    market_overview: buildOverviewNarrative(
      tvlUsd, base?.change_1d ?? null, topProtocols, categoryBreakdown,
      dexVol24h, fearGreedValue, fngRow?.value_classification ?? null, globalChangePct,
    ),
    generated_at: new Date().toISOString(),
  };
}
