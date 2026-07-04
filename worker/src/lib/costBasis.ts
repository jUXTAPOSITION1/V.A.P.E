/**
 * Estimated cost-basis P&L per token: current value vs. USD price at the
 * token's earliest recorded incoming transfer to the wallet. This is a
 * deliberately simple approximation, not real accounting — it uses a single
 * acquisition point rather than a quantity-weighted average across every
 * incoming transfer, specifically to keep this to one Alchemy call + one
 * CoinGecko historical call per token (bounded further by MAX_TOKENS below)
 * rather than one CoinGecko call per transfer, which would burn through the
 * Demo API key's rate limit on any wallet with real transaction history.
 * Every result says so explicitly via `method` so this never gets read as
 * more precise than it is.
 */
import { getEarliestIncomingTransfer } from "./alchemy";
import { getHistoricalPrice } from "./coingecko";

interface CostBasisEnv {
  ALCHEMY_API_KEY?: string;
  COINGECKO_API_KEY?: string;
}

export interface TokenForCostBasis {
  contractAddress: string;
  symbol: string;
  currentBalance: number;
  currentPriceUsd: number;
}

export interface TokenCostBasis {
  contractAddress: string;
  symbol: string;
  method: "first-acquisition-estimate";
  acquiredAt: string | null; // ISO date, or null if unavailable
  costBasisUsd: number | null; // price at acquisition
  currentValueUsd: number;
  pnlUsd: number | null;
  pnlPct: number | null;
  note?: string;
}

const MAX_TOKENS = 10;

export async function estimateCostBasis(env: CostBasisEnv, address: string, tokens: TokenForCostBasis[]): Promise<TokenCostBasis[]> {
  if (!env.COINGECKO_API_KEY) {
    throw new Error("cost basis estimate requires COINGECKO_API_KEY (Demo API key) to be configured");
  }
  const ranked = [...tokens].sort((a, b) => b.currentBalance * b.currentPriceUsd - a.currentBalance * a.currentPriceUsd).slice(0, MAX_TOKENS);

  const results: TokenCostBasis[] = [];
  for (const t of ranked) {
    const currentValueUsd = t.currentBalance * t.currentPriceUsd;
    try {
      const earliest = await getEarliestIncomingTransfer(env, address, t.contractAddress);
      if (!earliest) {
        results.push({ contractAddress: t.contractAddress, symbol: t.symbol, method: "first-acquisition-estimate", acquiredAt: null, costBasisUsd: null, currentValueUsd, pnlUsd: null, pnlPct: null, note: "no incoming transfer found on record" });
        continue;
      }
      const priceThen = await getHistoricalPrice(env, t.contractAddress, earliest.timestamp);
      if (priceThen == null) {
        results.push({ contractAddress: t.contractAddress, symbol: t.symbol, method: "first-acquisition-estimate", acquiredAt: new Date(earliest.timestamp * 1000).toISOString(), costBasisUsd: null, currentValueUsd, pnlUsd: null, pnlPct: null, note: "no historical price available for that date" });
        continue;
      }
      const costBasisUsd = earliest.value * priceThen;
      const pnlUsd = currentValueUsd - costBasisUsd;
      results.push({
        contractAddress: t.contractAddress,
        symbol: t.symbol,
        method: "first-acquisition-estimate",
        acquiredAt: new Date(earliest.timestamp * 1000).toISOString(),
        costBasisUsd,
        currentValueUsd,
        pnlUsd,
        pnlPct: costBasisUsd > 0 ? (pnlUsd / costBasisUsd) * 100 : null,
        note: "approximate — priced at first incoming transfer only, not a weighted average of every acquisition",
      });
    } catch (e) {
      results.push({ contractAddress: t.contractAddress, symbol: t.symbol, method: "first-acquisition-estimate", acquiredAt: null, costBasisUsd: null, currentValueUsd, pnlUsd: null, pnlPct: null, note: "lookup failed" });
    }
  }
  return results;
}
