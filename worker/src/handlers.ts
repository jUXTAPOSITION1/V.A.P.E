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
import { goplusRaw, dexscreenerFull, onchainPresence, hackCorrelation, webReputationCheck, score,
         type DexInfo } from "./lib/investigateLite";
import { webScrape, type ResearchEnv } from "./lib/webResearch";
import { askFrontier, type LlmEnv } from "./lib/llm";

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

// Best-effort: actually VISIT each DexScreener-declared website/social URL
// via lib/webResearch's Firecrawl -> keyless-fetch scrape chain, instead of
// only checking the array is non-empty (scan.ts's has_declared_socials is
// that lighter boolean-only check every free/auto offering already
// reports). NOT a follower-count/account-age check — X's/Telegram's real
// metrics need an official paid API this repo doesn't hold. Mirrors
// agents/acp_fulfill.py::_verify_socials() exactly.
async function verifySocials(env: ResearchEnv, dex: DexInfo) {
  const declared = [...dex.websites, ...dex.socials];
  if (!declared.length) return { declared_count: 0, checked: [] as Array<Record<string, unknown>> };
  // Cap at 3 — cost/latency proportionate to safety_preflight's instant,
  // synchronous nature.
  const checked = await Promise.all(declared.slice(0, 3).map(async (item: any) => {
    const url = item.url as string;
    const type = item.type || "website";
    try {
      const res = await webScrape(env, url);
      const reachable = Boolean(res.content && res.content.trim());
      return reachable
        ? { type, url, reachable, excerpt: res.content!.split(/\s+/).join(" ").slice(0, 200) }
        : { type, url, reachable };
    } catch (e: any) {
      return { type, url, reachable: false, error: String(e?.message || e) };
    }
  }));
  return { declared_count: declared.length, checked };
}

const AI_QUICK_REVIEW_SYSTEM = "You are VAPE, an autonomous on-chain security reviewer, giving a QUICK paid "
  + "pre-trade read (not the full $50 24h deep-dive audit). Base every claim on "
  + "the actual verified source given below — never invent function names or "
  + "behavior you weren't shown. In 3-5 sentences, name any real red flags across "
  + "reentrancy, access control, oracle trust, proxy/upgrade risk, and honeypot/rug "
  + "mechanics — or state plainly that nothing stood out in a quick read. This is a "
  + "fast signal, not a substitute for a full audit; do not fabricate confidence.";

// Frontier-LLM quick read of the actual verified source — same provider
// framing as the $50 deep-dive (Gemini 2.5 Pro, Groq fallback — see
// lib/llm.ts), but a far smaller prompt/output budget matched to
// safety_preflight's synchronous, instant-tier nature. Mirrors
// agents/acp_fulfill.py::_ai_quick_review() exactly.
async function aiQuickReview(env: LlmEnv, verifChecked: boolean, verifNote: string | undefined,
                              verifName: string | null | undefined, sourceCode: string | null | undefined,
                              reasons: string[]) {
  if (!verifChecked) return { available: false, note: verifNote ?? "contract source unavailable" };
  if (!sourceCode) return { available: false, note: "verified but no source text returned" };
  const user = `=== VERIFIED SOURCE (${verifName}, truncated) ===\n${sourceCode.slice(0, 12000)}\n\n`
    + `=== KNOWN RISK FACTORS FROM RECON ===\n${reasons.length ? reasons.join("\n") : "none"}`;
  const result = await askFrontier(env, AI_QUICK_REVIEW_SYSTEM, user, { maxTokens: 400, temperature: 0.3, timeoutMs: 25000 });
  return result.available
    ? { available: true, provider: result.provider, summary: result.text }
    : { available: false, note: result.note };
}

// All-in-one pre-trade verdict — VAPE's most complete instant offering.
// Reuses the same real heuristic engine (weighted score, meme-factory-
// template detection, recent-hack correlation, public web-reputation
// search) every FREE VAPE investigation runs — see lib/investigateLite.ts —
// instead of the thinner token_scan()-only verdict this offering returned
// before, plus a best-effort visit of the project's own declared website/
// social URLs and a frontier-LLM quick read of the actual verified source.
// Mirrors agents/acp_fulfill.py::_safety_preflight() exactly.
async function safetyPreflight(req: Requirement, env: { ETHERSCAN_API_KEY?: string } & ResearchEnv & LlmEnv) {
  const a = addrFrom(req);
  if (!a) return { error: "no address" };
  const chain = chainFrom(req);

  const [gp, dex, onchain, src] = await Promise.all([
    goplusRaw(a, chain),
    dexscreenerFull(a),
    onchainPresence(a),
    getContractSource(a, chain, env.ETHERSCAN_API_KEY),
  ]);
  const verifChecked = !src.error;
  const verif = { checked: verifChecked, verified: src.verified ?? null, name: src.contract_name ?? null,
                   proxy: src.proxy ?? null, note: src.note ?? src.error };
  const corr = hackCorrelation(gp);
  const symbol = dex.symbol || verif.name || "unknown";
  const webRep = await webReputationCheck(env, symbol, a);
  const { score: s, verdict, reasons, positive_signals } = score(gp, dex, onchain, verif, webRep);
  const cname = (verif.name || "").toLowerCase();
  const memeFactoryTemplate = ["clanker"].some((p) => cname.includes(p));

  const result: Record<string, unknown> = {
    address: a, chain_id: chain, symbol,
    score: s, verdict, reasons, positive_signals,
    verified: verif.verified, contract_name: verif.name, proxy: verif.proxy,
    meme_factory_template: memeFactoryTemplate,
    hack_correlation: corr,
    web_reputation: { checked: webRep.available, flagged: webRep.hits.length > 0, hits: webRep.hits, provider: webRep.provider },
  };
  // Same reasoning as exploitCheck: don't let a missing/failed verification
  // silently collapse into "verified: null" with no context.
  if (!verifChecked) result.verification_note = verif.note;

  result.social_verification = await verifySocials(env, dex);
  result.ai_review = await aiQuickReview(env, verifChecked, verif.note, verif.name, src.source_code, reasons);

  return result;
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
