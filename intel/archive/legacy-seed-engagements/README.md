# Legacy seed engagements — archived, not real VAPE output

Everything in this directory was moved here from `intel/engagements/`
(2026-07-13). It is pre-repo seed/example data from an earlier "ad hoc
Claude Code session" era — the same one flagged in
`agents/security_sweep.py`'s module docstring as having run without any
committed code until it silently stopped on 2026-07-01 with zero trace in
git history. A repo-wide search turns up no code, past or present, that
ever wrote to `intel/engagements/` — this content was never produced by
any of VAPE's real agents.

Concretely, none of it is real:

- `code4rena-someprotocol-audit.md` is a template stub with a placeholder
  protocol name ("SomeProtocol") and a fake scope URL
  (`https://code4rena.com/audits/x`) — never a real audit.
- The four `defillama-hack-*.md` files are drafted cold-outreach emails to
  real DeFi hack victims ("Hi Thorchain DEX ... security team"), signed
  from a personal gmail address, with no evidence any were ever actually
  sent through a real mail system.
- `hackenproof-smardex-smart-contracts.md` is a four-line stub.
- `engagement-log-legacy.jsonl` (renamed from `engagement-log.jsonl`)
  records these fabricated drafts as if they were completed actions, and
  references file paths on a different machine entirely
  (`/home/node/.openclaw/workspace/vape-intel/...`) — further confirming
  this is imported artifact from outside this repo's own runtime.

Kept here (not deleted) purely for provenance/history — see
`agents/engagements.py` for the real, automated replacement now populating
`intel/engagements/STATUS.md` and a genuine `engagement-log.jsonl`.
