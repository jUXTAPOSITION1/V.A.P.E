/**
 * TypeScript port of agents/investigate.py's real heuristic engine — the
 * same CertiK-style weighted score(), meme-factory-template detection, and
 * recent-hack correlation every FREE VAPE investigation runs, now reachable
 * from the paid dossier_check x402 route. Field-for-field port of the
 * scoring rubric (same weights, same thresholds, same messages) so the ACP
 * and x402 versions of dossier_check never disagree on a verdict — same
 * parity guarantee this repo already holds for token_scan.py/scan.ts.
 *
 * Deliberately does NOT persist anything (no report file, no ledger, no
 * memory/catalog) — this mirrors agents/investigate.py::quick_assess(),
 * not investigate(), since a paying customer's on-demand call has no
 * business writing to VAPE's own free investigation records.
 */
import { webSearch, webScrape, type ResearchEnv } from "./webResearch";
import { getContractMarketData, type CoingeckoContractMarket } from "./coingecko";

const UA = { "User-Agent": "VAPE-PrivateEye/1.0" };
const BASE_RPC = "https://mainnet.base.org";

// CoinGecko's own "asset platform" id per chain — a distinct slug family
// from GeckoTerminal's network id or DexScreener's chainId. Mirrors
// agents/investigate.py::COINGECKO_PLATFORM.
export const COINGECKO_PLATFORM: Record<number, string> = {
  8453: "base", 1: "ethereum", 42161: "arbitrum-one", 10: "optimistic-ethereum",
  137: "polygon-pos", 56: "binance-smart-chain", 43114: "avalanche",
};

async function safeGetJson(url: string, retries = 0): Promise<any> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(url, { headers: UA });
      if (!r.ok) {
        if (attempt < retries && (r.status === 429 || r.status === 403 || r.status >= 500)) {
          await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
          continue;
        }
        return {};
      }
      return await r.json();
    } catch {
      if (attempt < retries) {
        await new Promise((res) => setTimeout(res, 400 * (attempt + 1)));
        continue;
      }
      return {};
    }
  }
  return {};
}

/** Raw GoPlus token_security fields — deliberately the FULL raw dict (unlike
 * scan.ts's scan(), which only keeps derived flags), since score() below
 * needs individual raw traits (hidden_owner, can_take_back_ownership, etc.)
 * scan.ts never surfaces. GoPlus is the sole source for these traits (no
 * fallback), so a 429 gets extra retries same as scan.ts's safeGet. */
export async function goplusRaw(address: string, chainId: number): Promise<Record<string, any>> {
  const data = await safeGetJson(`https://api.gopluslabs.io/api/v1/token_security/${chainId}?contract_addresses=${address}`, 3);
  const result = data?.result;
  if (!result) return {};
  const vals = Object.values(result as Record<string, any>);
  return (vals[0] as Record<string, any>) || {};
}

export interface DexInfo {
  symbol?: string; name?: string; price_usd?: string; liquidity_usd?: number;
  vol_24h_usd?: number; change_24h_pct?: number; pair_created_ms?: number; dex?: string;
  socials: Array<{ type?: string; url?: string }>;
  websites: Array<{ url?: string }>;
}

export async function dexscreenerFull(address: string): Promise<DexInfo> {
  const data = await safeGetJson(`https://api.dexscreener.com/latest/dex/tokens/${address}`);
  const pairs: any[] = Array.isArray(data?.pairs) ? data.pairs : [];
  if (!pairs.length) return { socials: [], websites: [] };
  const p = pairs.reduce((best, cur) =>
    ((cur.liquidity?.usd || 0) > (best.liquidity?.usd || 0) ? cur : best), pairs[0]);
  const info = p.info || {};
  return {
    symbol: p.baseToken?.symbol, name: p.baseToken?.name, price_usd: p.priceUsd,
    liquidity_usd: p.liquidity?.usd, vol_24h_usd: p.volume?.h24, change_24h_pct: p.priceChange?.h24,
    pair_created_ms: p.pairCreatedAt, dex: p.dexId,
    socials: (info.socials || []).filter((s: any) => s.url).map((s: any) => ({ type: s.type, url: s.url })),
    websites: (info.websites || []).filter((w: any) => w.url).map((w: any) => ({ url: w.url })),
  };
}

// Real, confirmed bug this fixes (2026-07-25 — same root cause pinned in
// agents/investigate.py::onchain_presence()'s Python twin, from a live
// report that mislabeled the real, heavily-traded VIRTUAL token contract
// as a codeless EOA): a single failed/erroring RPC call — timeout, rate
// limit, malformed response — used to fall through to `is_contract: false`
// with zero retries, indistinguishable from a real, confirmed empty
// eth_getCode response. Now retried, and a still-failing call reports an
// honest is_contract=null ("unknown") rather than a fabricated false —
// score()'s own `onchain.is_contract === false` check below already uses
// strict equality, so null correctly never triggers the "no contract code"
// penalty.
export async function onchainPresence(
  address: string,
): Promise<{ is_contract: boolean | null; code_size_bytes: number | null; error?: string }> {
  let lastErr = "RPC call failed";
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(BASE_RPC, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...UA },
        body: JSON.stringify({ jsonrpc: "2.0", method: "eth_getCode", params: [address, "latest"], id: 1 }),
        // Real gap this closes (CodeRabbit, PR #277): with no timeout, a
        // single hanging RPC could block this whole 3-attempt retry loop
        // for however long the platform's own outer request timeout allows
        // — AbortSignal.timeout() is a standard Worker-supported API, so a
        // stuck attempt now fails fast into the existing catch/retry path
        // instead of exhausting the request budget on one hung call.
        signal: AbortSignal.timeout(8000),
      });
      const data: any = await res.json();
      if (typeof data?.result === "string") {
        const code: string = data.result;
        return { is_contract: Boolean(code && code !== "0x"), code_size_bytes: Math.max(0, (code.length - 2) / 2) };
      }
      lastErr = data?.error?.message || `HTTP ${res.status}`;
    } catch (e: any) {
      lastErr = e?.message || String(e);
    }
    if (attempt < 2) await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
  }
  return { is_contract: null, code_size_bytes: null, error: lastErr };
}

// Known permissionless meme-token factory templates on Base — see
// agents/investigate.py's MEME_FACTORY_NAME_PATTERNS for why this is a
// real, deterministic signal, not a guess. Keep in sync.
const MEME_FACTORY_NAME_PATTERNS = ["clanker"];

/** Crude trait -> exploit-technique messages, matching
 * agents/investigate.py::hack_correlation() exactly. Note: the Python
 * version also fetches DeFiLlama's hacks feed into a `techniques` dict that
 * the function never actually reads before returning — these hits are
 * generated purely from `gp`'s own boolean traits either way, so this port
 * skips that always-unused fetch rather than porting dead latency; output
 * is identical in every case. */
export function hackCorrelation(gp: Record<string, any>): string[] {
  const hits: string[] = [];
  if (String(gp.is_honeypot) === "1") hits.push("Honeypot trait present — matches recurring honeypot/rug incidents.");
  if (String(gp.can_take_back_ownership) === "1" || String(gp.owner_change_balance) === "1")
    hits.push("Owner can alter balances/ownership — access-control exploit surface (seen in recent key-compromise hacks).");
  if (String(gp.is_proxy) === "1")
    hits.push("Proxy contract — upgradeable logic; verify implementation isn't swappable to malicious code.");
  return hits;
}

const SCAM_KEYWORDS = ["rug pull", "rugpull", "rugged", "scam", "honeypot", "exit scam", "exploited", "hacked"];

export interface WebReputation {
  available: boolean;
  provider?: string;
  hits: string[];
  results: Array<{ title: string; url: string; snippet: string }>;
}

/** TypeScript port of agents/investigate.py::web_reputation_check() +
 * _scrape_excerpt(). Real web search for public reputation signals GoPlus/
 * DexScreener can't see — gracefully returns unavailable on any failure. */
export async function webReputationCheck(env: ResearchEnv, symbol: string, address: string): Promise<WebReputation> {
  const query = `"${symbol}" ${address} rug pull OR scam OR honeypot OR exploit`;
  let search;
  try {
    search = await webSearch(env, query, 5);
  } catch {
    return { available: false, hits: [], results: [] };
  }
  const hits: string[] = [];
  const normalized = search.results.slice(0, 5).map((r) => ({ title: r.title, url: r.url, snippet: r.snippet.slice(0, 200) }));
  let scrapedOne = false;
  const addrLower = address.toLowerCase();
  const symLower = symbol.toLowerCase();
  for (const r of normalized) {
    const blob = `${r.title} ${r.snippet}`.toLowerCase();
    // A broad OR-query like "... rug pull OR scam OR honeypot" reliably
    // surfaces popular GENERIC scam-education pages for virtually any
    // token, since search engines don't literally AND every quoted term.
    // Require the result to actually reference THIS token (address, or a
    // reasonably specific symbol) before treating a keyword match as real
    // evidence — otherwise every token gets the same generic hits and a
    // false penalty regardless of any real incident. Mirrors
    // agents/investigate.py::web_reputation_check() exactly.
    const mentionsTarget = blob.includes(addrLower) || (symLower.length >= 3 && blob.includes(symLower));
    if (mentionsTarget && SCAM_KEYWORDS.some((kw) => blob.includes(kw))) {
      let hit = `Public web result flags this project: "${r.title}" — ${r.url}`;
      if (!scrapedOne && r.url) {
        scrapedOne = true;
        try {
          const scraped = await webScrape(env, r.url);
          if (scraped.content) hit += `\n  - Scraped evidence: ${scraped.content.split(/\s+/).join(" ").slice(0, 400)}`;
        } catch { /* best-effort escalation only */ }
      }
      hits.push(hit);
    }
  }
  return { available: true, provider: search.provider, hits, results: normalized };
}

// $100M matches agents/defillama.py::stablecoins()'s own quality bar for a
// "real, major" stablecoin — one threshold, not two independently-chosen
// numbers. Mirrors agents/investigate.py::STABLECOIN_MIN_MCAP_USD.
const STABLECOIN_MIN_MCAP_USD = 1e8;
// A stablecoin trading meaningfully off its $1 peg is either already
// depegging (a real, live risk) or the CoinGecko match is wrong for some
// other reason — either way, not a case for the exception below. Mirrors
// agents/investigate.py::STABLECOIN_PEG_TOLERANCE.
const STABLECOIN_PEG_TOLERANCE = 0.03;

// Major fiat-backed stablecoin brand tickers/names — used ONLY to detect
// impersonation (see the stablecoin-brand-impersonation check in score()
// below), never to grant the verified-stablecoin exception itself (that's
// address-verified via stablecoinContext(), never guessed from a declared
// name/symbol). Tickers are matched EXACTLY against the declared symbol
// (not as a substring) — a short ticker like "dai" would false-positive on
// any unrelated symbol that happens to contain those letters (e.g. "DAIYA").
// Mirrors agents/investigate.py::STABLECOIN_BRAND_TICKERS.
const STABLECOIN_BRAND_TICKERS = new Set([
  "usdc", "usdt", "dai", "busd", "tusd", "usde", "usds", "frax", "gusd", "pyusd",
]);
// Full descriptive-name phrases are long/distinctive enough to stay safe as
// substrings of the token's declared name. Mirrors
// agents/investigate.py::STABLECOIN_BRAND_NAME_PHRASES.
const STABLECOIN_BRAND_NAME_PHRASES = ["usd coin", "tether"];

/**
 * Real, address-verified evidence that this exact contract is a live,
 * major, near-$1-pegged asset per CoinGecko's own data — or null if that
 * evidence doesn't exist. Never guessed from the token's own declared
 * name/symbol (a copycat contract self-declaring symbol "USDT" gets either
 * a 404 or its own, different CoinGecko listing, never Tether's real data —
 * closing the brand-impersonation loophole a symbol-only check would open).
 * Field-for-field port of agents/investigate.py::_stablecoin_context().
 */
export function stablecoinContext(cg: CoingeckoContractMarket | null | undefined): CoingeckoContractMarket | null {
  if (!cg) return null;
  const price = cg.price_usd;
  const mcap = cg.market_cap_usd;
  if (typeof price !== "number" || typeof mcap !== "number") return null;
  if (mcap < STABLECOIN_MIN_MCAP_USD) return null;
  if (Math.abs(price - 1.0) > STABLECOIN_PEG_TOLERANCE) return null;
  return { name: cg.name, symbol: cg.symbol, market_cap_usd: mcap, price_usd: price };
}

// Addresses whose held balance is permanently removed from circulation —
// must be excluded from concentration math or a healthy burn/deflationary
// mechanism would score as a whale-risk red flag. Mirrors
// agents/investigate.py::_BURN_ADDRESSES.
const BURN_ADDRESSES = new Set([
  "0x0000000000000000000000000000000000000000",
  "0x000000000000000000000000000000000000dead",
]);

/** Real top-holder concentration from GoPlus's own per-holder "holders"
 * array — already fetched inside goplusRaw() every call but never read
 * (only the scalar holder_count was). Excludes burn addresses and any
 * holder GoPlus itself tags as an LP/pool. Returns null on any missing/
 * malformed shape — GoPlus's exact schema couldn't be verified live from
 * the dev sandbox this was written in, so this degrades honestly to "no
 * signal" rather than ever guessing wrong. Field-for-field port of
 * agents/investigate.py::_holder_concentration(). */
export function holderConcentration(gp: Record<string, any>): { top_holders_pct: number; holders_counted: number } | null {
  const holders = gp?.holders;
  if (!Array.isArray(holders) || holders.length === 0) return null;
  let totalPct = 0;
  let counted = 0;
  for (const h of holders.slice(0, 10)) {
    if (!h || typeof h !== "object") continue;
    const addr = String(h.address || "").toLowerCase();
    if (BURN_ADDRESSES.has(addr)) continue;
    const tag = String(h.tag || "").toLowerCase();
    if (tag.includes("lp") || tag.includes("pool") || tag.includes("burn")) continue;
    let pct = Number(h.percent);
    if (!Number.isFinite(pct)) continue;
    if (pct > 1) pct = pct / 100;
    totalPct += pct;
    counted += 1;
  }
  if (counted === 0) return null;
  return { top_holders_pct: totalPct * 100, holders_counted: counted };
}

/** Real liquidity-lock status from GoPlus's own "lp_holders" array
 * (is_locked per LP-token holder) — the classic "can the dev pull
 * liquidity" check, already fetched but never read. Same honest-
 * degradation caveat as holderConcentration() above. Field-for-field port
 * of agents/investigate.py::_lp_lock_status(). */
export function lpLockStatus(gp: Record<string, any>): { locked_pct: number; lp_holders_counted: number } | null {
  const lpHolders = gp?.lp_holders;
  if (!Array.isArray(lpHolders) || lpHolders.length === 0) return null;
  let totalPct = 0;
  let lockedPct = 0;
  let counted = 0;
  for (const h of lpHolders) {
    if (!h || typeof h !== "object") continue;
    let pct = Number(h.percent);
    if (!Number.isFinite(pct)) continue;
    if (pct > 1) pct = pct / 100;
    totalPct += pct;
    if (String(h.is_locked) === "1") lockedPct += pct;
    counted += 1;
  }
  if (counted === 0 || totalPct <= 0) return null;
  return { locked_pct: (lockedPct / totalPct) * 100, lp_holders_counted: counted };
}

export interface ScoreVerif {
  checked: boolean;
  verified?: boolean | null;
  name?: string | null;
  proxy?: boolean | null;
  note?: string;
}

export interface ScoreResult {
  score: number;
  verdict: "PROCEED" | "CAUTION" | "REJECT";
  reasons: string[];
  positive_signals: string[];
}

/** Field-for-field port of agents/investigate.py::score() — same weights,
 * same thresholds, same messages. Keep both in sync on any change. */
export function score(gp: Record<string, any>, dex: DexInfo, onchain: { is_contract: boolean | null },
                       verif: ScoreVerif, webRep?: WebReputation,
                       coingeckoContract?: CoingeckoContractMarket | null): ScoreResult {
  let s = 100;
  const reasons: string[] = [];
  const positiveSignals: string[] = [];
  const flag = (cond: boolean, penalty: number, msg: string) => { if (cond) { s -= penalty; reasons.push(`[-${penalty}] ${msg}`); } };
  const signal = (cond: boolean, msg: string) => { if (cond) positiveSignals.push(msg); };

  flag(String(gp.is_honeypot) === "1", 60, "HONEYPOT detected");
  flag(String(gp.cannot_sell_all) === "1", 30, "Cannot sell all tokens");
  flag(String(gp.is_mintable) === "1", 12, "Mintable supply (dilution risk)");
  flag(String(gp.can_take_back_ownership) === "1", 18, "Ownership can be reclaimed");
  flag(String(gp.owner_change_balance) === "1", 25, "Owner can change balances (rug surface)");
  flag(String(gp.hidden_owner) === "1", 20, "Hidden owner");
  flag(String(gp.is_proxy) === "1", 8, "Upgradeable proxy (verify implementation)");
  flag(String(gp.transfer_pausable) === "1", 15, "Transfers can be paused by owner");
  const bt = parseFloat(gp.buy_tax) || 0;
  const st = parseFloat(gp.sell_tax) || 0;
  flag(bt > 0.10, 15, `High buy tax ${(bt * 100).toFixed(0)}%`);
  flag(st > 0.10, 20, `High sell tax ${(st * 100).toFixed(0)}%`);

  const owner = (gp.owner_address || "").toLowerCase();
  const zeroAddr = "0x0000000000000000000000000000000000000000";
  const ownerPresent = Boolean(owner) && owner !== zeroAddr;
  flag(ownerPresent, 10, `Owner not renounced (${gp.owner_address}) — can still act on the contract`);
  signal(Boolean(owner) && !ownerPresent, "Ownership renounced");

  // Recognized major stablecoin — refunds ONLY the three specific
  // compliance-mechanism penalties above (mint/owner-balance-change/
  // unrenounced-owner — the DEFINING, expected architecture of a compliant
  // fiat-backed stablecoin, not a rug surface), never honeypot/hidden-owner/
  // pausable-transfers/tax/liquidity/etc., which stay real red flags for any
  // token. Field-for-field port of agents/investigate.py::score()'s same block.
  const stableCtx = stablecoinContext(coingeckoContract);
  if (stableCtx) {
    let refund = 0;
    if (String(gp.is_mintable) === "1") refund += 12;
    if (String(gp.owner_change_balance) === "1") refund += 25;
    if (ownerPresent) refund += 10;
    if (refund) {
      s += refund;
      reasons.push(`[+${refund}] Verified major stablecoin (${stableCtx.name}, `
        + `$${stableCtx.market_cap_usd!.toLocaleString()} circulating, $${stableCtx.price_usd!.toFixed(4)} peg) — `
        + "mint/owner-controlled-freeze/retained-ownership are standard compliance mechanisms for "
        + "this category, not rug indicators; penalties above refunded");
    }
    signal(true, `Verified as a real, market-data-recognized major stablecoin `
      + `($${stableCtx.market_cap_usd!.toLocaleString()} circulating, $${stableCtx.price_usd!.toFixed(4)} peg)`);
  }

  // Stablecoin-brand impersonation — the inverse of the verified-stablecoin
  // exception above. Real gap this closes: a token self-declaring symbol
  // "USDC" scored only 68/100 CAUTION (intel/investigations/investigation-
  // 20260725-041324-0x8dB2be2b.md) despite actually being "United States of
  // Doge CashCat," trading at $0.0001865 — nowhere near the real $1 peg it
  // trades on the strength of its stolen ticker — and never verified by
  // CoinGecko as the genuine address. Deliberately requires BOTH a matching
  // brand name/symbol AND a real, far-off-peg (or missing) price — not just
  // "unverified by CoinGecko," which a legitimate but thinly-tracked
  // bridged/wrapped stablecoin variant could also trip. Field-for-field port
  // of agents/investigate.py::score()'s same block.
  const dexNameL = (dex.name || "").toLowerCase();
  const dexSymStripped = (dex.symbol || "").toLowerCase().trim();
  const claimsStablecoinBrand = STABLECOIN_BRAND_TICKERS.has(dexSymStripped)
    || STABLECOIN_BRAND_NAME_PHRASES.some((p) => dexNameL.includes(p));
  if (claimsStablecoinBrand && !stableCtx) {
    const dexPrice = Number(dex.price_usd) || 0;
    const priceOffPeg = dexPrice <= 0 || Math.abs(dexPrice - 1.0) > 0.15;
    flag(priceOffPeg, 40,
      `Token name/symbol (${dex.name} / ${dex.symbol}) claims a major stablecoin `
      + `brand but trades at $${dexPrice.toFixed(6)}, nowhere near the real $1 peg, and is not the `
      + "independently-verified real asset at this address — brand impersonation, not a real stablecoin");
  }

  const cname = (verif.name || "").toLowerCase();
  const isFactoryTemplate = MEME_FACTORY_NAME_PATTERNS.some((p) => cname.includes(p));
  flag(isFactoryTemplate, 20, `Deployed via a permissionless meme-token factory template (${verif.name}) `
    + "— no team vetting by design; this pattern strongly correlates with abandoned/rugged tokens");

  let holders: number | null = null;
  if (gp.holder_count !== undefined && gp.holder_count !== null && gp.holder_count !== "") {
    const parsed = parseInt(gp.holder_count, 10);
    if (!Number.isNaN(parsed)) holders = parsed;
  }
  if (holders !== null) {
    flag(holders < 50, 20, `Very few holders (${holders}) — thin, easily manipulated distribution`);
    flag(holders >= 50 && holders < 200, 8, `Low holder count (${holders})`);
    signal(holders >= 500, `${holders} holders — reasonably distributed`);
  } else {
    flag(true, 5, "Holder count unavailable — cannot assess distribution");
  }

  // Real top-holder concentration + LP-lock status — both already sitting
  // in GoPlus's own response every call but never previously read. Field-
  // for-field port of agents/investigate.py::score()'s same block
  // (deliberately moderate weights — see that block's comment for why).
  const concentration = holderConcentration(gp);
  if (concentration) {
    const topPct = concentration.top_holders_pct;
    flag(topPct >= 70, 15, `Top ${concentration.holders_counted} non-LP/burn holders control `
      + `${topPct.toFixed(0)}% of supply — concentrated, easily manipulated`);
    flag(topPct >= 50 && topPct < 70, 8, `Top ${concentration.holders_counted} non-LP/burn holders control `
      + `${topPct.toFixed(0)}% of supply — meaningful concentration`);
    signal(topPct < 20, `Top holders control only ${topPct.toFixed(0)}% of supply — broad distribution`);
  }

  const lpLock = lpLockStatus(gp);
  if (lpLock) {
    const lockedPct = lpLock.locked_pct;
    flag(lockedPct < 50, 15, `Only ${lockedPct.toFixed(0)}% of liquidity is locked — `
      + "the deployer can pull the rest at any time");
    signal(lockedPct >= 80, `${lockedPct.toFixed(0)}% of liquidity is locked — reduced rug-pull risk`);
  }

  // Mutually exclusive tiers -- real bug this fixes (found in
  // agents/investigate.py::score(), the Python side this file must stay in
  // exact sync with): liquidity < $10k used to trip BOTH "Very low
  // liquidity" (-25) AND "Low liquidity" (-10) since the second check's
  // `< 50000` had no lower bound at the first tier's own cutoff -- one real
  // fact double-penalized. Bounded here the same way the Python fix was.
  const liq = Number(dex.liquidity_usd) || 0;
  flag(Boolean(liq) && liq < 10000, 25, `Very low liquidity $${liq.toLocaleString()} (rug/illiquid)`);
  flag(Boolean(liq) && liq >= 10000 && liq < 50000, 10, `Low liquidity $${liq.toLocaleString()}`);
  signal(liq >= 500000, `Deep liquidity ($${liq.toLocaleString()})`);

  const chg = dex.change_24h_pct;
  if (chg !== undefined && chg !== null && Math.abs(Number(chg)) > 100) {
    flag(true, 10, `Violent 24h move ${Number(chg) >= 0 ? "+" : ""}${Number(chg).toFixed(0)}% (volatility/manipulation)`);
  }

  let ageDays: number | null = null;
  if (dex.pair_created_ms) {
    ageDays = (Date.now() - Number(dex.pair_created_ms)) / 86400000;
  }
  if (ageDays !== null) {
    flag(ageDays < 3, 15, `Pair only ${ageDays.toFixed(1)} days old (extreme fresh-launch risk)`);
    flag(ageDays >= 3 && ageDays < 14, 10, `Pair ${ageDays.toFixed(1)} days old — under two weeks, no track record yet`);
    flag(ageDays >= 14 && ageDays < 30, 5, `Pair ${ageDays.toFixed(1)} days old — under a month, still unproven`);
    signal(ageDays >= 90, `Trading ${ageDays.toFixed(0)}+ days without a known incident in this scan`);
  } else {
    flag(true, 8, "No pair-creation timestamp available — cannot establish track record length");
  }

  if (verif.checked) {
    flag(verif.verified === false, 15, "Contract source UNVERIFIED");
    signal(verif.verified === true && !isFactoryTemplate, "Custom verified source (not a mass-produced factory template)");
  }
  if (onchain.is_contract === false) reasons.push("[note] address has no contract code (EOA or not deployed)");

  const unproven = isFactoryTemplate || (ageDays !== null && ageDays < 30) || (holders !== null && holders < 200);
  flag(unproven, 10, "No known third-party audit or verifiable team identity found — "
    + "treated as unaudited/anonymous by default");

  if (webRep?.hits.length) {
    flag(true, 25, `Public web search surfaced ${webRep.hits.length} unambiguous `
      + "scam/rug mention(s) — see Public Web Signals section");
  }

  let cap: number | null = null;
  if (positiveSignals.length === 0) cap = 55;
  else if (positiveSignals.length === 1) cap = 70;
  if (cap !== null && s > cap) {
    reasons.push(`[capped at ${cap}] Only ${positiveSignals.length} positive legitimacy `
      + "signal(s) found — score capped even though few explicit red flags triggered");
    s = cap;
  }

  s = Math.max(0, Math.min(100, s));
  const verdict: ScoreResult["verdict"] = s >= 80 ? "PROCEED" : s >= 50 ? "CAUTION" : "REJECT";
  return { score: s, verdict, reasons, positive_signals: positiveSignals };
}

// ── Scoring Dashboard: weighted, multi-factor category scores ──────────────
// Field-for-field port of agents/investigate.py's _CATEGORY_WEIGHTS/
// _CATEGORY_SHORT_LABEL/_CATEGORY_KEYWORDS/_bucket_for_category_dashboard/
// _category_rationale/_compute_category_scores — real gap this closes:
// dossierCheck() had no category breakdown at all, a structurally thinner
// output than the free investigation report's Scoring Dashboard for the
// exact same underlying score()/reasons/positive_signals, which is its own
// kind of cross-surface inconsistency. Presentation-layer instrumentation
// only, same as the Python side — score()'s own number/verdict stays the
// one authoritative source of truth, never derived FROM these.
export interface CategoryScore { score: number; weight: number; rationale: string; }

export const CATEGORY_WEIGHTS: ReadonlyArray<readonly [string, number]> = [
  ["Contract Security & Controls", 0.25],
  ["Liquidity Health & Lock Quality", 0.20],
  ["Holder Distribution & Concentration", 0.15],
  ["Transparency & Provenance", 0.15],
  ["Narrative Strength & Social Proof", 0.15],
  ["Longevity & Clean Track Record", 0.10],
];

const REASON_WEIGHT_RE = /^\[([+-])(\d+)\]/;

// Field-for-field port of agents/investigate.py's _CAP_RE -- matches score()'s
// own legitimacy-cap reason string ("[capped at N] ..."), the one whole-score
// ceiling reachable from this file's score(). Keeps every category's display
// from exceeding a cap that already fired on the overall number -- real
// inconsistency this closes: dossierCheck() computes categories from the same
// reasons list as the capped overall score/verdict, so without this a capped
// CAUTION could still show a category at 100.
const CAP_RE = /^\[capped at (\d+)\]/;

// Deliberately excludes "Narrative Strength & Social Proof" -- score() has
// no rule that ever produces a narrative/social reason string, so that
// category is built entirely from direct signals below instead.
const CATEGORY_KEYWORDS: ReadonlyArray<readonly [string, readonly string[]]> = [
  ["Contract Security & Controls", [
    "honeypot", "cannot sell", "mintable", "mint function",
    "ownership can be reclaimed", "take back ownership", "change balances",
    "hidden owner", "proxy", "pausable", "buy tax", "sell tax",
    "not renounced", "renounced",
  ]],
  ["Liquidity Health & Lock Quality", ["liquidity", "locked"]],
  ["Holder Distribution & Concentration", ["holder", "concentrat", "distribution", "manipulated", "supply"]],
  ["Transparency & Provenance", [
    "audit", "verified source", "unverified", "factory", "template",
    "deployer", "web search", "scam", "rug", "eoa", "no contract code",
    "peg", "stablecoin", "impersonat", "fdv", "dilution",
  ]],
  ["Longevity & Clean Track Record", ["days old", "track record", "violent", "volatility", "24h move", "defillama"]],
];

function bucketForCategoryDashboard(text: string): string | null {
  const low = text.toLowerCase();
  for (const [name, keywords] of CATEGORY_KEYWORDS) {
    if (keywords.some((k) => low.includes(k))) return name;
  }
  return null;
}

function categoryRationale(score: number, hits: string[]): string {
  if (!hits.length) return score === 100 ? "No signal either way this cycle." : "Derived from the evidence above.";
  const joined = hits.slice(0, 3).join("; ");
  return joined.endsWith(".") ? joined : `${joined}.`;
}

/** Field-for-field port of agents/investigate.py::_compute_category_scores().
 * Never throws; missing evidence just leaves a category at its neutral
 * baseline rather than breaking the paid response. */
export function computeCategoryScores(
  reasons: string[], positiveSignals: string[], dex?: DexInfo | null,
  projectNarrative?: { text?: string; address_identity_verified?: boolean } | null,
  webRep?: WebReputation | null,
): Record<string, CategoryScore> {
  const totals: Record<string, number> = {};
  const hits: Record<string, string[]> = {};
  for (const [name] of CATEGORY_WEIGHTS) { totals[name] = 100; hits[name] = []; }

  for (const r of reasons || []) {
    const m = REASON_WEIGHT_RE.exec(r);
    if (!m) continue;
    const name = bucketForCategoryDashboard(r);
    if (!name) continue;
    const delta = parseInt(m[2], 10) * (m[1] === "+" ? 1 : -1);
    totals[name] += delta;
    if (delta < 0) hits[name].push(r.split("]").slice(1).join("]").trim());
  }
  for (const p of positiveSignals || []) {
    const name = bucketForCategoryDashboard(p);
    if (name) hits[name].push(`(+) ${p}`);
  }

  // Narrative Strength & Social Proof -- the one category score() has no
  // rule for at all. Starts LOW (missing narrative/social surface is
  // itself a disclosed risk), not neutral at 100 like an untouched
  // keyword bucket would default to.
  let narrativeScore = 20;
  const narrativeHits: string[] = [];
  const siteLinks = (dex?.websites || []).map((w) => w.url).filter(Boolean);
  const socialLinks = (dex?.socials || []).filter((s) => s.url);
  if (siteLinks.length) { narrativeScore += 25; narrativeHits.push("has a declared project website"); }
  if (socialLinks.length) {
    narrativeScore += 15 * Math.min(2, socialLinks.length);
    narrativeHits.push(`${socialLinks.length} declared social link(s)`);
  }
  if (projectNarrative?.text) {
    if (projectNarrative.address_identity_verified) {
      narrativeScore += 25;
      narrativeHits.push("a real, address-verified project narrative was established");
    } else {
      narrativeScore += 10;
      narrativeHits.push("a narrative exists but this contract's affiliation with it is unverified");
    }
  } else {
    narrativeHits.push("no coherent project narrative could be established this cycle");
  }
  if (webRep?.available && !webRep?.hits?.length) narrativeScore += 5;
  totals["Narrative Strength & Social Proof"] = narrativeScore;
  hits["Narrative Strength & Social Proof"] = narrativeHits;

  let cap: number | null = null;
  for (const r of reasons || []) {
    const m = CAP_RE.exec(r);
    if (m) {
      const n = parseInt(m[1], 10);
      cap = cap === null ? n : Math.min(cap, n);
    }
  }

  const result: Record<string, CategoryScore> = {};
  for (const [name, weight] of CATEGORY_WEIGHTS) {
    let score = Math.max(0, Math.min(100, Math.round(totals[name])));
    let rationale = categoryRationale(score, hits[name]);
    if (cap !== null && score > cap) {
      score = cap;
      rationale += ` (Capped at ${cap} in line with the overall verdict's own confidence ceiling.)`;
    }
    result[name] = { score, weight, rationale };
  }
  return result;
}
