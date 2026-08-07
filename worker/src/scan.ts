/**
 * VAPE token scan — TypeScript port of agents/token_scan.py::scan().
 *
 * Field-for-field mirror: same GoPlus token_security + DexScreener liquidity
 * calls, same flag thresholds, same PROCEED/CAUTION/REJECT verdict logic.
 * This is the single source of truth for the "auto" x402 offerings, the free
 * browser preview (docs/assets/app.js `App.hunt()`), and — indirectly, via
 * agents/token_scan.py — the real ACP deliverables. A CI check (see
 * .github/workflows/scan-parity.yml) runs the Python, this, and the browser
 * version against one fixed address and fails the build if verdicts diverge.
 */

const UA = { "User-Agent": "VAPE-PrivateEye/1.0 (+https://github.com/jUXTAPOSITION1/V.A.P.E)" };

// DexScreener fronts its API through Cloudflare, and its anti-bot layer
// occasionally rate-limits datacenter egress (Workers included) with an HTML
// block page (Cloudflare "error code: 1015") instead of a 429 — reading that
// as JSON throws a raw "Unexpected token '<'..." parser exception, which used
// to leak straight into a paying customer's report as `data_error`. GoPlus
// is rock-solid by comparison, so DexScreener is the one worth retrying.
// Same 7 chains as agents/token_scan.py's GECKOTERMINAL_NETWORK (and
// docs/assets/app.js's _GECKOTERMINAL_NETWORK) -- kept in sync across all
// three per this file's own scan-parity CI check. Real gap this closes:
// this used to stop at 3 of the 7 EVM chains VAPE otherwise tracks.
const GECKOTERMINAL_NETWORK: Record<number, string> = {
  8453: "base", 1: "eth", 42161: "arbitrum", 10: "optimism",
  137: "polygon_pos", 56: "bsc", 43114: "avax",
};

export interface ScanResult {
  ts: string;
  chain_id: number;
  address: string;
  name: string | null;
  symbol: string | null;
  verdict: "PROCEED" | "CAUTION" | "REJECT";
  flags: string[];
  holder_count: string | null;
  lp_holder_count: string | null;
  liquidity_usd: number;
  pair_created_ms: number | null;
  has_declared_socials: boolean;
  is_honeypot: string | null;
  buy_tax: string | null;
  sell_tax: string | null;
  owner_address: string | null;
  top_pair_dex: string | null;
  source: string;
  liquidity_source?: string;
  data_error?: string | null;
  error?: string;
}

// Hard-reject GoPlus fields — same tier as honeypot, not just an advisory
// flag. Real, documented GoPlus token_security fields, flat "0"/"1" strings
// like their siblings (is_mintable, is_proxy, etc.) already used below.
// Kept in its own list so agents/token_scan.py / docs/assets/app.js stay
// field-for-field identical.
const HARD_REJECT_FIELDS = ["is_blacklisted", "selfdestruct", "is_airdrop_scam"] as const;

// Addresses whose held balance is permanently removed from circulation —
// excluded from concentration math or a healthy burn/deflationary mechanism
// would flag as a whale-risk false positive. Mirrors
// agents/token_scan.py::BURN_ADDRESSES. Kept in its own constant so
// agents/token_scan.py / docs/assets/app.js port identically.
const BURN_ADDRESSES = new Set([
  "0x0000000000000000000000000000000000000000",
  "0x000000000000000000000000000000000000dead",
]);

// Real top-holder concentration + LP-lock status from GoPlus's own
// per-holder "holders"/"lp_holders" arrays — already inside the SAME `gp`
// object this scan() already fetches (keyless, no new API call), but never
// read; only the scalar holder_count/lp_holder_count were. Field-for-field
// port of agents/token_scan.py::_top_holder_concentration_pct()/
// _lp_locked_pct() — see those functions' docstrings for the full context
// and the schema-uncertainty caveat that also applies here.
function topHolderConcentrationPct(gp: Record<string, any>): number | null {
  const holders = gp?.holders;
  if (!Array.isArray(holders) || holders.length === 0) return null;
  let total = 0;
  let counted = 0;
  for (const h of holders.slice(0, 10)) {
    if (!h || typeof h !== "object") continue;
    const addr = String(h.address || "").toLowerCase();
    if (BURN_ADDRESSES.has(addr)) continue;
    const tag = String(h.tag || "").toLowerCase();
    if (tag.includes("lp") || tag.includes("pool") || tag.includes("burn")) continue;
    let pct = Number(h.percent);
    if (!Number.isFinite(pct)) continue;
    if (pct > 1) pct /= 100;
    total += pct;
    counted += 1;
  }
  if (counted === 0) return null;
  return total * 100;
}

function lpLockedPct(gp: Record<string, any>): number | null {
  const lpHolders = gp?.lp_holders;
  if (!Array.isArray(lpHolders) || lpHolders.length === 0) return null;
  let total = 0;
  let locked = 0;
  let counted = 0;
  for (const h of lpHolders) {
    if (!h || typeof h !== "object") continue;
    let pct = Number(h.percent);
    if (!Number.isFinite(pct)) continue;
    if (pct > 1) pct /= 100;
    total += pct;
    if (String(h.is_locked) === "1") locked += pct;
    counted += 1;
  }
  if (counted === 0 || total <= 0) return null;
  return (locked / total) * 100;
}

async function safeGet(url: string, retries = 1): Promise<any> {
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await fetch(url, { headers: UA });
      if (!r.ok) {
        // A non-2xx here (Cloudflare block/rate-limit pages included) is
        // HTML/plain-text, not JSON — never hand that to r.json(), which
        // would throw an opaque parser exception instead of a clean status.
        if (attempt < retries && (r.status === 429 || r.status === 403 || r.status >= 500)) {
          await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
          continue;
        }
        return { _error: `upstream returned HTTP ${r.status}` };
      }
      return await r.json();
    } catch (e: any) {
      if (attempt < retries) {
        await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
        continue;
      }
      // Covers both network failures and a 2xx response whose body still
      // isn't valid JSON — same clean-message treatment either way.
      return { _error: "upstream request failed or returned invalid data" };
    }
  }
}

interface LiquidityFallback {
  liquidity_usd: number;
  top_pair_dex: string | null;
  pair_created_ms: number | null;
  source: string;
}

// Used only when DexScreener fails outright (see safeGet above) — GoPlus
// alone still tells the customer everything about token *security*, but
// liquidity_check/token_safety_check would otherwise report $0 liquidity for
// a token that may have plenty, which is actively misleading rather than
// just incomplete. GeckoTerminal is already a real, keyless source used
// elsewhere in this repo (agents/data_fetchers.py's Base-movers feed).
async function fetchLiquidityFallback(addr: string, chainId: number): Promise<LiquidityFallback | null> {
  const network = GECKOTERMINAL_NETWORK[chainId];
  if (!network) return null;
  const data = await safeGet(`https://api.geckoterminal.com/api/v2/networks/${network}/tokens/${addr}/pools`, 0);
  const pools: any[] = Array.isArray(data?.data) ? data.data : [];
  if (!pools.length) return null;
  const liquidityUsd = pools.reduce((s, p) => s + (parseFloat(p?.attributes?.reserve_in_usd) || 0), 0);
  const createdTimes = pools
    .map((p) => p?.attributes?.pool_created_at ? Date.parse(p.attributes.pool_created_at) : NaN)
    .filter((t) => !Number.isNaN(t));
  return {
    liquidity_usd: Math.round(liquidityUsd * 100) / 100,
    top_pair_dex: pools[0]?.relationships?.dex?.data?.id ?? null,
    pair_created_ms: createdTimes.length ? Math.min(...createdTimes) : null,
    source: "geckoterminal",
  };
}

function toFloat(x: unknown): number | null {
  const n = typeof x === "string" ? parseFloat(x) : (x as number);
  return Number.isFinite(n) ? n : null;
}

export async function scan(address: string, chainId = 8453): Promise<ScanResult> {
  const addr = address.trim();
  if (!/^0x[a-fA-F0-9]{40}$/.test(addr)) {
    return { error: "invalid_address", address: addr } as unknown as ScanResult;
  }

  // GoPlus is the sole source for security fields (mintable/honeypot/owner/
  // taxes) — unlike DexScreener there's no GeckoTerminal-style fallback, so
  // a 429 here is worth extra retries rather than giving up after one.
  const [gpRaw, dsRaw] = await Promise.all([
    safeGet(`https://api.gopluslabs.io/api/v1/token_security/${chainId}?contract_addresses=${addr}`, 3),
    safeGet(`https://api.dexscreener.com/latest/dex/tokens/${addr}`),
  ]);

  let gp: Record<string, any> = {};
  if (gpRaw && typeof gpRaw === "object" && gpRaw.result) {
    const vals = Object.values(gpRaw.result as Record<string, any>);
    gp = (vals[0] as Record<string, any>) || {};
  }

  const pairs: any[] = (dsRaw && typeof dsRaw === "object" && Array.isArray(dsRaw.pairs)) ? dsRaw.pairs : [];
  let liquidityUsd = Math.round(pairs.reduce((s, p) => s + ((p.liquidity || {}).usd || 0), 0) * 100) / 100;
  // Oldest pair creation timestamp across all pairs — a token's real track
  // record starts at its FIRST pair, not whichever pair happens deepest now.
  const pairCreatedTimes = pairs.map((p) => p.pairCreatedAt).filter((t) => !!t);
  let pairCreatedMs = pairCreatedTimes.length ? Math.min(...pairCreatedTimes) : null;
  const hasSocials = pairs.some((p) => (p.info?.socials?.length ?? 0) > 0 || (p.info?.websites?.length ?? 0) > 0);
  let topPairDex: string | null = pairs[0]?.dexId ?? null;
  let liquiditySource = "dexscreener";

  // DexScreener failed outright (not just "no pairs found") — GoPlus alone
  // would otherwise report $0 liquidity for a token that may have plenty,
  // which is misleading rather than merely incomplete for a paying customer.
  if (dsRaw?._error && !pairs.length) {
    const fallback = await fetchLiquidityFallback(addr, chainId);
    if (fallback) {
      liquidityUsd = fallback.liquidity_usd;
      pairCreatedMs = fallback.pair_created_ms;
      topPairDex = fallback.top_pair_dex;
      liquiditySource = fallback.source;
    }
  }

  const flags: string[] = [];
  if (gp.is_honeypot === "1") flags.push("HONEYPOT");
  const buyTax = toFloat(gp.buy_tax) || 0;
  if (buyTax > 0.10) flags.push(`buy_tax ${(buyTax * 100).toFixed(0)}%`);
  const sellTax = toFloat(gp.sell_tax) || 0;
  if (sellTax > 0.10) flags.push(`sell_tax ${(sellTax * 100).toFixed(0)}%`);
  if (gp.is_mintable === "1") flags.push("mintable");
  const owner: string = gp.owner_address || "";
  if (owner && owner !== "0x0000000000000000000000000000000000000000") flags.push("owner_not_renounced");
  if (gp.is_proxy === "1") flags.push("proxy");
  if (liquidityUsd > 0 && liquidityUsd < 10000) flags.push("low_liquidity");
  if (gp.cannot_sell_all === "1") flags.push("cannot_sell_all");
  if (gp.transfer_pausable === "1") flags.push("transfer_pausable");
  for (const field of HARD_REJECT_FIELDS) {
    if (gp[field] === "1") flags.push(field);
  }
  const lpHolders = gp.lp_holder_count != null && gp.lp_holder_count !== "" ? parseInt(gp.lp_holder_count, 10) : null;
  if (lpHolders !== null && !Number.isNaN(lpHolders) && lpHolders <= 1) flags.push("lp_concentrated");
  const holders = gp.holder_count != null && gp.holder_count !== "" ? parseInt(gp.holder_count, 10) : null;
  if (holders !== null && !Number.isNaN(holders) && holders < 50) flags.push("low_holder_count");
  if (pairCreatedMs && (Date.now() - pairCreatedMs) / 86400000 < 3) flags.push("fresh_launch");
  if (!hasSocials) flags.push("no_declared_socials");

  // Real top-holder concentration + LP-lock status — see
  // topHolderConcentrationPct()/lpLockedPct()'s docstrings. Kept as
  // separate, more informative flags alongside the cruder scalar-count
  // checks above (lp_concentrated/low_holder_count), not a replacement.
  const topHolderPct = topHolderConcentrationPct(gp);
  if (topHolderPct !== null && topHolderPct >= 70) flags.push(`concentrated_holders_${topHolderPct.toFixed(0)}pct`);
  const lpLocked = lpLockedPct(gp);
  if (lpLocked !== null && lpLocked < 50) flags.push(`lp_mostly_unlocked_${lpLocked.toFixed(0)}pct`);

  const hardReject = gp.is_honeypot === "1" || HARD_REJECT_FIELDS.some((field) => gp[field] === "1");
  let verdict: ScanResult["verdict"];
  if (hardReject) verdict = "REJECT";
  else if (flags.length >= 2) verdict = "CAUTION";
  else verdict = "PROCEED";

  return {
    ts: new Date().toISOString().replace(/\.\d+Z$/, "Z"),
    chain_id: chainId,
    address: addr,
    name: gp.token_name ?? null,
    symbol: gp.token_symbol ?? null,
    verdict,
    flags,
    holder_count: gp.holder_count ?? null,
    lp_holder_count: gp.lp_holder_count ?? null,
    liquidity_usd: liquidityUsd,
    pair_created_ms: pairCreatedMs,
    has_declared_socials: hasSocials,
    is_honeypot: gp.is_honeypot ?? null,
    buy_tax: gp.buy_tax ?? null,
    sell_tax: gp.sell_tax ?? null,
    owner_address: owner || null,
    top_pair_dex: topPairDex,
    source: "goplus+dexscreener",
    liquidity_source: liquiditySource,
    data_error: gpRaw?._error
      ? gpRaw._error
      : dsRaw?._error
        ? (liquiditySource === "geckoterminal" ? `dexscreener unavailable (${dsRaw._error}) — liquidity from GeckoTerminal instead` : dsRaw._error)
        : null,
  };
}
