# VAPE SKILLFORGE Build — hack_feed_replacement.py (DeFiLlama /hacks fetcher + normalizer)

**Justification:** The only concrete gap signal is "hack_feed (recon) is BROKEN: Keyless DeFi exploit/hack feed (DeFiLlama /hacks): dated incidents, loss $, chain, technique. Scripts the security-sweep vertical." All bounty-radar entries are merely "Lead for incident response + forensics" on already-covered chains (Arbitrum, Base, Ethereum, etc.) and do not state any missing capability.

**Spec:** Python stdlib-only script (agents/hack_feed.py) that does a single requests.get to https://api.llama.fi/hacks, filters to last 90 days, extracts/normalizes fields (date, protocol, chain(s), technique, loss_usd), emits JSON + markdown table to stdout, and writes a dated snapshot under intel/hacks/. No external deps, fits agents/ Python rule, directly replaces the broken recon feed used by security-sweep.

## Files generated
- `agents/hack_feed.py`

PR opened: https://github.com/jUXTAPOSITION1/V.A.P.E/pull/188
