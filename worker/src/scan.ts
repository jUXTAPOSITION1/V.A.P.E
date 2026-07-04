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
  data_error?: string | null;
  error?: string;
}

// Hard-reject GoPlus fields — same tier as honeypot, not just an advisory
// flag. Real, documented GoPlus token_security fields, flat "0"/"1" strings
// like their siblings (is_mintable, is_proxy, etc.) already used below.
// Kept in its own list so agents/token_scan.py / docs/assets/app.js stay
// field-for-field identical.
const HARD_REJECT_FIELDS = ["is_blacklisted", "selfdestruct", "is_airdrop_scam"] as const;

async function safeGet(url: string): Promise<any> {
  try {
    const r = await fetch(url, { headers: UA });
    return await r.json();
  } catch (e: any) {
    return { _error: String(e?.message || e) };
  }
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

  const [gpRaw, dsRaw] = await Promise.all([
    safeGet(`https://api.gopluslabs.io/api/v1/token_security/${chainId}?contract_addresses=${addr}`),
    safeGet(`https://api.dexscreener.com/latest/dex/tokens/${addr}`),
  ]);

  let gp: Record<string, any> = {};
  if (gpRaw && typeof gpRaw === "object" && gpRaw.result) {
    const vals = Object.values(gpRaw.result as Record<string, any>);
    gp = (vals[0] as Record<string, any>) || {};
  }

  const pairs: any[] = (dsRaw && typeof dsRaw === "object" && Array.isArray(dsRaw.pairs)) ? dsRaw.pairs : [];
  const liquidityUsd = Math.round(pairs.reduce((s, p) => s + ((p.liquidity || {}).usd || 0), 0) * 100) / 100;
  // Oldest pair creation timestamp across all pairs — a token's real track
  // record starts at its FIRST pair, not whichever pair happens deepest now.
  const pairCreatedTimes = pairs.map((p) => p.pairCreatedAt).filter((t) => !!t);
  const pairCreatedMs = pairCreatedTimes.length ? Math.min(...pairCreatedTimes) : null;
  const hasSocials = pairs.some((p) => (p.info?.socials?.length ?? 0) > 0 || (p.info?.websites?.length ?? 0) > 0);

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
    top_pair_dex: pairs[0]?.dexId ?? null,
    source: "goplus+dexscreener",
    data_error: gpRaw?._error || dsRaw?._error || null,
  };
}
