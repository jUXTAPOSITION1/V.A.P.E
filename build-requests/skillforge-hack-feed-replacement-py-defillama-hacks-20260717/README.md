# VAPE self-directed build — hack_feed_replacement.py (DeFiLlama /hacks fetcher + normalizer)

**Justification:** The only concrete gap signal is "hack_feed (recon) is BROKEN: Keyless DeFi exploit/hack feed (DeFiLlama /hacks): dated incidents, loss $, chain, technique. Scripts the security-sweep vertical." All bounty-radar entries are merely "Lead for incident response + forensics" on already-covered chains (Arbitrum, Base, Ethereum, etc.) and do not state any missing capability.

**Spec:** Python stdlib-only script (agents/hack_feed.py) that does a single requests.get to https://api.llama.fi/hacks, filters to last 90 days, extracts/normalizes fields (date, protocol, chain(s), technique, loss_usd), emits JSON + markdown table to stdout, and writes a dated snapshot under intel/hacks/. No external deps, fits agents/ Python rule, directly replaces the broken recon feed used by security-sweep.

**Security review:** review: 'open(' present (advisory); review: 'urllib.request' present (advisory); review: 'import os' present (advisory)

This is VAPE's own proposal, grounded in real Memory/tool-registry/investigation signals (see the PR description) — not applied automatically. A human reviews this PR and decides whether/how/where to integrate it.

## Files
- `agents/hack_feed.py`

## Generated-file verification (real compile/syntax check, not just pattern-matching)

- [OK] `agents/hack_feed.py` — py_compile OK
