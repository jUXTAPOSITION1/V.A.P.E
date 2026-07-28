# skills/bsc_token_investigation.md

## when-to-use
Run when a BSC token address shows thin holder distribution, low liquidity, or unverified claims in news_reporter.py output; use before any market_data or wallet_trace follow-up to produce a numeric safety score and verdict.

## step-by-step procedure
1. Invoke `agents/investigate.py` with the target BSC address (e.g., `0x3C0541e68CE0F1F9073E4BA3Db81b730Eb614444` or `0x9a6Cb2C43A3454c8DB4e89e4e031FDcFC8769A02`).
2. Capture the raw score, verdict, and penalty list directly from the agent output (example penalties: -20 for <25 holders, -15 for top-10 control >85%, -25 for liquidity <$10, -10 for unaudited).
3. Cross-check the same address against `agents/news_reporter.py` intel-sweep tags for any matching "crypto markets" or "stablecoins" headlines; flag any headline-only claims lacking metrics.
4. Record final verdict and report path (e.g., `intel/investigations/investigation-20260728-001613-0x3C0541e6.md`).
5. If score <60, halt further tool calls; if 60-80, proceed only with `token_safety` and `market_data` wrappers.

## quality gates
- Score must be produced by `agents/investigate.py` with explicit penalty breakdown; no manual overrides.
- Verdict matches observed thresholds: REJECT at 0/100, CAUTION at 55/100.
- All cited news headlines must be tagged "thin-data" or "sparse-data" when body/metrics are absent.

## limitations
- Agent only evaluates on-chain distribution and liquidity at scan time; does not detect post-scan liquidity removal.
- Findings limited to BSC chain (chain id 56) and addresses with <10k holders.
- Expert review may disagree with agent verdict when holder count >9000 and trading history >100 days despite 100% top-holder concentration.

_Distilled 2026-07-28T08:40:57Z from real SKILLFORGE memory._
