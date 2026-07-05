/**
 * TypeScript port of agents/acp_fulfill.py's 6 "auto" offering handlers.
 * Same shapes, same logic — this is what runs behind the x402-paid routes.
 * The other 8 offerings (deep_contract_audit, forensics_deep, wallet_recon,
 * etc.) need the SKILLFORGE tool tier or a runner and are intentionally not
 * auto-run here, exactly as in the Python version — see docs/ACP_PROTOCOL.md
 * for hiring VAPE for those via a real ACP job instead.
 */
import { scan, type ScanResult } from "./scan";
import { getContractSource } from "./lib/contractSource";
import { marketIntel } from "./lib/marketIntel";

export interface Requirement {
  address?: string;
  contract?: string;
  token?: string;
  target?: string;
  chain_id?: number;
  chainId?: number;
  chain?: number;
}

function addrFrom(req: Requirement): string | null {
  for (const k of ["address", "contract", "token", "target"] as const) {
    if (req[k]) return String(req[k]).trim();
  }
  return null;
}

function chainFrom(req: Requirement, fallback = 8453): number {
  for (const k of ["chain_id", "chainId", "chain"] as const) {
    if (req[k]) return Number(req[k]);
  }
  return fallback;
}

async function tokenSafetyCheck(req: Requirement) {
  const a = addrFrom(req);
  if (!a) return { error: "no address in requirement" };
  return scan(a, chainFrom(req));
}

async function liquidityCheck(req: Requirement) {
  const a = addrFrom(req);
  if (!a) return { error: "no address" };
  const r = await scan(a, chainFrom(req));
  if (r.error) return r;
  return { address: a, liquidity_usd: r.liquidity_usd, top_pair_dex: r.top_pair_dex, verdict: r.verdict };
}

async function rugPullAlert(req: Requirement) {
  const a = addrFrom(req);
  if (!a) return { error: "no address" };
  const r = await scan(a, chainFrom(req));
  if (r.error) return r;
  const ownerFlags = new Set(["HONEYPOT", "mintable", "owner_not_renounced", "cannot_sell_all", "transfer_pausable",
    "is_blacklisted", "selfdestruct", "is_airdrop_scam", "lp_concentrated"]);
  const rug = r.flags.filter(f => ownerFlags.has(f));
  return {
    address: a,
    rug_risk: (r.is_honeypot === "1" || rug.length >= 2) ? "HIGH" : "LOW",
    owner_powers: rug,
    verdict: r.verdict,
  };
}

async function exploitCheck(req: Requirement, env: { ETHERSCAN_API_KEY?: string }) {
  const a = addrFrom(req);
  if (!a) return { error: "no address" };
  const src = await getContractSource(a, chainFrom(req), env.ETHERSCAN_API_KEY);
  // src.error (e.g. "no_key" when ETHERSCAN_API_KEY isn't configured, or a
  // real Etherscan API failure) must be surfaced, not swallowed — silently
  // falling through to all-null fields looks like "we checked, it's not
  // verified" when the truth is "we never checked", which a paying customer
  // has no way to tell apart otherwise.
  if (src.error) {
    return { address: a, error: src.error, note: src.note ?? "contract verification unavailable" };
  }
  return {
    address: a,
    verified: src.verified ?? null,
    contract_name: src.contract_name ?? null,
    proxy: src.proxy ?? null,
    note: "verification + proxy surface; deep audit = deep_contract_audit offering (ACP only)",
  };
}

async function marketIntelHandler(_req: Requirement) {
  const ctx = await marketIntel();
  return { base_tvl: ctx.base_tvl, top_protocols: ctx.top_protocols, prices: ctx.prices };
}

async function safetyPreflight(req: Requirement, env: { ETHERSCAN_API_KEY?: string }) {
  const a = addrFrom(req);
  if (!a) return { error: "no address" };
  const [ts, src] = await Promise.all([
    scan(a, chainFrom(req)),
    getContractSource(a, chainFrom(req), env.ETHERSCAN_API_KEY),
  ]);
  if (ts.error) return ts;
  return {
    address: a,
    token_verdict: ts.verdict,
    flags: ts.flags,
    verified: src.verified ?? null,
    // Same reasoning as exploitCheck: don't let a missing/failed
    // verification silently collapse into "verified: null" with no context.
    verification_note: src.error ? (src.note ?? src.error) : undefined,
    combined: (ts.verdict === "PROCEED" && src.verified) ? "PROCEED" : "REVIEW",
  };
}

export type HandlerName = "token_safety_check" | "liquidity_check" | "rug_pull_alert" | "exploit_check" | "market_intel" | "safety_preflight";

export const HANDLERS: Record<HandlerName, (req: Requirement, env: any) => Promise<unknown>> = {
  token_safety_check: tokenSafetyCheck,
  liquidity_check: liquidityCheck,
  rug_pull_alert: rugPullAlert,
  exploit_check: exploitCheck,
  market_intel: marketIntelHandler,
  safety_preflight: safetyPreflight,
};

export async function fulfill(offering: HandlerName, req: Requirement, env: any) {
  const h = HANDLERS[offering];
  try {
    const deliverable = await h(req, env);
    return { offering, status: "ok", deliverable, source: "vape-real-data", disclaimer: "Real on-chain data. Not investment advice." };
  } catch (e: any) {
    return { offering, status: "error", error: String(e?.message || e) };
  }
}
