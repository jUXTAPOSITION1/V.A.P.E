# Deployer Wallet History Recon

**When-to-use**  
Bounty-cycle analysis (agents/run.py) returns REJECT or CAUTION on unverified deployer (e.g., CATE 20260803_202705) where exploit hypothesis centers on post-launch mint/ownership calls; evidence is limited to on-chain flags with no deployer identity or prior deployments.

**Step-by-step procedure**  
1. Extract deployer address from contract_recon output on the target token.  
2. Run `wallet_trace` on the deployer address with focus on creation transactions and prior contract deployments.  
3. Execute `base_rpc` to fetch recent Transfer events and ownership-related calls from the deployer.  
4. Cross-reference results against hack_feed for any overlapping malicious patterns (price manipulation, malicious Set).  
5. Feed findings back into agents/investigate.py to update verdict and confidence.

**Quality gates**  
- 16/16 tools verified (toolcheck outcome) before starting.  
- At least one prior deployment or ownership call identified, or explicit confirmation of zero history.  
- Updated report written to reports/bounty_report_*.md with new confidence score.

**Limitations**  
No Slither/aderyn/mythril output available in cycle; works only on chains supported by base_rpc and wallet_trace; thin evidence remains if no on-chain history exists.

_Distilled 2026-08-04T08:44:20Z from real SKILLFORGE memory._
