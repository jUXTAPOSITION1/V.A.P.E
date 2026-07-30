# BSC Serial Deployer Token Screening

**When-to-use**  
Screen fresh BSC (chain 56) token launches showing mintable supply, <25 holders, or 0% locked liquidity to detect repeat deployer campaigns before interaction.

**Step-by-step procedure**  
1. Execute `contract_recon` on the token address to extract deployer, pair age, liquidity lock status, and holder distribution.  
2. Run `token_safety` on the same address to confirm mint functions, tax flags, and source verification status.  
3. Feed the deployer address into `wallet_trace` to retrieve prior contract creations and historical verdicts.  
4. Query `hack_feed` with the deployer address to surface matching prior REJECT/CAUTION records.  
5. Cross-check results against `market_data` for TVL and age signals if a pair exists.  

**Quality gates**  
- All four tools must return data; any missing field triggers manual `base_rpc` follow-up.  
- Verdict only issued when deployer history + holder concentration + liquidity lock all align with documented REJECT patterns.  
- Output written to `intel/investigations/investigation-*.md` with explicit score breakdown.  

**Limitations**  
Covers only BSC chain 56; unverified sources and <5 holder distributions reduce confidence below 0.9. No coverage for non-EVM chains or verified audited contracts.

_Distilled 2026-07-30T08:33:38Z from real SKILLFORGE memory._
