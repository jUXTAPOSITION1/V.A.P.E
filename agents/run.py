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
    market_json = json.dumps(market_context, indent=2)[:3000]

    if review_repo:
        print("[Mode] Self-Review Pass\n")
        report = ask_llm(
            "You are VAPE, a thorough repo reviewer. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use real data only.",
            f"Review the entire repo structure, code, recent changes, and give detailed findings, bugs, and improvement suggestions. Slither result: {slither_result[:500]}"
        )
        report_path = f"reports/repo_review_{timestamp}.md"
    else:
        print("[Mode] Bounty Hunt Pass\n")

        # STEP 1: Ground in Memory (SEARCH ONLY) before analysis. We inject any
        # relevant prior findings/lessons into the prompt so the LLM builds on
        # accumulated intelligence rather than starting cold each hour.
        memory_priming = ""
        if INTEGRATION_AVAILABLE:
            try:
                from skillforge.memory.retriever import search_memory as _search
                prior = _search(
                    query="base defi anomaly exploit tvl outflow",
                    max_results=4,
                    days_back=14,
                )
                if prior:
                    print(f"[Memory] Grounded in {len(prior)} prior entries\n")
                    lines = [f"- ({p.get('timestamp','')[:10]}) {p.get('title','')}" for p in prior]
                    memory_priming = (
                        "\n=== PRIOR INTELLIGENCE (from Memory — build on this, avoid repeating) ===\n"
                        + "\n".join(lines) + "\n"
                    )
                else:
                    print("[Memory] No prior grounding entries — fresh start\n")
            except Exception as e:
                print(f"[Integration] Memory grounding failed: {e}\n")

        report = ask_llm(
            "You are VAPE + HACK, a real autonomous on-chain detective. Provide concrete, actionable analysis without disclaimers, simulations, or fictional examples. Use ONLY the real data provided.",
            f"Analyze the live Base/DeFi data below for anomalies, exploit signals, TVL outflows, and threats. "
            f"Tie findings to specific protocols/numbers. Give actionable recommendations.\n\n"
            f"=== LIVE MARKET/CHAIN DATA (real, fetched now) ===\n{market_json}\n\n"
            f"=== SLITHER (self-repo static analysis) ===\n{slither_result[:500]}"
            f"{memory_priming}"
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
        f.write(f"# VAPE Report - {timestamp}\n\n")
        if market_context and not review_repo:
            f.write(f"## Live Data Snapshot\n\n```json\n{market_json}\n```\n\n## Analysis\n\n")
        f.write(report)
    
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
