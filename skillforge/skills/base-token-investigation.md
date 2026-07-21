# Base Token Investigation

**When-to-use**  
Investigating Base-chain tokens (chain 8453) that return CAUTION verdicts (e.g. cbBTC at 0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf scoring 74/100) with flags for upgradeable proxies, unrenounced ownership, or missing pair-creation timestamps.

**Step-by-step procedure**  
1. Run `agents/investigate.py` targeting the contract address on chain 8453.  
2. Pipe results through `token_safety` and `contract_recon` wrappers for proxy/owner checks.  
3. Cross-reference with `base_rpc` for on-chain state and `market_data` for TVL context.  
4. Log verdict and report path (e.g. `intel/investigations/investigation-20260720-130922-0xcbB7C000.md`).  
5. Feed summary to `agents/broadcast.py` for community intel.

**Quality gates**  
- All 16 verified tools must pass toolcheck before execution.  
- Score must be reproducible across two consecutive runs within 0.75 confidence.  
- Report must include at minimum the three flags shown in real cbBTC finding.

**Limitations**  
- No pair-creation timestamp available prevents track-record length calculation.  
- Owner not renounced remains actionable only via on-chain governance checks.  
- Applies only to Base (8453); Arbitrum/OP findings require separate tracer.

_Distilled 2026-07-21T08:35:27Z from real SKILLFORGE memory._
