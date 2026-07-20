/**
 * bulk_safety_bundle — scan 5-25 tokens in one job at a flat price (per
 * data/reputation.json: $0.50 for up to 25, vs. $0.02 x 25 = $0.50 standalone
 * — the "40% off" in its summary refers to ACP's per-seat/negotiated pricing
 * history, not a discount this route computes; the flat $0.50 ceiling price
 * already reflects it). Real gap this closes: listed since day one
 * (auto:false, x402:false) with no code ever fulfilling it — this is a thin
 * batch wrapper around the exact same token_safety_check pipeline every
 * other token gets scanned with (worker/src/handlers.ts::fulfill()), not a
 * new scoring path.
 */
import { fulfill, type HandlerName } from "../handlers";

export interface BulkSafetyItem {
  address: string;
  chain_id: number;
  status: string;
  deliverable?: unknown;
  error?: string;
}

export interface BulkSafetyResult {
  error?: string;
  note?: string;
  count?: number;
  results?: BulkSafetyItem[];
}

const MIN_ADDRESSES = 5;
const MAX_ADDRESSES = 25;

export async function bulkSafetyBundle(addresses: string[], chainId: number, env: unknown): Promise<BulkSafetyResult> {
  if (addresses.length < MIN_ADDRESSES || addresses.length > MAX_ADDRESSES) {
    return { error: "invalid_count", note: `supply ${MIN_ADDRESSES}-${MAX_ADDRESSES} comma-separated addresses (got ${addresses.length})` };
  }
  const offering: HandlerName = "token_safety_check";
  const results = await Promise.all(
    addresses.map(async (address): Promise<BulkSafetyItem> => {
      const r = (await fulfill(offering, { address, chain_id: chainId }, env)) as {
        status: string; deliverable?: unknown; error?: string;
      };
      return {
        address, chain_id: chainId, status: r.status, deliverable: r.deliverable,
        error: r.status === "error" ? r.error : undefined,
      };
    })
  );
  return { count: results.length, results };
}
