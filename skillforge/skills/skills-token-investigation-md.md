# skills/token-investigation.md

## Token Safety Investigation

### When-to-use
Run before interacting with any ERC-20 on Polygon (137) or Ethereum (1) when holder concentration, mint authority, ownership, or liquidity lock status is unknown. Use on targets surfaced by hack_feed or market_data.

### Step-by-step procedure
1. `contract_recon --chain 137 --address 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` (or chain 1 equivalent) to map proxy/implementation and owner.
2. `token_safety --chain 137 --address 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` to extract mintable flag, top-holder distribution, and LP-lock percentage.
3. `agents/investigate.py --target 0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359 --chain 137` to aggregate penalties and produce verdict + report.
4. Cross-check any owner address with `wallet_trace --address [OWNER]` and recent `hack_feed` entries.
5. Record final score and verdict in intel/investigations/.

### Quality gates
- All 16 tools return verified (toolcheck outcome 16/16) before proceeding.
- Report must contain explicit numeric score (0-100) and one of {PROCEED, CAUTION, REJECT}.
- At minimum: proxy status, owner status, mint flag, top-10 holder %, LP-lock % must be populated.

### Limitations
- Does not cover code-level bugs (use slither/aderyn separately).
- Relies on public on-chain data only; unaudited or anonymous teams default to penalty.
- Liquidity-lock data is snapshot-based and can change after investigation timestamp.

_Distilled 2026-07-26T08:31:49Z from real SKILLFORGE memory._
