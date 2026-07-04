/**
 * Alchemy-backed Base mainnet reads: full ERC-20 token auto-discovery (via
 * `alchemy_getTokenBalances`, which covers far more tokens than the site's
 * curated `base-tokens.json` list) and NFT holdings (via the NFT v3 REST
 * API). Kept server-side only — `ALCHEMY_API_KEY` is a Worker secret, never
 * shipped to client JS, unlike the public `mainnet.base.org` RPC the site
 * falls back to when this isn't configured.
 */
interface AlchemyEnv {
  ALCHEMY_API_KEY?: string;
}

function rpcUrl(env: AlchemyEnv): string {
  return `https://base-mainnet.g.alchemy.com/v2/${env.ALCHEMY_API_KEY}`;
}

function nftBaseUrl(env: AlchemyEnv): string {
  return `https://base-mainnet.g.alchemy.com/nft/v3/${env.ALCHEMY_API_KEY}`;
}

interface RpcCall {
  method: string;
  params: unknown[];
}

async function batchRpc(env: AlchemyEnv, calls: RpcCall[]): Promise<unknown[]> {
  const body = calls.map((call, i) => ({ jsonrpc: "2.0", id: i, method: call.method, params: call.params }));
  const res = await fetch(rpcUrl(env), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Alchemy RPC HTTP ${res.status}`);
  const json = (await res.json()) as Array<{ id: number; result?: unknown; error?: { message: string } }>;
  const byId = Array.isArray(json) ? json : [json as any];
  return calls.map((_, i) => {
    const entry = byId.find((r) => r.id === i);
    if (!entry) throw new Error("Alchemy RPC: missing batch response");
    if (entry.error) throw new Error(entry.error.message);
    return entry.result;
  });
}

export interface PortfolioToken {
  contractAddress: string;
  symbol: string;
  name: string;
  decimals: number;
  balance: number;
  logo?: string;
}

export interface Portfolio {
  ethBalance: number;
  tokens: PortfolioToken[];
}

interface AlchemyTokenBalanceEntry {
  contractAddress: string;
  tokenBalance: string | null;
}

interface AlchemyTokenMetadata {
  name: string | null;
  symbol: string | null;
  decimals: number | null;
  logo: string | null;
}

/** Full auto-discovered ETH + ERC-20 holdings for `address` on Base mainnet. */
export async function getPortfolio(env: AlchemyEnv, address: string): Promise<Portfolio> {
  const [ethBalanceHex, tokenBalancesResult] = (await batchRpc(env, [
    { method: "eth_getBalance", params: [address, "latest"] },
    { method: "alchemy_getTokenBalances", params: [address, "erc20"] },
  ])) as [string, { tokenBalances: AlchemyTokenBalanceEntry[] }];

  const ethBalance = Number(BigInt(ethBalanceHex)) / 1e18;
  const nonzero = (tokenBalancesResult.tokenBalances || []).filter(
    (t) => t.tokenBalance && BigInt(t.tokenBalance) > 0n
  );
  if (!nonzero.length) return { ethBalance, tokens: [] };

  const metadata = (await batchRpc(
    env,
    nonzero.map((t) => ({ method: "alchemy_getTokenMetadata", params: [t.contractAddress] }))
  )) as AlchemyTokenMetadata[];

  const tokens: PortfolioToken[] = nonzero.map((t, i) => {
    const meta = metadata[i] || { name: null, symbol: null, decimals: null, logo: null };
    const decimals = typeof meta.decimals === "number" ? meta.decimals : 18;
    // Precision loss above 2^53 is acceptable here — display-only balances at
    // normal token-decimal scales, same tradeoff already made in profile.js.
    const balance = Number(BigInt(t.tokenBalance as string)) / Math.pow(10, decimals);
    return {
      contractAddress: t.contractAddress,
      symbol: meta.symbol || "?",
      name: meta.name || "Unknown token",
      decimals,
      balance,
      logo: meta.logo || undefined,
    };
  });

  return { ethBalance, tokens };
}

export interface OwnedNft {
  contractAddress: string;
  tokenId: string;
  name: string;
  collectionName?: string;
  image?: string;
}

interface AlchemyNftResponse {
  ownedNfts: Array<{
    contract: { address: string; name?: string };
    tokenId: string;
    name?: string;
    image?: { cachedUrl?: string; thumbnailUrl?: string; originalUrl?: string };
  }>;
}

/** NFTs owned by `address` on Base mainnet, newest collection metadata Alchemy has indexed. */
export async function getNftsForOwner(env: AlchemyEnv, address: string): Promise<OwnedNft[]> {
  const url = `${nftBaseUrl(env)}/getNFTsForOwner?owner=${address}&withMetadata=true&pageSize=100`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Alchemy NFT API HTTP ${res.status}`);
  const json = (await res.json()) as AlchemyNftResponse;
  return (json.ownedNfts || []).map((n) => ({
    contractAddress: n.contract.address,
    tokenId: n.tokenId,
    name: n.name || (n.contract.name ? `${n.contract.name} #${n.tokenId}` : `#${n.tokenId}`),
    collectionName: n.contract.name,
    image: n.image?.cachedUrl || n.image?.thumbnailUrl || n.image?.originalUrl,
  }));
}

export interface EarliestTransfer {
  timestamp: number; // unix seconds
  value: number; // token units (already decimal-adjusted by Alchemy)
}

interface AlchemyTransfersResponse {
  transfers: Array<{ metadata?: { blockTimestamp?: string }; value?: number | null }>;
}

/**
 * The single earliest incoming ERC-20 transfer of `contractAddress` to
 * `address`, if any — used as a lightweight, single-call proxy for "when
 * was this token first acquired" (see lib/costBasis.ts). Deliberately not a
 * full transfer history: `alchemy_getAssetTransfers` with `order: "asc"` and
 * `maxCount: 1` returns just the first match directly, one call per token
 * instead of paging through everything.
 */
export async function getEarliestIncomingTransfer(env: AlchemyEnv, address: string, contractAddress: string): Promise<EarliestTransfer | null> {
  const res = await fetch(rpcUrl(env), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "alchemy_getAssetTransfers",
      params: [{
        toAddress: address,
        contractAddresses: [contractAddress],
        category: ["erc20"],
        order: "asc",
        maxCount: "0x1",
        withMetadata: true,
        excludeZeroValue: true,
      }],
    }),
  });
  if (!res.ok) throw new Error(`Alchemy RPC HTTP ${res.status}`);
  const json = (await res.json()) as { result?: AlchemyTransfersResponse; error?: { message: string } };
  if (json.error) throw new Error(json.error.message);
  const transfer = json.result?.transfers?.[0];
  if (!transfer || typeof transfer.value !== "number" || !transfer.metadata?.blockTimestamp) return null;
  return { timestamp: Math.floor(new Date(transfer.metadata.blockTimestamp).getTime() / 1000), value: transfer.value };
}

interface NetworkStatus {
  blockNumber: number;
  gasPriceGwei: number;
}

/** Cheap Base mainnet block/gas read via Alchemy, for reliability over the public RPC. */
export async function getNetworkStatus(env: AlchemyEnv): Promise<NetworkStatus> {
  const [blockHex, gasHex] = (await batchRpc(env, [
    { method: "eth_blockNumber", params: [] },
    { method: "eth_gasPrice", params: [] },
  ])) as [string, string];
  return {
    blockNumber: Number(BigInt(blockHex)),
    gasPriceGwei: Number(BigInt(gasHex)) / 1e9,
  };
}
