/**
 * TypeScript port of agents/defillama.py — VAPE's DefiLlama data layer, made
 * available to the x402 market-data tool tier.
 *
 * Field-for-field faithful to the Python module so the x402 result, the ACP
 * deliverable, and any Python-side investigation never disagree. Same design
 * law: every function returns real data or an `{ error }` object and NEVER
 * throws — a caller (and the payment middleware) can always degrade honestly.
 *
 * Per-route HTTP caching is handled by Hono's `cache` middleware in index.ts
 * (Cloudflare Cache API), so this layer is a thin fetch+parse — it does not
 * re-implement the Python disk cache.
 *
 * Hosts: api.llama.fi, coins.llama.fi, yields.llama.fi, stablecoins.llama.fi,
 * bridges.llama.fi.
 */
const API = "https://api.llama.fi";
const COINS = "https://coins.llama.fi";
const YIELDS = "https://yields.llama.fi";
const STABLE = "https://stablecoins.llama.fi";
const BRIDGES = "https://bridges.llama.fi";

const UA = "VAPE/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)";

export type DlResult = Record<string, unknown> & { error?: string };

function nowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function isErr(x: unknown): x is { error: string } {
  return Boolean(x && typeof x === "object" && (x as Record<string, unknown>).error);
}

// Mirrors data_fetchers._get's contract: real JSON, or {error} — never throws.
// `any` return since DefiLlama endpoints legitimately return both arrays and
// objects; each caller narrows what it needs.
async function dlGet(url: string): Promise<any> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
    if (!r.ok) return { error: `HTTP ${r.status}`, url };
    return await r.json();
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e), url };
  }
}

function coinKey(chain: string | number, address: string): string {
  return `${String(chain).toLowerCase()}:${String(address).toLowerCase()}`;
}

// ── Prices — the multichain oracle (coins.llama.fi) ──────────────────────────
export async function tokenPrice(chain: string, address: string): Promise<DlResult> {
  const cid = coinKey(chain, address);
  const d = await dlGet(`${COINS}/prices/current/${encodeURIComponent(cid)}`);
  if (isErr(d)) return d;
  const coin = (d.coins || {})[cid];
  if (!coin) return { error: "no price on DefiLlama", coin: cid };
  return { ts: nowIso(), chain, address, ...coin };
}

export async function tokenFirstPrice(chain: string, address: string): Promise<DlResult> {
  const cid = coinKey(chain, address);
  const d = await dlGet(`${COINS}/prices/first/${encodeURIComponent(cid)}`);
  if (isErr(d)) return d;
  const coin = (d.coins || {})[cid];
  if (!coin) return { error: "no first-price on DefiLlama", coin: cid };
  const ts = coin.timestamp;
  const out: DlResult = { ts: nowIso(), chain, address, ...coin };
  if (typeof ts === "number") {
    out.first_seen_iso = new Date(ts * 1000).toISOString().replace(/\.\d{3}Z$/, "Z");
    out.age_days = Math.round(((Date.now() / 1000 - ts) / 86400) * 10) / 10;
  }
  return out;
}

export async function tokenPriceChart(chain: string, address: string, spanDays = 30): Promise<DlResult> {
  const cid = coinKey(chain, address);
  const start = Math.floor(Date.now() / 1000 - spanDays * 86400);
  const url = `${COINS}/chart/${encodeURIComponent(cid)}?start=${start}&span=${spanDays}&period=1d`;
  const d = await dlGet(url);
  if (isErr(d)) return d;
  const coin = (d.coins || {})[cid] || {};
  return { ts: nowIso(), chain, address, symbol: coin.symbol, prices: coin.prices || [] };
}

// ── TVL / protocols / chains (api.llama.fi) ──────────────────────────────────
export async function protocol(slug: string): Promise<DlResult> {
  const d = await dlGet(`${API}/protocol/${encodeURIComponent(slug)}`);
  if (isErr(d)) return d;
  return {
    ts: nowIso(), slug, name: d.name, logo: d.logo, category: d.category, url: d.url,
    chains: d.chains, tvl: d.currentChainTvls || {}, audits: d.audits, audit_links: d.audit_links,
    twitter: d.twitter, description: d.description,
  };
}

export async function protocolsOnChain(chain = "Base", topN = 20): Promise<DlResult> {
  const d = await dlGet(`${API}/protocols`);
  if (isErr(d)) return d;
  const rows: Record<string, unknown>[] = [];
  for (const p of Array.isArray(d) ? d : []) {
    const ctvl = (p.chainTvls || {})[chain];
    if (!ctvl || ctvl <= 0) continue;
    rows.push({
      name: p.name, slug: p.slug, logo: p.logo, category: p.category, tvl_usd: ctvl,
      change_1d: p.change_1d, change_7d: p.change_7d,
    });
  }
  rows.sort((a, b) => ((b.tvl_usd as number) || 0) - ((a.tvl_usd as number) || 0));
  return { ts: nowIso(), chain, count: rows.length, protocols: rows.slice(0, topN) };
}

export async function chainOverview(chain = "Base"): Promise<DlResult> {
  const d = await dlGet(`${API}/v2/chains`);
  if (isErr(d)) return d;
  const chains = (Array.isArray(d) ? d.filter((c: any) => c && typeof c === "object") : [])
    .sort((a: any, b: any) => (b.tvl || 0) - (a.tvl || 0));
  for (let i = 0; i < chains.length; i++) {
    const c = chains[i];
    if (String(c.name || "").toLowerCase() === chain.toLowerCase()) {
      return {
        ts: nowIso(), chain: c.name, tvl_usd: c.tvl, rank: i + 1, total_chains: chains.length,
        token_symbol: c.tokenSymbol, gecko_id: c.gecko_id,
      };
    }
  }
  return { error: `chain not found: ${chain}` };
}

// ── Fees & revenue (api.llama.fi/overview + /summary) ────────────────────────
export async function protocolFees(slug: string): Promise<DlResult> {
  const d = await dlGet(`${API}/summary/fees/${encodeURIComponent(slug)}?dataType=dailyFees`);
  if (isErr(d)) return d;
  const rev = await dlGet(`${API}/summary/fees/${encodeURIComponent(slug)}?dataType=dailyRevenue`);
  const out: DlResult = {
    ts: nowIso(), slug, name: d.name, logo: d.logo,
    fees_24h: d.total24h, fees_7d: d.total7d, fees_30d: d.total30d,
  };
  if (!isErr(rev)) {
    out.revenue_24h = rev.total24h;
    out.revenue_7d = rev.total7d;
    out.revenue_30d = rev.total30d;
  }
  return out;
}

export async function chainFees(chain = "base"): Promise<DlResult> {
  const url = `${API}/overview/fees/${encodeURIComponent(chain)}`
    + `?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true`;
  const d = await dlGet(url);
  if (isErr(d)) return d;
  const protos = (d.protocols || []).map((p: any) => ({
    name: p.name, logo: p.logo, category: p.category, fees_24h: p.total24h, fees_7d: p.total7d,
  }));
  protos.sort((a: any, b: any) => (b.fees_24h || 0) - (a.fees_24h || 0));
  return { ts: nowIso(), chain, total_fees_24h: d.total24h, total_fees_7d: d.total7d, protocols: protos.slice(0, 20) };
}

export async function dexVolumes(chain = "base"): Promise<DlResult> {
  const url = `${API}/overview/dexs/${encodeURIComponent(chain)}`
    + `?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true`;
  const d = await dlGet(url);
  if (isErr(d)) return d;
  const protos = (d.protocols || []).map((p: any) => ({
    name: p.name, logo: p.logo, vol_24h: p.total24h, vol_7d: p.total7d,
  }));
  protos.sort((a: any, b: any) => (b.vol_24h || 0) - (a.vol_24h || 0));
  return { ts: nowIso(), chain, total_vol_24h: d.total24h, dexs: protos.slice(0, 20) };
}

export async function derivativesVolumes(): Promise<DlResult> {
  const url = `${API}/overview/derivatives?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true`;
  const d = await dlGet(url);
  if (isErr(d)) return d;
  const protos = (d.protocols || []).map((p: any) => ({
    name: p.name, logo: p.logo, vol_24h: p.total24h, vol_7d: p.total7d,
  }));
  protos.sort((a: any, b: any) => (b.vol_24h || 0) - (a.vol_24h || 0));
  return { ts: nowIso(), total_vol_24h: d.total24h, venues: protos.slice(0, 20) };
}

// ── Yields (yields.llama.fi) ─────────────────────────────────────────────────
export interface YieldFilter {
  chain?: string;
  project?: string;
  symbol?: string;
  minTvl?: number;
  limit?: number;
}

export async function yieldPools(f: YieldFilter = {}): Promise<DlResult> {
  const { chain, project, symbol, minTvl = 10000, limit = 25 } = f;
  const d = await dlGet(`${YIELDS}/pools`);
  if (isErr(d)) return d;
  const rows: Record<string, unknown>[] = [];
  for (const p of d.data || []) {
    if (chain && String(p.chain || "").toLowerCase() !== chain.toLowerCase()) continue;
    if (project && !String(p.project || "").toLowerCase().includes(project.toLowerCase())) continue;
    if (symbol && !String(p.symbol || "").toLowerCase().includes(symbol.toLowerCase())) continue;
    if ((p.tvlUsd || 0) < minTvl) continue;
    rows.push({
      pool: p.pool, chain: p.chain, project: p.project, symbol: p.symbol, tvl_usd: p.tvlUsd,
      apy: p.apy, apy_base: p.apyBase, apy_reward: p.apyReward, il_risk: p.ilRisk,
      exposure: p.exposure, stablecoin: p.stablecoin,
    });
  }
  rows.sort((a, b) => ((b.tvl_usd as number) || 0) - ((a.tvl_usd as number) || 0));
  return { ts: nowIso(), count: rows.length, pools: rows.slice(0, limit) };
}

// ── Stablecoins (stablecoins.llama.fi) ───────────────────────────────────────
export async function stablecoins(minMcap = 1e8, limit = 25): Promise<DlResult> {
  const d = await dlGet(`${STABLE}/stablecoins?includePrices=true`);
  if (isErr(d)) return d;
  const rows: Record<string, unknown>[] = [];
  for (const s of d.peggedAssets || []) {
    const circ = ((s.circulating || {}).peggedUSD) || 0;
    if (circ < minMcap) continue;
    const price = s.price;
    const depeg = typeof price === "number" ? Math.round(Math.abs(price - 1.0) * 10000) / 10000 : null;
    rows.push({
      name: s.name, symbol: s.symbol, circulating_usd: circ, price, depeg,
      peg_type: s.pegType, mechanism: s.pegMechanism,
    });
  }
  rows.sort((a, b) => ((b.circulating_usd as number) || 0) - ((a.circulating_usd as number) || 0));
  return { ts: nowIso(), count: rows.length, stablecoins: rows.slice(0, limit) };
}

// ── Bridges (bridges.llama.fi) — feeds threat work ───────────────────────────
export async function bridges(limit = 25): Promise<DlResult> {
  const d = await dlGet(`${BRIDGES}/bridges?includeChains=true`);
  if (isErr(d)) return d;
  const rows = (d.bridges || []).map((b: any) => ({
    id: b.id, name: b.displayName || b.name, chains: b.chains,
    last_daily_volume: b.lastDailyVolume, weekly_volume: b.weeklyVolume,
  }));
  rows.sort((a: any, b: any) => (b.last_daily_volume || 0) - (a.last_daily_volume || 0));
  return { ts: nowIso(), count: rows.length, bridges: rows.slice(0, limit) };
}

export async function bridgeVolume(chain = "Base"): Promise<DlResult> {
  const d = await dlGet(`${BRIDGES}/bridgevolume/${encodeURIComponent(chain)}`);
  if (isErr(d)) return d;
  const series = Array.isArray(d) ? d : [];
  const latest = series.length ? series[series.length - 1] : {};
  return {
    ts: nowIso(), chain, latest_deposit_usd: latest.depositUSD,
    latest_withdraw_usd: latest.withdrawUSD, days: series.length,
  };
}

// ── Unlocks / emissions (api.llama.fi) ───────────────────────────────────────
export async function unlocks(slug: string): Promise<DlResult> {
  const d = await dlGet(`${API}/emission/${encodeURIComponent(slug)}`);
  if (isErr(d)) return d;
  const events = d.events || d.unlocks || [];
  const now = Date.now() / 1000;
  let upcoming: Record<string, unknown> | null = null;
  let bestTs: number | null = null;
  // Keep the EARLIEST future event — `events` isn't guaranteed sorted, so
  // stopping at the first future item can surface a later unlock than the next.
  for (const e of events) {
    const ts = e.timestamp ?? e.date;
    if (typeof ts === "number" && ts > now && (bestTs === null || ts < bestTs)) {
      bestTs = ts;
      upcoming = {
        timestamp: ts, in_days: Math.round(((ts - now) / 86400) * 10) / 10,
        description: e.description || e.category, amount: e.noOfTokens ?? e.amount,
      };
    }
  }
  return { ts: nowIso(), slug, name: d.name, next_unlock: upcoming, tracked_events: events.length };
}

// ── Treasury (api.llama.fi) ──────────────────────────────────────────────────
export async function treasury(slug: string): Promise<DlResult> {
  const d = await dlGet(`${API}/treasury/${encodeURIComponent(slug)}`);
  if (isErr(d)) return d;
  const tvls = d.currentChainTvls || {};
  const own = tvls.OwnTokens || tvls.ownTokens || 0;
  // currentChainTvls mixes per-chain totals (already inclusive of own tokens)
  // with own-token breakdowns — an aggregate OwnTokens + per-chain
  // <chain>-OwnTokens. Sum only the plain per-chain totals so treasury_usd /
  // own_token_share aren't double-counted.
  let total = 0;
  for (const [k, v] of Object.entries(tvls)) {
    if (typeof v === "number" && k !== "OwnTokens" && k !== "ownTokens" && !k.endsWith("-OwnTokens")) total += v;
  }
  return {
    ts: nowIso(), slug, name: d.name, treasury_usd: Math.round(total * 100) / 100,
    own_token_usd: Math.round(own * 100) / 100,
    own_token_share: total ? Math.round((own / total) * 1000) / 1000 : null,
  };
}

// ── Convenience: everything DefiLlama knows about one token ───────────────────
export async function tokenIntel(chain: string, address: string, protocolSlug?: string): Promise<DlResult> {
  const out: DlResult = { ts: nowIso(), chain, address };
  const [price, first] = await Promise.all([tokenPrice(chain, address), tokenFirstPrice(chain, address)]);
  out.price = isErr(price) ? null : price;
  out.first_price = isErr(first) ? null : first;
  if (protocolSlug) {
    const [fees, unlk, treas] = await Promise.all([
      protocolFees(protocolSlug), unlocks(protocolSlug), treasury(protocolSlug),
    ]);
    out.fees = isErr(fees) ? null : fees;
    out.unlocks = isErr(unlk) ? null : unlk;
    out.treasury = isErr(treas) ? null : treas;
  }
  return out;
}
