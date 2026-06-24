# Skill: Free On-Chain & Market Recon (keyless, LLM-free)

**Tier:** recon
**Tools:** `tools/recon/base_rpc.sh`, `tools/recon/market_data.sh`
**Why:** When `web_search`/`xurl` are unavailable (missing API key) the intel sweep must still produce real numbers. These wrappers hit free, keyless endpoints.

## Base chain (public JSON-RPC — https://mainnet.base.org)
- `base_rpc.sh balance <addr>` — ETH balance (decimal)
- `base_rpc.sh nonce <addr>` — tx count / activity proxy
- `base_rpc.sh gas` — gas price in gwei
- `base_rpc.sh block` — latest block height
Note: Basescan/Etherscan V1 (`api.basescan.org`) is **deprecated** ("switch to V2"). Use raw RPC instead — no key needed.

## Market data (CoinGecko + DeFiLlama — keyless)
- `market_data.sh price <id,id>` — usd, 24h chg, vol, mcap (e.g. `virtual-protocol`, `bitcoin`, `ethereum`)
- `market_data.sh global` — BTC/ETH dominance + 24h total-mcap change
- `market_data.sh chaintvl Base` — DeFiLlama chain TVL

## Sentiment fallback
With no live X scrape, derive a quantitative sentiment score from market breadth: alt beta vs. BTC, total-mcap 24h change, dominance trend. Risk-off + alts underperforming BTC => Fear (2-4/10).

## Verified
2026-06-24T20:02Z — both wrappers run clean against live endpoints.
