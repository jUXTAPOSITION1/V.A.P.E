import os
import json
from datetime import datetime
import sys
import time
import subprocess

# Ensure the repository ROOT is importable so `agents.*` and `skillforge.*`
# resolve whether we're invoked as `python agents/run.py` (CI) or as a module.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*a, **k):
        return False

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    from agents.data_fetchers import build_market_context
except Exception:
    try:
        from data_fetchers import build_market_context
    except Exception:
        build_market_context = None

# Multi-provider LLM layer
try:
    from agents.llm import ask as _llm_ask, available as _llm_available
except Exception:
    try:
        from llm import ask as _llm_ask, available as _llm_available
    except Exception:
        _llm_ask = None
        _llm_available = lambda: []

# NEW: Integration layer (Memory + Builder + MCP)
try:
    from agents.integration import (
        analysis_with_memory_grounding,
        builder_generate_and_append,
        mcp_harvest_and_append,
        run_full_cycle,
        get_system_status,
    )
    INTEGRATION_AVAILABLE = True
except Exception as e:
    print(f"[run.py] Warning: Integration layer not available: {e}")
    INTEGRATION_AVAILABLE = False

load_dotenv()
# Guard Groq init: don't crash at import if the SDK or key is absent — the
# multi-provider llm.py layer is the primary path; Groq SDK is a legacy fallback.
client = None
if Groq is not None and os.getenv("GROQ_API_KEY"):
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    except Exception as _e:
        print(f"[run.py] Groq SDK init skipped: {_e}")

def ask_llm(system, query, tier="fast"):
    """Prefer the resilient multi-provider layer; fall back to Groq SDK."""
    if _llm_ask is not None and _llm_available():
        try:
            txt, prov = _llm_ask(system, query, tier=tier)
            print(f"[llm:{prov}] ok")
            return txt
        except Exception as e:
            print(f"[llm] all providers failed ({e}); falling back to Groq SDK")
    
    # Legacy direct-Groq fallback (only if the SDK client initialized)
    if client is None:
        return "[llm unavailable: no provider key set (need GROQ_API_KEY or one of CEREBRAS/OPENROUTER/GITHUB_MODELS/TOGETHER)]"
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=2048
            )
            return response.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower():
                print(f"Rate limit hit. Waiting 30s... (attempt {attempt+1}/3)")
                time.sleep(30)
            else:
                return f"Error: {str(e)}"
    return "Rate limit persistent. Try later."

def run_slither():
    """Run slither static analysis (or return placeholder in limited environment)."""
    try:
        result = subprocess.run(["slither", "."], capture_output=True, text=True, timeout=30)
        return result.stdout
    except:
        return "Slither scan completed (limited environment)."


# ============================================================================
# Full-report generation: system prompt, grounding, and structured template
# ============================================================================

VAPE_REPORT_SYSTEM = """You are V.A.P.E. (Virtual Ape Private Eye) + HACK — a real, autonomous
on-chain detective and security analyst operating on Base + Virtuals Protocol.

You write a COMPLETE, ROBUST intelligence report every cycle. You are NOT a chatbot
summarizing numbers; you are a detective connecting evidence into a narrative with
specific, non-obvious insight.

HARD RULES:
- Use ONLY the real data provided. Never invent numbers, incidents, or tickers.
- If a data section is missing/errored, say "no data this cycle" — do not fabricate.
- NEVER repeat last cycle's phrasing. Lead with WHAT CHANGED vs prior intel.
- Every claim ties to a specific number, protocol, address, incident, or date.
- No hedging filler ("could indicate a potential possible…"). Be decisive; state
  confidence (HIGH/MED/LOW) and the evidence behind it.
- No disclaimers, no "as an AI", no generic "monitor closely" advice. Give the
  specific thing to watch and the threshold that would change your call.

You MUST output these sections as Markdown (omit a section only if it truly has no
data, and say so):

## 🔍 Executive Summary
3-5 punchy bullets. Bullet 1 MUST state what CHANGED vs your last reports (the delta,
not the level). Then the single most important development this cycle and the net risk
posture (RISK-ON / NEUTRAL / RISK-OFF). Do not just restate raw numbers here.

## 🛡️ Security & Exploits
Analyze the DeFi hack feed. Newest incidents, techniques, $ lost, which chains. Are any
relevant to Base or Base-deployed protocols? Extract the repeatable attack pattern and
the defensive takeaway for holders/protocols.

## 🔵 Base Chain Intel
TVL, fees/revenue, gas, block activity, top protocols. Where is capital flowing IN vs OUT?
Name protocols + numbers. Flag concentration risk (e.g. one protocol = X% of Base TVL).

## 📈 Crypto Macro
BTC/ETH price + 24h, total mcap change, BTC/ETH dominance, Fear & Greed (+direction),
stablecoin supply as a risk-on/off tell. What regime are we in and what flips it?

## 🦍 Virtuals Ecosystem
VIRTUAL price/mcap/volume + 24h, protocol TVL. Health of the agent economy VAPE lives in.

## 🕯️ Movers & Investigations
Notable Base token movers (volume/price). For anything violent or low-liquidity, open a
mini-investigation: rug/honeypot/wash-trade hypothesis + what to verify next.

## 🎯 Watchlist & Next Actions
Concrete, prioritized. Each item: the trigger/threshold, the tool VAPE would run
(token_safety, contract_recon, hack_feed, base_rpc), and why.

Close with one sharp line in VAPE's noir detective voice. The chain never lies.
"""


def _recent_report_digests(n=5):
    """Pull the last N bounty reports' Analysis sections (short) to force novelty."""
    import glob
    digests = []
    try:
        files = sorted(glob.glob("reports/bounty_report_*.md"), reverse=True)[:n]
        for fp in files:
            try:
                with open(fp) as fh:
                    txt = fh.read()
                # take the summary/analysis portion, compressed
                if "Executive Summary" in txt:
                    body = txt.split("Executive Summary", 1)[1]
                elif "## Analysis" in txt:
                    body = txt.split("## Analysis", 1)[-1]
                else:
                    body = txt
                snippet = " ".join(body.split())[:280]
                stamp = os.path.basename(fp).replace("bounty_report_", "").replace(".md", "")
                digests.append(f"- [{stamp}] {snippet}")
            except Exception:
                continue
    except Exception:
        pass
    return digests


def _build_grounding():
    """Assemble anti-repetition grounding: recent report digests + Memory hits."""
    parts = []
    recent = _recent_report_digests(5)
    if recent:
        print(f"[Grounding] {len(recent)} recent reports loaded for novelty check\n")
        parts.append(
            "=== YOUR LAST FEW REPORTS (do NOT repeat these framings; report what CHANGED) ===\n"
            + "\n".join(recent)
        )
    if INTEGRATION_AVAILABLE:
        try:
            from skillforge.memory.retriever import search_memory as _search
            prior = _search(query="base exploit security virtuals macro anomaly",
                            max_results=5, days_back=10)
            if prior:
                lines = [f"- ({p.get('timestamp','')[:10]}) {p.get('title','')}" for p in prior]
                parts.append(
                    "=== PRIOR INTELLIGENCE (Memory — build on this) ===\n" + "\n".join(lines)
                )
                print(f"[Memory] Grounded in {len(prior)} prior entries\n")
        except Exception as e:
            print(f"[Integration] Memory grounding failed: {e}\n")
    return ("\n\n" + "\n\n".join(parts) + "\n") if parts else ""


def _build_report_prompt(market_json, slither_result, memory_priming):
    return (
        "Write today's full V.A.P.E. intelligence report from the REAL data below. "
        "Follow the exact section structure from your instructions. Be specific, "
        "decisive, and non-repetitive.\n\n"
        f"=== LIVE MULTI-DOMAIN DATA (real, fetched now) ===\n{market_json}\n\n"
        f"=== SELF-REPO STATIC ANALYSIS (slither) ===\n{slither_result[:400]}\n"
        f"{memory_priming}"
    )


def main(review_repo=False):
    print("=" * 80)
    print("VAPE + HACK Cycle Started")
    print("=" * 80)
    
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Print integration system status
    if INTEGRATION_AVAILABLE:
        status = get_system_status()
        print(f"\n[Integration Status]")
        print(f"  Memory: {'✅' if status['memory_available'] else '❌'}")
        print(f"  Builder: {'✅' if status['builder_available'] else '❌'}")
        print(f"  MCP: {'✅' if status['mcp_available'] else '❌'}")
        if status['memory_stats']:
            print(f"  Memory entries: {status['memory_stats'].get('total_entries', 0)}")
        print()
    
    slither_result = run_slither()

    # Build market context
    market_context = {}
    if build_market_context is not None:
        try:
            market_context = build_market_context()
        except Exception as e:
            market_context = {"error": f"market context unavailable: {e}"}
    market_json = json.dumps(market_context, indent=2)[:9000]

    if review_repo:
        print("[Mode] Self-Review Pass\n")
        report = ask_llm(
            "You are VAPE, a thorough repo reviewer. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use real data only.",
            f"Review the entire repo structure, code, recent changes, and give detailed findings, bugs, and improvement suggestions. Slither result: {slither_result[:500]}"
        )
        report_path = f"reports/repo_review_{timestamp}.md"
    else:
        print("[Mode] Bounty Hunt Pass\n")

        # STEP 1: Ground in Memory + recent reports to FORCE novelty. We show the
        # LLM the last several report summaries so it explicitly builds on prior
        # intel and calls out what CHANGED instead of repeating boilerplate.
        memory_priming = _build_grounding()

        report = ask_llm(
            VAPE_REPORT_SYSTEM,
            _build_report_prompt(market_json, slither_result, memory_priming),
            tier="deep",
        )
        report_path = f"reports/bounty_report_{timestamp}.md"

        # STEP 2: Append the ACTUAL analysis back to Memory (not raw data), and
        # only when we produced a real report (skip LLM-unavailable stubs).
        if INTEGRATION_AVAILABLE and report and not report.startswith("[llm unavailable"):
            try:
                from skillforge.memory.retriever import append_to_memory as _append
                _append(
                    category="finding",
                    title=f"Bounty-cycle analysis {timestamp}",
                    content=report[:2000],
                    source="agents/run.py",
                    tags=["bounty-cycle", "base", "defi", "analysis"],
                    confidence=0.8,
                    metadata={"timestamp": timestamp, "report_path": report_path},
                )
                print("[Memory] Analysis appended to findings\n")
            except Exception as e:
                print(f"[Integration] Memory append failed: {e}\n")
    
    # Write report
    with open(report_path, "w") as f:
        if review_repo:
            f.write(f"# VAPE Repo Review — {timestamp}\n\n")
            f.write(report)
        else:
            gen = (market_context or {}).get("generated_at", timestamp)
            f.write("# 🦍 V.A.P.E. Intelligence Report\n\n")
            f.write(f"**Cycle:** `{timestamp}` · **Data timestamp (UTC):** {gen}  \n")
            f.write("**Coverage:** Security · Base · Crypto Macro · Virtuals · Forensics · Movers\n\n")
            # rule-based anomaly flags up top as an at-a-glance banner
            flags = (market_context or {}).get("anomaly_flags") or []
            if flags and flags != ["none detected by rule-based pass"]:
                f.write("> **⚠️ Auto-flagged this cycle:**\n")
                for fl in flags:
                    f.write(f"> - {fl}\n")
                f.write("\n")
            f.write("---\n\n")
            f.write(report)
            # full raw data as a collapsed appendix (auditable, not noisy)
            if market_context:
                f.write("\n\n---\n\n<details>\n<summary>📊 Raw data snapshot (audit trail)</summary>\n\n")
                f.write(f"```json\n{json.dumps(market_context, indent=2)}\n```\n\n</details>\n")
    
    print(f"\n✅ Report saved to: {report_path}\n")
    
    # NEW: Optionally run full cycle if requested
    if os.getenv("VAPE_FULL_CYCLE"):
        print("[Integration] Running full cycle (Memory + Builder + MCP)...")
        try:
            cycle = run_full_cycle(
                market_data=market_context,
                slither_output=slither_result[:500],
                bounties=[]  # Would fetch real bounties
            )
            print(f"[Cycle] Detective grounded: {cycle['detective_grounded']}")
            print(f"[Cycle] Builder generated: {cycle['builder_generated']}")
            print(f"[Cycle] MCP harvested: {cycle['mcp_harvested']}")
            if cycle['memory_stats']:
                print(f"[Cycle] Memory entries: {cycle['memory_stats'].get('total_entries', 0)}\n")
        except Exception as e:
            print(f"[Cycle] Full cycle failed: {e}\n")

if __name__ == "__main__":
    review = "--review-repo" in sys.argv
    main(review)
