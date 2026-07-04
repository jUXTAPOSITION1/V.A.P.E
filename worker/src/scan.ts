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
  liquidity_usd: number;
  is_honeypot: string | null;
  buy_tax: string | null;
  sell_tax: string | null;
  owner_address: string | null;
  top_pair_dex: string | null;
  source: string;
  data_error?: string | null;
  error?: string;
}

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

  let verdict: ScanResult["verdict"];
  if (gp.is_honeypot === "1") verdict = "REJECT";
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
    liquidity_usd: liquidityUsd,
    is_honeypot: gp.is_honeypot ?? null,
    buy_tax: gp.buy_tax ?? null,
    sell_tax: gp.sell_tax ?? null,
    owner_address: owner || null,
    top_pair_dex: pairs[0]?.dexId ?? null,
    source: "goplus+dexscreener",
    data_error: gpRaw?._error || dsRaw?._error || null,
  };
}
