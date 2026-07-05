/**
 * Port of agents/data_fetchers.py::get_contract_source() — Etherscan V2
 * unified API, works across Base/Ethereum/Arbitrum by chainid. Needs
 * ETHERSCAN_API_KEY (Worker secret); degrades to {error:"no_key"} exactly
 * like the Python version rather than failing the whole request.
 */
const ETHERSCAN_V2 = "https://api.etherscan.io/v2/api";

export interface ContractSource {
  error?: string;
  note?: string;
  verified?: boolean;
  contract_name?: string | null;
  compiler?: string | null;
  proxy?: boolean;
  implementation?: string | null;
  // Raw verified source (may be multi-file JSON-wrapped by Etherscan for
  // standard-json-input contracts) — additive field, existing callers only
  // ever read the fields above so this is safe. Mirrors
  // agents/data_fetchers.py::get_contract_source()'s source_code field,
  // used by the safety_preflight offering's frontier-LLM quick read.
  source_code?: string | null;
}

export async function getContractSource(address: string, chainId: number, apiKey?: string): Promise<ContractSource> {
  if (!apiKey) return { error: "no_key", note: "set ETHERSCAN_API_KEY for contract source" };
  const q = new URLSearchParams({
    chainid: String(chainId), module: "contract", action: "getsourcecode",
    address, apikey: apiKey,
  });
  try {
    const r = await fetch(`${ETHERSCAN_V2}?${q}`);
    const d: any = await r.json();
    if (d?.result) {
      const res = Array.isArray(d.result) ? d.result[0] : d.result;
      return {
        verified: Boolean(res.SourceCode),
        contract_name: res.ContractName ?? null,
        compiler: res.CompilerVersion ?? null,
        proxy: res.Proxy === "1",
        implementation: res.Implementation || null,
        source_code: res.SourceCode || null,
      };
    }
    return d;
  } catch (e: any) {
    return { error: String(e?.message || e) };
  }
}
