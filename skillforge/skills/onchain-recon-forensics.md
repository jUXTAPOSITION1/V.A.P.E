# Skill: On-Chain Recon & Forensics

**Tier:** recon · **Tools:** base_rpc, market_data, token_safety, wallet_trace, contract_recon · **Status:** active

## When to use
First-touch intelligence on any address, token, or contract before deeper audit/fuzzing.
Powers VAPE's forensics + market-intel ACP offerings and the daily intel sweeps.
Keyless tools run anywhere; Etherscan-backed tools need `ETHERSCAN_API_KEY`.

## Tool map
| Tool | Key? | Use |
|------|------|-----|
| `base_rpc.sh` | no | Live Base state: balance, nonce, gas, block (public RPC) |
| `market_data.sh` | no | Price/mcap/vol (CoinGecko) + dominance + chain TVL (DeFiLlama) |
| `token_safety.sh` | no | Honeypot/tax/mint/owner (GoPlusLabs) + DEX liquidity (DexScreener) → PROCEED/CAUTION/REJECT |
| `wallet_trace.sh` | ETHERSCAN | tx history, ERC-20 flows, first-funding source (multichain V2) |
| `contract_recon.sh` | ETHERSCAN | verification status, source, ABI, creator (multichain V2) |

## Procedure (real-data-only)
1. **Token triage:** `token_safety.sh check <chainId> <addr>` for a fast keyless verdict; `dex` for liquidity depth.
2. **Contract provenance:** `contract_recon.sh verified <chainId> <addr>` → if UNVERIFIED, note limited-review;
   `creation` for the deployer, then `wallet_trace.sh first` on the deployer for funding origin.
3. **Wallet forensics:** `wallet_trace.sh txs|erc20 <chainId> <addr>` to map flows; cluster counterparties.
4. **Market context:** `market_data.sh price <ids>` + `chaintvl <Chain>` for the macro frame.
5. Record real findings (with tx hashes / addresses) to `skillforge/memory/findings.jsonl`.

## Chain IDs
Base 8453 · Ethereum 1 · Arbitrum 42161 · Optimism 10 · Polygon 137 · BNB 56.

## Quality gates
- Every claim cites a real tx hash, address, or API field. No invented balances or flows.
- Etherscan V2 has NO keyless tier — key-dependent tools fail loudly, never fabricate.
- Respect rate limits: GoPlus/CoinGecko/DeFiLlama free tiers — batch, don't hammer.

## Known limitations
- Public Base RPC can rate-limit under load → back off, or use a dedicated endpoint.
- GoPlus returns empty for very new/unindexed tokens → treat as REJECT (unknown = unsafe).

_Phase 3 tier. base_rpc + market_data were auto-built by VAPE's own sweep; rest added in Phase 3._
