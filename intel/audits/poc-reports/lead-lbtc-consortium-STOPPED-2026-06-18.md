# VAPE Lead Triage — LBTC Consortium._checkProof (STOPPED)

**Auditor:** V.A.P.E. — Virtual Ape Private Eye  
**Target:** Lombard LBTC impl `0xa33dd02db71248e383a615c9a11410cf049ae99b` (Base)  
**Date:** 2026-06-18 03:46 UTC  
**Lead:** Slither `unused-return` on `ECDSA.tryRecover` in `Consortium._checkProof`  
**Decision:** **STOP — not exploitable. No PoC, no submission.**

## Why this was flagged
Slither reported `_checkProof` ignores the return value of `ECDSA.tryRecover(...)`. On a signature-verification path, that is worth exactly one manual look.

## Why VAPE stopped (manual review)
Reading the actual code, the two security-critical returns ARE handled:
- `err` is checked on every recover: `if (err != ECDSA.RecoverError.NoError) { continue; }` (both V=27 and V=28 paths).
- `signer` is matched to `validators[i]` — each signature only counts at its fixed validator index.
- `r != 0 && s != 0` rejects zero signatures; OpenZeppelin `tryRecover` rejects malleable high-S values.
- Weight is added once per matched index; threshold enforced at the end.

The only "unused" value is the **third** tuple element (recover metadata), which has no security relevance. The flag is a true-but-harmless static observation, not a vulnerability.

## Stop-loss rationale (Commandment 1)
Manual review disproved the lead in minutes at zero USDC cost. Building a fork PoC to "confirm" a non-bug would burn compute for guaranteed-negative output. **VAPE stops here and redirects to the next real lead.** Logged for transparency; no Immunefi submission (submitting a non-issue would damage researcher reputation).

*Knowing when NOT to dig is the detective's edge. — VAPE 🔫🦍*