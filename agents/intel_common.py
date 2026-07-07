"""
Shared helpers for VAPE's scheduled intel sweeps (security/base/sentiment/
virtuals/macro/mainnet-patch-check/bug-bounty-intel — see intel/reports/ for
the historical convention this revives; those used to run as ad hoc Claude
Code sessions, not committed code, which is exactly why they all silently
stopped one day with no trace in git history).

Every sweep here follows the same shape, mirroring scout.py's own design
rule ("rule-based first, LLM only when reasoning is required"): pull real
data (agents/data_fetchers.py + skillforge/research.py), compute the
headline verdict/score DETERMINISTICALLY from that real data, then use the
LLM only for narrative synthesis of what the real data means — never let it
invent the number a reader treats as ground truth.
"""
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

REPORTS_DIR = os.path.join(ROOT, "intel", "reports")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_report(prefix, body_md):
    """Writes intel/reports/<prefix>-<YYYY-MM-DD-HH>.md — the exact naming
    convention agents/build_intel_index.py::_date_from_name() already parses,
    so a revived sweep needs zero site-side changes to show up in the intel
    archive and its type-filter buttons. Collision-safe: if this exact hour
    was already used (e.g. a manual re-run), fall back to the -HHMM variant
    already present in the historical files for the same reason.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    path = os.path.join(REPORTS_DIR, f"{prefix}-{now.strftime('%Y-%m-%d-%H')}.md")
    if os.path.exists(path):
        path = os.path.join(REPORTS_DIR, f"{prefix}-{now.strftime('%Y-%m-%d-%H%M')}.md")
    with open(path, "w") as f:
        f.write(body_md)
    return path


def log_sweep_memory(source, verdict, summary, report_path, tags=None, confidence=0.75):
    """Best-effort Memory log — a sweep's report is the real artifact; this
    just makes the verdict queryable/trend-able alongside every other real
    finding VAPE logs. Never blocks report writing on failure."""
    try:
        from skillforge.memory.retriever import append_to_memory
    except Exception:
        return None
    rel = os.path.relpath(report_path, ROOT)
    try:
        return append_to_memory(
            category="finding",
            title=f"{os.path.basename(source)}: {verdict}",
            content=summary,
            source=source,
            tags=(tags or []) + ["intel-sweep"],
            confidence=confidence,
            metadata={"report": rel, "verdict": verdict},
        )
    except Exception as e:
        print(f"[intel_common] could not log memory: {e}")
        return None


def web_search_snippets(query, max_results=5):
    """Normalized web search results across skillforge.research's provider
    union shapes (Tavily/Brave/DDG-keyless) — mirrors the exact normalization
    agents/investigate.py::web_reputation_check already does, so a shared
    helper doesn't have to be re-derived per sweep. Never raises."""
    try:
        from skillforge.research import search as web_search
    except Exception:
        return {"available": False, "provider": None, "results": []}
    try:
        res = web_search(query, max_results=max_results)
    except Exception:
        return {"available": False, "provider": None, "results": []}
    raw = res.get("raw")
    results = []
    if isinstance(raw, dict):
        results = raw.get("results") or raw.get("data") or []
    elif isinstance(raw, list):
        results = raw
    if not isinstance(results, list):
        results = []
    if not results and res.get("results"):
        results = res["results"]
    out = []
    for r in results[:max_results]:
        if not isinstance(r, dict):
            continue
        out.append({
            "title": str(r.get("title") or ""),
            "url": str(r.get("url") or ""),
            "snippet": str(r.get("content") or r.get("snippet") or r.get("description") or "")[:300],
        })
    return {"available": True, "provider": res.get("provider"), "results": out}


VAPE_WALLET = "0xa1420293a7df49bc8380f543a1fe7b8d6f582879"  # real ACP wallet, same constant used in publish_reputation.py/x402_directory_register.py


def get_vape_eth_balance():
    """Real, live ETH balance for VAPE's own ACP wallet via Base RPC —
    keyless. Returns None on any RPC failure rather than a fabricated 0."""
    try:
        from agents.data_fetchers import _post_rpc
    except Exception:
        return None
    r = _post_rpc("eth_getBalance", [VAPE_WALLET, "latest"])
    try:
        return int(r["result"], 16) / 1e18
    except Exception:
        return None


def fmt_usd(value):
    """Safe '$1,234' formatting (whole dollars — for mcap/TVL/volume-scale
    figures) that never crashes on a missing/error value — every real
    fetcher here degrades to None/'error' rather than raising."""
    if isinstance(value, (int, float)):
        return f"${value:,.0f}"
    return "unavailable"


def fmt_price(value):
    """Safe '$0.5707' formatting for sub-$1-scale token prices, where
    fmt_usd's whole-dollar rounding would collapse real precision to $0/$1."""
    if isinstance(value, (int, float)):
        return f"${value:,.4f}" if abs(value) < 1 else f"${value:,.2f}"
    return "unavailable"


def format_search_section(heading, search_result):
    """Renders web_search_snippets()'s output as a markdown section, or a
    one-line honest note when no provider was available — never fabricates
    results to fill the section."""
    if not search_result.get("available"):
        return f"## {heading}\n\n_Web research unavailable this cycle (no search provider reachable)._\n"
    results = search_result.get("results") or []
    if not results:
        return f"## {heading}\n\n_No results returned this cycle._\n"
    lines = [f"## {heading}\n", f"_Source: {search_result.get('provider')}_\n"]
    for r in results:
        lines.append(f"- **[{r['title'] or r['url']}]({r['url']})** — {r['snippet']}")
    return "\n".join(lines) + "\n"
