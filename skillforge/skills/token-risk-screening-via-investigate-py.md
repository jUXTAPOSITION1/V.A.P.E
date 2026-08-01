# Token Risk Screening via investigate.py

**When-to-use**  
Screen any ERC-20/ BEP-20 token on Polygon (137), BSC (56) or Base (8453) before liquidity provision, swaps or wallet interaction. Use when `token_safety` or `contract_recon` flags are unavailable or when a full 0-100 score with explicit rejection criteria is required.

**Step-by-step procedure**

1. Invoke the verified wrapper:  
   ```bash
   python agents/investigate.py --target <contract> --chain <id>
   ```
   Example:  
   ```bash
   python agents/investigate.py --target 0xC28475DE46305BDf8E8522Fc282CC13106812ccC --chain 137
   ```

2. Review the generated report at:  
   `intel/investigations/investigation-YYYYMMDD-HHMMSS-<addr>.md`

3. Apply the fixed scoring penalties observed in real runs:  
   - Mintable supply → -12  
   - Owner can change balances → -25  
   - Holders ≤ 31 → -20  
   - Top-10 non-LP control ≥ 95 % → -15  
   - Liquidity unlocked or < $25k → -15 to -25  
   - Pair age < 30 days → -5 to -15  
   - No audit / anonymous team → -10  

4. Emit verdict:  
   - Score < 50 → REJECT (record in hack_feed)  
   - 50-69 → CAUTION  
   - ≥ 70 → PROCEED only after additional `wallet_trace` and `market_data` checks

**Quality gates**  
- All 7 penalty categories must be enumerated in the report.  
- `confidence` field ≥ 0.9 (as produced by investigate.py).  
- Output file must exist under `intel/investigations/` before any downstream action.

**Limitations**  
- Wrapper only supports chains 137, 56, 8453.  
- Does not replace static analysis (slither/aderyn) or formal verification (halmos).  
- Scores are deterministic from on-chain metadata only; social or off-chain signals are ignored.

_Distilled 2026-08-01T08:26:37Z from real SKILLFORGE memory._
