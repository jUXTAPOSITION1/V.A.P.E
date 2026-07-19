```markdown
# Token Investigation Workflow

**When-to-use**  
Run before any PROCEED decision on fresh or low-liquidity tokens on Base/BSC. Use when `token_safety` or `market_data` flags volatility, low holders, or new pairs.

**Step-by-step procedure**

1. Invoke the investigation wrapper on the target contract:  
   `agents/investigate.py --target 0xB33F6E70535584c2aCa18335305797C16f1ad589 --chain 56`

2. Capture the generated report path from metadata:  
   `intel/investigations/investigation-YYYYMMDD-HHMMSS-0xTARGET.md`

3. Cross-check with supporting verified tools:  
   `token_safety` (distribution/liquidity)  
   `market_data` (24h move, pair age)  
   `contract_recon` (audit/team signals)

4. Apply scoring gates directly from agent output:  
   - 0–49 → REJECT (thin distribution + fresh pair + volatility)  
   - 50–79 → CAUTION (requires manual review of owner privileges)  
   - 80–100 → PROCEED only if no single-EOA owner remains

5. Log verdict and broadcast ID for traceability:  
   `agents/broadcast.py` (auto-includes score and tags)

**Quality gates**  
- Must produce both numeric score and explicit verdict string.  
- All four risk factors (holders, liquidity, 24h move, pair age) must be present in report.  
- Toolcheck status ≥14/15 verified before execution.

**Limitations**  
- Agent output is static snapshot; does not detect post-launch owner renounces.  
- Single-EOA owner flag remains even on otherwise clean ERC20s (see BRIUN 90/100 case).  
- No on-chain simulation performed; pair with `foundry` only when score ≥80.
```

_Distilled 2026-07-19T08:25:12Z from real SKILLFORGE memory._
