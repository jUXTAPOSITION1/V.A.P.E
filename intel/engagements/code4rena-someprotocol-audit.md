# VAPE engagement brief — SomeProtocol Audit (code4rena)

- Lead: VAPE (performs audit + PoC + submission directly)
- Scope URL: https://code4rena.com/audits/x
- Max reward / pool: $100,000
- Auth: GitHub OAuth (jUXTAPOSITION1)
- Logs published to: jUXTAPOSITION1/V.A.P.E
- VAPE offering: deep_contract_audit
- Optional HACK reference (specialist backup only): exploit_simulation

## Execution checklist (VAPE)
- [ ] VAPE: sign in to code4rena with GitHub (account jUXTAPOSITION1) — prefer 'Sign in with GitHub' over email; no OTP needed.
- [ ] VAPE: open contest scope: https://code4rena.com/audits/x
- [ ] VAPE: clone scope repo / read in-scope contracts.
- [ ] VAPE: run vape_lab.py audit on each in-scope contract (Slither + manual review).
- [ ] VAPE: for each finding, build a Foundry fork PoC (vape_lab.py newpoc/poc).
- [ ] VAPE: write findings to platform template and submit before deadline.

## Finding report template
Title: <vuln> in <contract>.<fn>()
Severity: <C/H/M/L>
Impact: <funds at risk / who is affected>
PoC: vape-lab/test/<Target>_<Vuln>.t.sol (fork run, see poc-reports/)
Recommended fix: <code-level remediation>
