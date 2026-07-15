#!/usr/bin/env python3
"""
VAPE Community Intel Broadcast — real-data sections + a Grok 4.1 Fast
analyst briefing.

intel/broadcasts/ went dormant on 2026-07-01: nothing in this repo's CI ever
generated these files — every historical broadcast came from an external
process outside this codebase. Same "declared but never wired" gap as the
Tavily/Firecrawl/BrightData research router before it got wired into
agents/investigate.py and agents/run.py.

Every numeric section is built entirely from data VAPE's own pipeline
already fetches — agents/data_fetchers.build_market_context() (TVL, fees,
hacks, Fear&Greed, global market, Virtuals, movers, anomaly flags) plus the
investigation ledger (agents/investigate.py). On top of that, one bounded
web search plus a frontier-tier (Grok 4.1 Fast first, see
agents/intel_common.py::grok_analysis()) narrative section synthesizes what
this cycle's data + research actually implies — the numbers stay
deterministic, only the "Analyst Briefing" section is model-generated, and
it's explicitly barred from inventing facts beyond what it was given.

Output: intel/broadcasts/broadcast-<UTC-YYYY-MM-DD-HH>.md — same naming
convention the old broadcasts used, so agents/build_intel_index.py's
scan_broadcasts() picks it up with zero changes.

CLI:
  python -m agents.broadcast [--window-hours 6]
"""
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.report_format import letterhead_md

BROADCAST_DIR = os.path.join(ROOT, "intel", "broadcasts")

try:
    from agents.data_fetchers import build_market_context
    from agents import investigate as inv
except Exception:
    from data_fetchers import build_market_context
    import investigate as inv

try:
    from skillforge.memory.retriever import append_to_memory
except Exception:
    append_to_memory = None

from agents import intel_common as ic


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _usd(n):
    try:
        n = float(n)
    except Exception:
        return "—"
    if abs(n) >= 1e12:
        return f"${n/1e12:.2f}T"
    if abs(n) >= 1e9:
        return f"${n/1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"${n/1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"${n/1e3:.0f}K"
    return f"${n:.0f}"


def _pct(n, digits=1):
    try:
        return f"{float(n):+.{digits}f}%"
    except Exception:
        return "—"


def _recent_ledger_activity(window_hours):
    """Ledger entries last_investigated within the window, newest first."""
    ledger = inv._load_ledger()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=window_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent = [e for e in ledger.values() if e.get("last_investigated", "") >= cutoff]
    recent.sort(key=lambda e: e.get("last_investigated", ""), reverse=True)
    return recent, ledger


def _verdict_counts(ledger):
    counts = {"PROCEED": 0, "CAUTION": 0, "REJECT": 0}
    for e in ledger.values():
        v = e.get("last_verdict")
        if v in counts:
            counts[v] += 1
    return counts


def build_broadcast(window_hours=6):
    ctx = build_market_context()
    recent, ledger = _recent_ledger_activity(window_hours)
    counts = _verdict_counts(ledger)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
    L = []
    L.extend(letterhead_md("VAPE Community Intelligence Broadcast"))
    L.append(f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC  ")
    L.append(f"**Broadcast #:** {stamp}")
    L.append("")
    L.append("---")
    L.append("")

    # ── Overview (feeds build_intel_index.py's _summary() extraction) ──────
    flags = ctx.get("anomaly_flags") or []
    clean = flags == ["none detected by rule-based pass"]
    L.append("## Overview")
    if clean and not recent:
        L.append(f"Quiet cycle: no rule-based anomalies flagged across Base/DeFi/macro this "
                  f"window, and no new VAPE investigations completed in the last {window_hours}h. "
                  f"Base TVL {_usd((ctx.get('base_tvl') or {}).get('tvl_usd'))}, "
                  f"{counts['PROCEED']+counts['CAUTION']+counts['REJECT']} targets on VAPE's "
                  f"permanent record ({counts['REJECT']} REJECT / {counts['CAUTION']} CAUTION / "
                  f"{counts['PROCEED']} PROCEED).")
    else:
        bits = []
        if recent:
            bits.append(f"{len(recent)} new VAPE investigation(s) in the last {window_hours}h")
        if not clean:
            bits.append(f"{len(flags)} rule-based anomaly flag(s) this cycle")
        L.append(f"{' and '.join(bits)}. Base TVL {_usd((ctx.get('base_tvl') or {}).get('tvl_usd'))}, "
                  f"{counts['PROCEED']+counts['CAUTION']+counts['REJECT']} targets on VAPE's permanent "
                  f"record ({counts['REJECT']} REJECT / {counts['CAUTION']} CAUTION / {counts['PROCEED']} PROCEED).")
    L.append("")

    # ── Anomaly flags (rule-based, real) ────────────────────────────────────
    L.append("## Anomaly Flags")
    if clean:
        L.append("None this cycle — clean sweep across TVL, gas, exploit feed, and macro sentiment checks.")
    else:
        for f in flags:
            L.append(f"- {f}")
    L.append("")

    # ── VAPE Casework (real ledger activity) ────────────────────────────────
    L.append("## VAPE Casework")
    if recent:
        for e in recent[:8]:
            L.append(f"- **{e.get('symbol', '?')}** (`{e.get('address', '?')[:10]}…`) — "
                      f"{e.get('last_verdict')} {e.get('last_score')}/100")
    else:
        L.append(f"No new investigations completed in the last {window_hours}h — see the "
                  "[fail](../investigations/fail-list.md) / [caution](../investigations/caution-list.md) / "
                  "[pass](../investigations/pass-list.md) lists for the full permanent record.")
    L.append("")

    # ── Security Pulse (real DeFiLlama hack feed) ───────────────────────────
    L.append("## Security Pulse")
    hacks = (ctx.get("security_hacks") or {}).get("incidents") or []
    if hacks:
        for h in hacks[:5]:
            L.append(f"- **{h.get('date')}** {h.get('name')} — ${h.get('amount_usd_m')}M on "
                      f"{', '.join(h.get('chains') or [])} ({h.get('technique') or 'technique unknown'})")
    else:
        L.append("No incidents in DeFiLlama's feed this cycle.")
    L.append("")

    # ── Market Pulse (real Fear&Greed + global market) ──────────────────────
    fng = ctx.get("fear_greed") or {}
    glob_m = ctx.get("global_market") or {}
    prices = ctx.get("prices") or {}
    L.append("## Market Pulse")
    if fng.get("value") is not None:
        L.append(f"- Fear & Greed: **{fng.get('value')}** ({fng.get('classification')}), "
                  f"prev {fng.get('prev_value')} ({fng.get('prev_classification')})")
    if glob_m.get("total_mcap_usd") is not None:
        L.append(f"- Total crypto mcap: {_usd(glob_m.get('total_mcap_usd'))} "
                  f"({_pct(glob_m.get('mcap_change_24h_pct'))} 24h) · "
                  f"BTC dom {glob_m.get('btc_dominance_pct')}% · ETH dom {glob_m.get('eth_dominance_pct')}%")
    if isinstance(prices, dict) and prices.get("ethereum"):
        eth_p = (prices.get("ethereum") or {}).get("usd")
        btc_p = (prices.get("bitcoin") or {}).get("usd")
        L.append(f"- ETH ${eth_p} · BTC ${btc_p}")
    L.append("")

    # ── Base & Virtuals Update (real TVL/fees/gas + VIRTUAL) ────────────────
    tvl = ctx.get("base_tvl") or {}
    fees = ctx.get("base_fees") or {}
    activity = ctx.get("chain_activity") or {}
    virtuals = ctx.get("virtuals") or {}
    L.append("## Base & Virtuals Update")
    L.append(f"- Base TVL: {_usd(tvl.get('tvl_usd'))} ({_pct(tvl.get('tvl_24h_change_pct'))} 24h)")
    top_protocols = tvl.get("top_protocols") or []
    if top_protocols:
        top3 = ", ".join(f"{p.get('name')} ({_usd(p.get('tvl_usd'))})" for p in top_protocols[:3])
        L.append(f"- Top protocols: {top3}")
    if activity.get("gas_price_gwei") is not None:
        L.append(f"- Gas: {activity.get('gas_price_gwei')} gwei")
    if fees.get("total_fees_24h_usd") is not None:
        L.append(f"- Base 24h fees: {_usd(fees.get('total_fees_24h_usd'))} ({_pct(fees.get('change_24h_pct'))})")
    if virtuals.get("virtual_price_usd") is not None:
        L.append(f"- VIRTUAL: ${virtuals.get('virtual_price_usd')} "
                  f"({_pct(virtuals.get('virtual_change_24h_pct'))} 24h)")
    L.append("")

    # ── Analyst Briefing (Grok 4.1 Fast, frontier tier) ─────────────────────
    # Everything above is deterministic, real-data markdown — this is the one
    # section where VAPE's frontier LLM gets real room to connect the dots
    # across this cycle's data rather than just restating it. One bounded web
    # search gives it outside context the internal fetchers can't see (this
    # broadcast previously did zero web research at all).
    search = ic.web_search_snippets("Base blockchain AI agent ecosystem news this week", max_results=6)
    search_lines = "\n".join(f"- {r['title']}: {r['snippet']}" for r in search.get("results", [])) or "none available"
    grounding = (
        f"Recent VAPE casework (last {window_hours}h): {len(recent)} investigation(s). "
        f"Ledger totals: {counts['REJECT']} REJECT / {counts['CAUTION']} CAUTION / {counts['PROCEED']} PROCEED.\n"
        f"Rule-based anomaly flags this cycle: {flags if not clean else 'none'}\n"
        f"Recent DeFiLlama hack feed: {[(h.get('date'), h.get('name'), h.get('amount_usd_m')) for h in hacks[:5]] or 'none'}\n"
        f"Fear & Greed: {fng.get('value')} ({fng.get('classification')}), prev {fng.get('prev_value')}\n"
        f"Global crypto mcap: {_usd(glob_m.get('total_mcap_usd'))} ({_pct(glob_m.get('mcap_change_24h_pct'))} 24h)\n"
        f"Base TVL: {_usd(tvl.get('tvl_usd'))} ({_pct(tvl.get('tvl_24h_change_pct'))} 24h), "
        f"top protocols: {[(p.get('name'), _usd(p.get('tvl_usd'))) for p in top_protocols[:3]]}\n"
        f"Base gas: {activity.get('gas_price_gwei')} gwei, 24h fees {_usd(fees.get('total_fees_24h_usd'))}\n"
        f"VIRTUAL: {virtuals.get('virtual_price_usd')} ({_pct(virtuals.get('virtual_change_24h_pct'))} 24h)\n\n"
        f"Web research this cycle ({search.get('provider') or 'unavailable'}):\n{search_lines}"
    )
    briefing = ic.grok_analysis(
        "on-chain intelligence analyst",
        grounding,
        instructions=(
            "Write the 'Analyst Briefing' section of a community intelligence broadcast. "
            "Synthesize what this cycle's real data + web research actually implies for Base, "
            "Virtuals/AI-agent activity, and VAPE's own casework — don't just restate the numbers "
            "above, interpret them. If nothing notable stands out, say that plainly rather than "
            "manufacturing a narrative."
        ),
    )
    L.append("## Analyst Briefing")
    L.append("")
    L.append(briefing)
    L.append("")

    L.append("---")
    L.append("")
    L.append("*V.A.P.E. — Virtual Ape Private Eye — @based_vape*  ")
    L.append("*Real data only — every figure above traces to a live, keyless API call made at "
              "generation time. The Analyst Briefing section is Grok 4.1 Fast's synthesis of that "
              "data plus this cycle's web research, clearly separated from the deterministic figures.*")

    return "\n".join(L) + "\n", stamp


def main():
    ap = argparse.ArgumentParser(description="VAPE Community Intel Broadcast")
    ap.add_argument("--window-hours", type=int, default=6,
                     help="lookback window for 'recent' casework/cadence framing (default 6)")
    args = ap.parse_args()

    os.makedirs(BROADCAST_DIR, exist_ok=True)
    content, stamp = build_broadcast(args.window_hours)
    path = os.path.join(BROADCAST_DIR, f"broadcast-{stamp}.md")
    with open(path, "w") as f:
        f.write(content)
    print(f"[broadcast] wrote {path}")

    if append_to_memory:
        try:
            append_to_memory(
                category="finding",
                title=f"Community broadcast {stamp}",
                content=content[:1500],
                source="agents/broadcast.py",
                tags=["broadcast", "community-intel"],
                confidence=0.7,
                metadata={"path": os.path.relpath(path, ROOT)},
            )
        except Exception as e:
            print(f"[broadcast] memory log failed (non-fatal): {e}")


if __name__ == "__main__":
    main()
