# Token Risk Investigation

## When to Use
Evaluate new or low-history token contracts on Ethereum (chain 1), BSC (chain 56), or Polygon (chain 137) before interaction or allocation. Use when holder concentration, liquidity age/lock status, or upgradeability flags appear in initial scans.

## Step-by-Step Procedure
1. Invoke `agents/investigate.py` with target contract address and chain ID (examples: `0x2e5ef97C96D6a44CcB8Db9C30f2F5DCec04BB6f9` on 1, `0x5b650B618B988090A0D30831846cA3105B527d70` on 137).
2. Capture output fields: pair age, top-10 holder concentration (non-LP/burn), liquidity USD value and lock percentage, owner renouncement status, audit presence, and 24h volatility.
3. Cross-reference with `contract_recon` for proxy/implementation details and `token_safety` for tax/holder distribution confirmation.
4. Compute composite score from weighted deductions (pair <1 day: -15 to -25; top-10 concentration >80%: -15; 0% liquidity locked: -15; unaudited/anonymous: -10; owner not renounced: -10).
5. Map score to verdict: PROCEED (≥80), CAUTION (60-79), REJECT (<60).

## Quality Gates
- All high-impact flags (concentration ≥80%, liquidity <$15k, pair age <1 day, 0% lock) must be explicitly logged before verdict.
- Require at least two independent tool outputs (`contract_recon` + `token_safety`) to match `agents/investigate.py` findings.
- Reject if any single flag exceeds -20 deduction without mitigation evidence.

## Limitations
- Relies solely on on-chain snapshot at runtime; does not detect future owner actions or off-chain changes.
- No coverage for non-EVM chains or contracts without detectable liquidity pair.
- Verdict accuracy drops on tokens <7 days old due to insufficient holder distribution data.

_Distilled 2026-07-29T08:46:48Z from real SKILLFORGE memory._
