/**
 * tx_decode — plain-language transaction decode + risk flags for a Base/EVM
 * tx hash. Real data only, no simulation, no LLM:
 *   - Etherscan V2 unified API (eth_getTransactionByHash/eth_getTransactionReceipt)
 *     for the tx itself and its emitted logs — same ETHERSCAN_API_KEY and
 *     endpoint convention as lib/contractSource.ts.
 *   - 4byte.directory's public, keyless method/event-signature database to
 *     turn raw selectors/topic0 hashes into a real human-readable signature
 *     (e.g. `transfer(address,uint256)`), when a match exists.
 * Real gap this closes: data/reputation.json has listed tx_decode ($0.05)
 * since day one, but it was ACP-only (auto:false, x402:false) — no code ever
 * actually fulfilled it. This is a genuinely new, deterministic pipeline, not
 * a relisting of an existing handler.
 */
const ETHERSCAN_V2 = "https://api.etherscan.io/v2/api";
const FOURBYTE = "https://www.4byte.directory/api/v1";

export interface DecodedLog {
  address: string;
  topic0: string | null;
  event: string | null;
}

export interface TxDecodeResult {
  error?: string;
  note?: string;
  tx_hash?: string;
  chain_id?: number;
  status?: "success" | "failed" | "pending";
  from?: string | null;
  to?: string | null;
  value_wei?: string | null;
  method?: { selector: string; signature: string | null } | null;
  logs_decoded?: DecodedLog[];
  risk_flags?: string[];
  summary?: string;
}

// keccak256("Approval(address,address,uint256)") — the standard ERC-20
// Approval event's topic0, a well-known constant (value is unindexed, so it
// lives in `data`, not `topics`, which is why the max-uint256 check below
// reads log.data rather than a topic slot).
const APPROVAL_EVENT_TOPIC0 = "0x8c5be1e5ebec7d5bd14f71427d1e84f3dd0314c0f7b2291e5b200ac8c7c3b925";
// type(uint256).max, left-padded to a 32-byte log data word — the exact value
// wallets/drainer kits alike use for an "infinite" ERC-20 approval.
const MAX_UINT256_DATA = "0x" + "f".repeat(64);

async function fourByteLookup(kind: "signatures" | "event-signatures", hex: string): Promise<string | null> {
  try {
    const r = await fetch(`${FOURBYTE}/${kind}/?hex_signature=${hex}`);
    if (!r.ok) return null;
    const d: any = await r.json();
    const results = Array.isArray(d?.results) ? d.results : [];
    if (!results.length) return null;
    // Selector/topic0 collisions are possible (4 or 32 bytes of hash space,
    // not a guarantee) — 4byte has no popularity ranking, so the lowest
    // submission id is used as the best-effort canonical pick (usually the
    // longest-standing, most widely-adopted signature for that hash).
    const best = results.reduce((a: any, b: any) => (a.id < b.id ? a : b));
    return best.text_signature || null;
  } catch {
    return null;
  }
}

export async function decodeTx(txHash: string, chainId: number, apiKey?: string): Promise<TxDecodeResult> {
  if (!apiKey) return { error: "no_key", note: "set ETHERSCAN_API_KEY for tx decode" };

  const q = (params: Record<string, string>) =>
    new URLSearchParams({ chainid: String(chainId), apikey: apiKey, ...params });

  let tx: any, receipt: any;
  try {
    const [txRes, receiptRes] = await Promise.all([
      fetch(`${ETHERSCAN_V2}?${q({ module: "proxy", action: "eth_getTransactionByHash", txhash: txHash })}`),
      fetch(`${ETHERSCAN_V2}?${q({ module: "proxy", action: "eth_getTransactionReceipt", txhash: txHash })}`),
    ]);
    tx = ((await txRes.json()) as any)?.result;
    receipt = ((await receiptRes.json()) as any)?.result;
  } catch (e: any) {
    return { error: String(e?.message || e) };
  }

  if (!tx) return { error: "not_found", note: "no transaction found for this hash on this chain" };

  const input: string = tx.input || "0x";
  const selector = input.length >= 10 ? input.slice(0, 10) : null;
  const methodSig = selector && selector !== "0x" ? await fourByteLookup("signatures", selector) : null;

  const logs: any[] = Array.isArray(receipt?.logs) ? receipt.logs : [];
  // Cap at 25 — a real bound on 4byte.directory calls fan-out for a tx with
  // an unusually large log count (e.g. a multicall/batch settlement), same
  // spirit as this repo's other external-API loops.
  const logsDecoded: DecodedLog[] = await Promise.all(
    logs.slice(0, 25).map(async (log): Promise<DecodedLog> => {
      const topic0 = (log.topics || [])[0] || null;
      const event = topic0 ? await fourByteLookup("event-signatures", topic0) : null;
      return { address: log.address, topic0, event };
    })
  );

  const txStatus: TxDecodeResult["status"] = !receipt
    ? "pending"
    : receipt.status === "0x1"
    ? "success"
    : receipt.status === "0x0"
    ? "failed"
    : "pending";

  const riskFlags: string[] = [];
  if (txStatus === "failed") {
    riskFlags.push("transaction reverted — nothing actually executed on-chain despite being mined");
  }
  for (const log of logs) {
    const topics: string[] = log.topics || [];
    if (topics[0] === APPROVAL_EVENT_TOPIC0 && topics.length >= 3 && typeof log.data === "string") {
      if (log.data.toLowerCase() === MAX_UINT256_DATA) {
        const spender = `0x${topics[2].slice(-40)}`;
        riskFlags.push(
          `unlimited ERC-20 approval granted to spender ${spender} — classic drainer pre-condition, only sign this for contracts you fully trust`
        );
      }
    }
  }

  const parts: string[] = [];
  parts.push(
    txStatus === "failed" ? "Transaction reverted." : txStatus === "pending" ? "Transaction not yet mined." : "Transaction succeeded."
  );
  if (methodSig) parts.push(`Called \`${methodSig}\` on ${tx.to}.`);
  else if (selector) parts.push(`Called an unrecognized method (selector ${selector}) on ${tx.to} — no 4byte.directory match.`);
  else if (input === "0x") parts.push(`Plain value transfer to ${tx.to}.`);
  const namedEvents = logsDecoded.filter((l) => l.event).map((l) => l.event!.split("(")[0]);
  if (namedEvents.length) parts.push(`Emitted: ${namedEvents.join(", ")}.`);

  return {
    tx_hash: txHash,
    chain_id: chainId,
    status: txStatus,
    from: tx.from ?? null,
    to: tx.to ?? null,
    value_wei: tx.value ?? null,
    method: selector ? { selector, signature: methodSig } : null,
    logs_decoded: logsDecoded,
    risk_flags: riskFlags,
    summary: parts.join(" "),
  };
}
