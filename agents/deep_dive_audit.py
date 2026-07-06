#!/usr/bin/env python3
"""
VAPE Deep-Dive Bounty Audit — the 50 USDC / 24h-SLA premium offering.

The cheapest 6 x402 offerings and agents/investigate.py's free auto-cycle are all
deliberately zero/light-LLM, keyless-first, sub-5-minute checks. This is the other
end of the spectrum: a real frontier-tier model (agents/llm.py::ask_frontier() —
Gemini 2.5 Pro, Groq as the automatic fallback) reads the contract's ACTUAL verified
source text and reasons about specific vulnerability classes line-by-line, on top of
every recon signal agents/investigate.py already gathers (GoPlus, DexScreener, on-chain
presence, hack-technique correlation, public web reputation). Slither runs too, for
real, if it's already on PATH in the environment this executes in — never a hard
dependency, since a fresh multi-minute toolchain install has no place in a script whose
whole point is a reliable result, not gambling on a slow install succeeding.

"24h SLA" is a turnaround promise to the buyer, not a literal runtime — this completes
in one run (recon + optional Slither + one frontier LLM call), matching
intel/audits/poc-reports/'s existing hand-written audit format and rigor (see e.g.
audit-aerodrome-aero-2026-06-18.md: real tool output, honest triage of false positives,
explicit methodology) so the automated version holds the same bar.

Fulfillment paths:
  - ACP: scripts/acp-monitor/HANDLER_BRIEF.md maps the `bounty_deep_dive` offering to
    this script — the host-side reasoning handler runs it and submits the report as
    the deliverable.
  - x402: worker/src/index.ts's /scan/bounty_deep_dive route triggers
    .github/workflows/deep-dive-bounty.yml (workflow_dispatch) with the target address,
    which runs this script and commits the report — a real async-job pattern, since a
    multi-tool audit can't fit inside a serverless request/response window.

CLI:
  python -m agents.deep_dive_audit --address 0x... [--chain 8453] [--callback-url URL]
"""
import argparse
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

AUDIT_DIR = os.path.join(ROOT, "intel", "audits", "poc-reports")

try:
    from agents import investigate as inv
    from agents import data_fetchers as DF
    from agents.llm import ask_frontier
except Exception:
    import investigate as inv
    import data_fetchers as DF
    from llm import ask_frontier


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_safe_callback_url(url):
    """callback_url is attacker-influenced (an x402 buyer's own query param,
    passed through unvalidated by the worker) and this script POSTs to it from
    a GitHub Actions runner — block the obvious SSRF targets (cloud metadata
    endpoints, loopback, link-local, private ranges) rather than blindly
    fetching whatever URL a buyer supplies. Not a complete SSRF defense (DNS
    rebinding, redirects, etc. are out of scope for this), just the cheap,
    high-value checks."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


def _run_slither(address, chain, timeout=180):
    """Best-effort real static analysis — only if slither is already installed on
    PATH (e.g. via skillforge/toolcheck.py's cache) and an Etherscan key is set, so
    it can fetch + compile by address directly. Never a hard dependency: a slow
    fresh install has no place in a script whose value is a reliable result."""
    if not shutil.which("slither"):
        return {"ran": False, "reason": "slither not installed in this environment this run"}
    key = os.getenv("ETHERSCAN_API_KEY")
    if not key:
        return {"ran": False, "reason": "no ETHERSCAN_API_KEY — slither needs it to fetch+compile by address"}
    try:
        p = subprocess.run(
            ["slither", address, "--etherscan-apikey", key, "--json", "-"],
            capture_output=True, text=True, timeout=timeout,
        )
        try:
            data = json.loads(p.stdout)
        except Exception:
            return {"ran": True, "ok": False, "reason": f"slither produced no valid JSON (rc={p.returncode})",
                    "raw_tail": (p.stderr or p.stdout or "")[-500:]}
        detectors = ((data.get("results") or {}).get("detectors")) or []
        counts = {}
        for d in detectors:
            sev = d.get("impact", "Informational")
            counts[sev] = counts.get(sev, 0) + 1
        findings = [{"impact": d.get("impact"), "check": d.get("check"),
                     "description": (d.get("description") or "")[:300]} for d in detectors[:30]]
        return {"ran": True, "ok": True, "counts": counts, "findings": findings, "total": len(detectors)}
    except subprocess.TimeoutExpired:
        return {"ran": True, "ok": False, "reason": f"slither timed out after {timeout}s"}
    except Exception as e:
        return {"ran": True, "ok": False, "reason": str(e)}


FRONTIER_SYSTEM = """You are VAPE, an autonomous on-chain security auditor, performing a PAID
24-hour-SLA deep-dive bug bounty audit. This is VAPE's premium tier — the highest rigor
VAPE offers. Real money is on the line; be precise, evidence-based, and honest.

Rules:
- Base every claim on the ACTUAL verified source code and recon data given below — never
  invent function names, line numbers, or behavior you weren't shown.
- Reason explicitly through these vulnerability classes against the real code: reentrancy,
  access control (owner/role gating), oracle manipulation / price feed trust, integer
  overflow/precision loss, upgrade/proxy risk (storage collisions, unprotected
  initializers), unbounded loops / DoS, front-running / MEV surface, and any honeypot/
  rug mechanics GoPlus already flagged.
- If source code was not available, say so plainly and reason only from the real recon
  data provided — do not fabricate a source-level finding.
- Cross-reference any static-analysis (Slither) findings given — confirm, refute, or
  add context; don't just restate them.
- Distinguish real, exploitable findings from theoretical/low-severity noise, the same
  way a human auditor would triage away known false positives (e.g. standard-library
  math functions) rather than inflating a verdict off raw tool count.
- End with a clear PROCEED/CAUTION/REJECT verdict and a short list of what a human
  reviewer should still manually verify before relying on this report.

Output plain Markdown: an Executive Summary, then a section per vulnerability class you
found evidence for (skip classes with nothing to say rather than padding), then
"Recommended Human Follow-up".
"""


def build_prompt(address, chain, gp, dex, onchain, src, corr, web_rep, slither_result):
    parts = [f"=== TARGET ===\naddress: {address}\nchain: {chain}"]
    parts.append(f"=== GOPLUS TOKEN SECURITY (real) ===\n{json.dumps(gp, indent=2)[:2000]}")
    parts.append(f"=== DEXSCREENER MARKET DATA (real) ===\n{json.dumps(dex, indent=2)[:1000]}")
    parts.append(f"=== ON-CHAIN PRESENCE (real, Base RPC) ===\n{json.dumps(onchain, indent=2)}")
    parts.append(f"=== CONTRACT VERIFICATION (real, Etherscan V2) ===\n"
                 f"verified: {src.get('verified')}, name: {src.get('contract_name')}, "
                 f"compiler: {src.get('compiler')}, proxy: {src.get('proxy')}, "
                 f"implementation: {src.get('implementation')}")
    if src.get("source_code"):
        parts.append(f"=== VERIFIED SOURCE CODE (real, truncated to fit context) ===\n"
                     f"{src['source_code'][:40000]}")
    else:
        parts.append("=== VERIFIED SOURCE CODE ===\nNOT AVAILABLE — contract unverified or no "
                     "ETHERSCAN_API_KEY set. Do not fabricate source-level findings; reason "
                     "only from the other real recon data here.")
    if slither_result.get("ran") and slither_result.get("ok"):
        parts.append(f"=== SLITHER STATIC ANALYSIS (real, {slither_result['total']} raw findings) ===\n"
                     f"Severity counts: {slither_result['counts']}\n"
                     f"{json.dumps(slither_result['findings'], indent=2)[:3000]}")
    else:
        parts.append(f"=== SLITHER STATIC ANALYSIS ===\nNot available this run: "
                     f"{slither_result.get('reason', 'unknown')}")
    if corr:
        parts.append("=== RECENT-HACK TECHNIQUE CORRELATION (real, DeFiLlama feed) ===\n"
                     + "\n".join(f"- {c}" for c in corr))
    if web_rep and web_rep.get("hits"):
        parts.append("=== PUBLIC WEB REPUTATION FLAGS (real search results) ===\n"
                     + "\n".join(f"- {h}" for h in web_rep["hits"]))
    return "\n\n".join(parts)


def run_audit(address, chain="8453", callback_url=None):
    address = address.strip()
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return {"error": f"invalid address: {address}"}

    print(f"[deep_dive_audit] target {address} (chain {chain})")
    gp = inv.goplus_security(address, chain)
    # Real bug fixed here: these two previously always defaulted to Base
    # regardless of the requested `chain` — a paid deep-dive on any other
    # chain would silently check Base's on-chain state / DexScreener pair
    # instead of the actual target's.
    dex = inv.dexscreener(address, chain)
    onchain = inv.onchain_presence(address, chain)
    src = DF.get_contract_source(address, int(chain))
    if not isinstance(src, dict):
        src = {"error": "contract source lookup failed"}
    corr = inv.hack_correlation(gp)
    prelim_sym = dex.get("symbol") or src.get("contract_name") or "unknown"
    web_rep = inv.web_reputation_check(prelim_sym, address)
    slither_result = _run_slither(address, chain)

    # Reuse investigate.py's scoring engine for a baseline consistent with every other
    # VAPE verdict — the frontier LLM pass adds depth on top, it doesn't replace this.
    verif_for_score = {"checked": "error" not in src, "verified": src.get("verified"),
                       "name": src.get("contract_name"), "compiler": src.get("compiler"),
                       "proxy": src.get("proxy"), "implementation": src.get("implementation")}
    deployer_repeat = inv._deployer_repeat_offender(gp.get("creator_address"), chain, address)
    score, verdict, reasons, positive_signals = inv.score(gp, dex, onchain, verif_for_score, web_rep, deployer_repeat)

    sym = dex.get("symbol") or src.get("contract_name") or "unknown"
    prompt = build_prompt(address, chain, gp, dex, onchain, src, corr, web_rep, slither_result)
    try:
        narrative, provider = ask_frontier(FRONTIER_SYSTEM, prompt, max_tokens=3000, temperature=0.3)
    except Exception as e:
        narrative, provider = f"[frontier LLM unavailable this cycle: {e}]", None

    os.makedirs(AUDIT_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = re.sub(r"[^a-z0-9]+", "-", sym.lower()).strip("-") or address[:10]
    path = os.path.join(AUDIT_DIR, f"audit-deep-dive-{slug}-{stamp}.md")

    L = []
    L.append(f"# VAPE Deep-Dive Bounty Audit — {sym}")
    L.append("")
    L.append(f"**Target:** `{address}` (chain {chain})  ")
    L.append(f"**Date:** {now_iso()}  ")
    L.append(f"**Engine:** Frontier LLM ({provider or 'unavailable'}) + real recon"
             f"{' + Slither static analysis' if slither_result.get('ok') else ''}  ")
    L.append(f"**Baseline Verdict:** {verdict} ({score}/100 — same scoring engine as every "
             "VAPE investigation, for consistency)")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## AI Deep-Dive Analysis")
    L.append(narrative)
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Baseline Recon (same checks as every VAPE investigation)")
    L.append("### Verdict Rationale")
    for r in reasons or ["No risk penalties triggered — clean across all automated checks."]:
        L.append(f"- {r}")
    L.append("")
    L.append("### Positive Signals")
    for p in positive_signals or ["None found."]:
        L.append(f"- {p}")
    L.append("")
    L.append("## Static Analysis (Slither)")
    if slither_result.get("ok"):
        L.append(f"- Raw findings: **{slither_result['total']}** — {slither_result['counts']}")
    else:
        L.append(f"- Not run this cycle: {slither_result.get('reason')}")
    L.append("")
    L.append("## Methodology")
    L.append("1. Real keyless recon: GoPlus token security, DexScreener liquidity, Base RPC "
             "on-chain presence, DeFiLlama hack-technique correlation, public web search for "
             "reputation flags — identical pipeline to every free VAPE investigation.")
    L.append("2. Etherscan V2 contract verification + full verified source (when available).")
    L.append("3. Slither static analysis, real tool output, only if pre-installed this run.")
    L.append("4. A frontier-tier LLM (Gemini 2.5 Pro, Groq as automatic fallback) reads the "
             "actual verified source and reasons per vulnerability class — this is VAPE's "
             "deepest automated pass, still followed by the human-verification list above.")
    L.append("5. White-hat only: read-only analysis, no exploitation attempted.")
    L.append("")
    L.append("*V.A.P.E. — The chain never lies. This is a 24h-SLA premium engagement; "
             "results delivered as soon as generated, well inside that window.*")

    content = "\n".join(L)
    with open(path, "w") as f:
        f.write(content)
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    print(f"[deep_dive_audit] wrote {rel}")

    result = {"address": address, "chain": chain, "symbol": sym, "verdict": verdict,
              "score": score, "report": rel, "provider": provider}

    if callback_url:
        if not _is_safe_callback_url(callback_url):
            print("[deep_dive_audit] callback_url rejected (not a public http/https host) "
                  "— report is still committed, just not POSTed anywhere")
        else:
            try:
                req = urllib.request.Request(
                    callback_url, data=json.dumps(result).encode(),
                    headers={"Content-Type": "application/json", "User-Agent": "VAPE-DeepDive/1.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15):
                    print("[deep_dive_audit] delivered result to callback_url")
            except Exception as e:
                print(f"[deep_dive_audit] callback delivery failed (non-fatal, report is committed either way): {e}")

    return result


def main():
    ap = argparse.ArgumentParser(description="VAPE Deep-Dive Bounty Audit (50 USDC / 24h SLA)")
    ap.add_argument("--address", required=True, help="target contract/token address (0x...)")
    ap.add_argument("--chain", default="8453", help="chain id (default Base 8453)")
    ap.add_argument("--callback-url", default=None, help="optional webhook to POST the result to on completion")
    args = ap.parse_args()

    result = run_audit(args.address, args.chain, args.callback_url)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
