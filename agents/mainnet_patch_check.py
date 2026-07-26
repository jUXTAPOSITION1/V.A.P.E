"""
VAPE Mainnet Patch Check — revives the "Mainnet Patch Status Check" cron
(see intel/reports/mainnet-patch-check-2026-06-10.md), which only ever ran
once. That report's actual finding was: AgentNftV2::addValidator() (a real,
known, singleton contract at a specific verified Base address) had a
Code4rena HIGH finding (H-01, missing access control) that appeared FIXED
on mainnet as of the one check that was ever run. This script makes that a
real recurring re-verification instead of a one-time snapshot, using the
exact same address quoted in that historical report.

Real data: agents/data_fetchers.get_contract_source() — real verified
Solidity source from Etherscan V2/Basescan (needs ETHERSCAN_API_KEY;
degrades honestly if unset, same as every other optional key in this repo).
Patch status is a DETERMINISTIC text-pattern check against the real fetched
source, not an LLM guess — but this is a lightweight static check, not a
real audit, so findings are reported as a starting point for a human/deep-
dive follow-up, never as a definitive "safe" verdict. One bounded web
search adds real outside-research freedom this script previously had none
of; a frontier-tier (Grok 4.1 Fast first — see agents/intel_common.py's
grok_analysis()) Analyst Briefing section interprets the pattern-check
result plus that research, still never overriding the deterministic verdict.

Scope note: the historical report also flagged AgentToken-level issues
(setProjectTaxRates, distributeTaxTokens), but AgentToken is clone-based —
there's no single canonical address to re-check, and this script won't
fabricate one. Those remain a manual/deep-dive item, exactly as the
original report scoped them.

Usage: python agents/mainnet_patch_check.py
"""
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import get_contract_source  # noqa: E402
from agents import intel_common as ic  # noqa: E402

# Real address quoted in intel/reports/mainnet-patch-check-2026-06-10.md —
# AgentNftV2's implementation on Base, per that report's Basescan lookup.
AGENT_NFT_V2_IMPL = "0xdE8299ba9a20f6aca7516735FcAe3E04F8ba417b"

CHECKS = [
    {
        "id": "H-01 addValidator access control",
        "function": "addValidator",
        "safe_patterns": (r"onlyRole", r"onlyOwner", r"onlyValidatorAdmin"),
    },
    {
        "id": "setDAO self-replacement guard",
        "function": "setDAO",
        "safe_patterns": (r"onlyRole", r"require\s*\(\s*_msgSender\(\)\s*==",),
    },
]


def _extract_function_body(source, fn_name, window=400):
    """Grabs the text starting at 'function <fn_name>(' through `window`
    chars after it — enough to see the modifier list and first require()
    without needing a real Solidity parser."""
    m = re.search(rf"function\s+{re.escape(fn_name)}\s*\(", source)
    if not m:
        return None
    return source[m.start():m.start() + window]


def check_patch_status(source_code):
    if not source_code:
        return []
    results = []
    for check in CHECKS:
        snippet = _extract_function_body(source_code, check["function"])
        if snippet is None:
            results.append({**check, "status": "FUNCTION NOT FOUND", "snippet": None})
            continue
        matched = any(re.search(p, snippet) for p in check["safe_patterns"])
        results.append({
            **check,
            "status": "LIKELY PATCHED" if matched else "NEEDS REVIEW — no access-control pattern found",
            "snippet": snippet[:250],
        })
    return results


def run():
    # Previously this script only ever ran the deterministic pattern check
    # below — zero outside research. One bounded web search gives it real
    # freedom to catch anything the static pattern check can't see (a fresh
    # public disclosure, a since-published PoC, a community thread flagging
    # a bypass of the very access-control pattern the check looks for).
    search = ic.web_search_snippets("AgentNftV2 Virtuals Protocol vulnerability exploit disclosure", max_results=6)

    src = get_contract_source(AGENT_NFT_V2_IMPL, chainid=8453)

    if src.get("error") == "no_key":
        checks = []
        note = "ETHERSCAN_API_KEY not set — cannot fetch verified source this cycle."
    elif src.get("error"):
        checks = []
        note = f"Contract source fetch failed: {src.get('error')}"
    elif not src.get("verified") or not src.get("source_code"):
        checks = []
        note = "Contract is not verified or has no source available."
    else:
        checks = check_patch_status(src["source_code"])
        note = None

    check_rows = "\n".join(
        f"| {c['id']} | {c['status']} |"
        for c in checks
    ) or "| — | could not run this cycle |"

    any_needs_review = any(c["status"] != "LIKELY PATCHED" for c in checks)
    if not checks:
        verdict = "UNKNOWN"
    elif any_needs_review:
        verdict = "NEEDS REVIEW"
    else:
        verdict = "ALL CLEAR"

    briefing = ic.grok_analysis(
        "smart-contract security analyst",
        (
            f"VERDICT (deterministic pattern check, do not change): {verdict}\n"
            f"Contract: AgentNftV2 implementation {AGENT_NFT_V2_IMPL} (Base, chain 8453)\n"
            f"Pattern-check results:\n{check_rows}\n\n"
            f"Web research this cycle ({search.get('provider') or 'unavailable'}):\n"
            + ("\n".join(f"- {r['title']} ({r['url']}): {r['snippet']}" for r in search.get("results", [])) or "none available")
        ),
        instructions=(
            "Write the 'Analyst Briefing' section of this mainnet patch-status report. Interpret what "
            "the pattern-check status plus this cycle's web research actually implies — call out "
            "specifically if the web research surfaces anything (a disclosure, a discussion, a PoC) "
            "the static pattern check wouldn't catch, and say plainly if it doesn't. Do not declare a "
            "contract 'safe' — a NEEDS REVIEW result always warrants a real human look regardless of "
            "what the web research does or doesn't show."
        ),
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""# Mainnet Patch Status Check — Virtuals Protocol AgentNftV2

**Date:** {stamp}
**Contract:** `{AGENT_NFT_V2_IMPL}` (AgentNftV2 implementation, Base 8453)
**Source:** live on-chain verified source fetch

---

## VERDICT: {verdict}

{note or f"Re-checked {len(checks)} previously-flagged item(s) from the original Code4rena audit + attack-surface review."}

---

## Patch Status (real, from live verified source)

| Finding | Status |
|---------|--------|
{check_rows}

---

## Analyst Briefing

{briefing}

---

{ic.format_search_section("Web Signals — AgentNftV2 Disclosure Watch", search)}

---

## Method & Limitations

This is a lightweight, deterministic text-pattern check against the real verified
Solidity source — it looks for an access-control modifier (`onlyRole`, `onlyOwner`, etc.)
in the ~400 characters following each flagged function's signature. It is **not** a real
audit: a "LIKELY PATCHED" result means an authorization pattern is present, not that the
authorization logic is correct. A "NEEDS REVIEW" result means no such pattern was found in
that window and warrants a real human look, not that a vulnerability is confirmed.

**Out of scope (unchanged from the original 2026-06-10 report):** AgentToken's
`setProjectTaxRates`/`distributeTaxTokens` findings are clone-based — there is no single
canonical address to re-check automatically. That remains a manual/deep-dive item.

---

## Sources
- Etherscan V2 / Basescan verified source (`get_contract_source`)
- Live web search ({search.get('provider') or 'unavailable'})
- Prior finding: `intel/reports/mainnet-patch-check-2026-06-10.md`, `intel/reports/attack-surface-map-2026-06-10.md`
- Analyst Briefing: VAPE

---

*Report generated by `agents/mainnet_patch_check.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} as a
real recurring re-check of the original one-time 2026-06-10 finding.*
"""
    path = ic.write_report("mainnet-patch-check", body)
    summary = f"Mainnet patch re-check: {verdict} on AgentNftV2 ({AGENT_NFT_V2_IMPL})."
    ic.log_sweep_memory("agents/mainnet_patch_check.py", verdict, summary, path, tags=["virtuals", "patch-check"])
    print(f"[mainnet_patch_check] {verdict} — wrote {os.path.relpath(path, ic.ROOT)}")
    return {"verdict": verdict, "path": path}


if __name__ == "__main__":
    run()
