# VAPE SKILLFORGE Build — arbitrum hot-wallet-compromise forensics tracer

**Justification:** "AFX Bridge (exploit $24,150,000) (defillama-hack, fit 95, $24,150,000): Private Key Compromised on Arbitrum. Lead for incident response + forensics." and "Triple-A (exploit $9,700,000) (defillama-hack, fit 90, $9,700,000): Hot Wallet Compromise on Ethereum,Tron,Arbitrum." — neither of these map to any already-built item (arbitrum oracle manip tracer, layerzero oft, unlimited approval, etc.).

**Spec:** Python stdlib CLI (agents/ style) that ingests an Arbitrum tx hash or address list, pulls receipts/logs via RPC, flags patterns indicative of hot-wallet/private-key compromise (sudden large outflows to new EOAs, no prior interaction, exact nonce-0 transfers, funding from known mixer/bridge in same block window), outputs a compact JSON report with affected addresses, value moved, and first-hop recipients. Single-file script, no external deps beyond stdlib + optional web3.py if already in env; run as `python agents/arbitrum_hotwallet_tracer.py --tx 0x...`.

## Files generated
None — Builder produced no usable FILE blocks this cycle.

No PR opened (see log for why).
