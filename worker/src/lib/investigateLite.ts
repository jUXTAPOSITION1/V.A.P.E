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

const UA = { "User-Agent": "VAPE-PrivateEye/1.0" };
const BASE_RPC = "https://mainnet.base.org";

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

export async function onchainPresence(address: string): Promise<{ is_contract: boolean; code_size_bytes: number }> {
  try {
    const res = await fetch(BASE_RPC, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...UA },
      body: JSON.stringify({ jsonrpc: "2.0", method: "eth_getCode", params: [address, "latest"], id: 1 }),
    });
    const data: any = await res.json();
    const code: string = data?.result || "0x";
    return { is_contract: Boolean(code && code !== "0x"), code_size_bytes: Math.max(0, (code.length - 2) / 2) };
  } catch {
    return { is_contract: false, code_size_bytes: 0 };
  }
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
export function score(gp: Record<string, any>, dex: DexInfo, onchain: { is_contract: boolean },
                       verif: ScoreVerif, webRep?: WebReputation): ScoreResult {
  let s = 100;
  const reasons: string[] = [];
  const positiveSignals: string[] = [];
  const flag = (cond: boolean, penalty: number, msg: string) => { if (cond) { s -= penalty; reasons.push(`[-${penalty}] ${msg}`); } };
  const signal = (cond: boolean, msg: string) => { if (cond) positiveSignals.push(msg); };

  flag(String(gp.is_honeypot) === "1", 60, "GoPlus: HONEYPOT detected");
  flag(String(gp.cannot_sell_all) === "1", 30, "GoPlus: cannot sell all tokens");
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

  const liq = Number(dex.liquidity_usd) || 0;
  flag(Boolean(liq) && liq < 10000, 25, `Very low liquidity $${liq.toLocaleString()} (rug/illiquid)`);
  flag(Boolean(liq) && liq < 50000, 10, `Low liquidity $${liq.toLocaleString()}`);
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
