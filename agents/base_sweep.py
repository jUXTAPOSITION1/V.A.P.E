"""
VAPE Base Chain Sweep — revives the "VAPE Base Chain Sweep" cron (see
intel/reports/base-*.md); same story as security_sweep.py's docstring:
ran as an ad hoc Claude Code session for 3 weeks, then silently stopped
2026-07-01 with no code left behind.

Real data: agents/data_fetchers.py's already-built, keyless DefiLlama/RPC
fetchers (TVL, top protocols, gas, fees) plus a live ETH balance check on
VAPE's own wallet. BASE HEALTH SCORE is computed deterministically from real
TVL/gas movement, not eyeballed. One bounded web search adds qualitative
ecosystem news (upgrades, launches) the numeric feeds can't see.

Usage: python agents/base_sweep.py
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import (  # noqa: E402
    get_base_tvl_and_protocols, get_chain_activity, get_base_fees,
)
from agents import intel_common as ic  # noqa: E402
from agents import llm  # noqa: E402


def compute_health_score(tvl, activity):
    """0-10, starts at a neutral 5. Real thresholds, reproducible from the
    numbers printed in the report — see intel_common.py's module docstring
    for why this isn't an LLM guess."""
    score = 5.0
    chg = tvl.get("tvl_24h_change_pct")
    if isinstance(chg, (int, float)):
        if chg >= 2:
            score += 2
        elif chg > 0:
            score += 1
        elif chg <= -10:
            score -= 3
        elif chg < 0:
            score -= 1
    gas = activity.get("gas_price_gwei")
    if isinstance(gas, (int, float)):
        if gas < 1:
            score += 1
        elif gas > 5:
            score -= 1
    return max(0, min(10, round(score, 1)))


def run():
    tvl = get_base_tvl_and_protocols(top_n=8)
    activity = get_chain_activity()
    fees = get_base_fees()
    eth_balance = ic.get_vape_eth_balance()

    if tvl.get("error"):
        score = None
    else:
        score = compute_health_score(tvl, activity)

    search = ic.web_search_snippets("Base blockchain Coinbase L2 news update this week", max_results=8)

    protos = tvl.get("top_protocols") or []
    proto_rows = "\n".join(
        f"| {p['name']} | ${p['base_tvl_usd']:,.0f} | {p.get('change_1d', '—')}% | {p.get('category') or '—'} |"
        for p in protos
    ) or "| — | data unavailable this cycle | — | — |"

    system = (
        "You are VAPE, an autonomous on-chain analyst covering the Base L2 ecosystem. "
        "Write using ONLY the real numbers and search results provided — never invent "
        "TVL figures, protocol names, or upgrade dates beyond what's given. If the web "
        "search found nothing new, say so rather than padding with generic L2 commentary. "
        "You have real analytical freedom here — go as deep as the real data supports, "
        "connect protocol-level moves to the broader TVL/gas picture, and bring in your own "
        "general knowledge of the L2/Base landscape to contextualize what the search results "
        "surfaced, clearly marked as background rather than this cycle's own data."
    )
    user = (
        f"BASE HEALTH SCORE (already computed, do not change it): {score if score is not None else 'unavailable'}/10\n"
        f"TVL: {ic.fmt_usd(tvl.get('tvl_usd'))} ({tvl.get('tvl_24h_change_pct')}% 24h, {tvl.get('tvl_7d_change_pct')}% 7d)\n"
        f"Gas: {activity.get('gas_price_gwei', 'unavailable')} gwei, latest block {activity.get('latest_block', 'unavailable')}\n"
        f"24h fees: {fees}\n"
        f"VAPE wallet ETH balance: {eth_balance if eth_balance is not None else 'unavailable'} ETH\n\n"
        f"Top protocols by TVL:\n{proto_rows}\n\n"
        f"Web search on recent Base ecosystem news:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in search.get('results', [])] or 'none available'}\n\n"
        "Write two sections in markdown, each starting with '### ':\n"
        "1. Ecosystem Highlights — what the TVL/gas numbers and search results together say "
        "about Base's current state, at whatever depth they support. Cite specific protocols/news "
        "items from the data above.\n"
        "2. Summary & Watch Items — action items for VAPE, grounded in the real data (as many as "
        "are genuinely warranted, not a fixed count)."
    )
    # ask_vertex_candidate_safe() tries VAPE's own Vertex-tuned model first if
    # VAPE_VERTEX_ACCESS_TOKEN is set this run, falling back to exactly the
    # same frontier tier/order as before otherwise — a run without the token
    # configured behaves identically to before this change.
    narrative, provider = llm.ask_vertex_candidate_safe(system, user, tier="frontier", max_tokens=2200,
                                                       provider_order=llm.FRONTIER_ORDER)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""# Base Blockchain Sweep Report

**Date:** {stamp}
**Chain:** Base (Coinbase Ethereum L2, Chain ID 8453)
**Wallet:** {ic.VAPE_WALLET}

---

## BASE HEALTH SCORE: {score if score is not None else 'N/A'} / 10

Computed deterministically from real TVL 24h change ({tvl.get('tvl_24h_change_pct', '—')}%) and
gas price ({activity.get('gas_price_gwei', '—')} gwei) — see `agents/base_sweep.py::compute_health_score`.

---

## TVL & Chain Activity (real, DefiLlama + Base RPC)

| Metric | Value |
|--------|-------|
| Total TVL | {ic.fmt_usd(tvl.get('tvl_usd'))} |
| 24h Change | {tvl.get('tvl_24h_change_pct', '—')}% |
| 7d Change | {tvl.get('tvl_7d_change_pct', '—')}% |
| Gas Price | {activity.get('gas_price_gwei', '—')} gwei |
| Latest Block | {activity.get('latest_block', '—')} |

### Top Protocols by TVL

| Protocol | Base TVL | 24h Change | Category |
|----------|----------|------------|----------|
{proto_rows}

---

## VAPE Wallet Status

| Field | Value |
|-------|-------|
| Address | {ic.VAPE_WALLET} |
| ETH Balance | {f'{eth_balance:.6f} ETH' if eth_balance is not None else 'unavailable this cycle'} |

---

{narrative}

---

{ic.format_search_section("Web Signals — Base Ecosystem", search)}

---

## Sources
- DefiLlama TVL/protocols API — keyless
- Base RPC (`mainnet.base.org`) — keyless
- Live web search ({search.get('provider') or 'unavailable'})
- LLM synthesis: {provider or 'unavailable this cycle'}

---

*Report generated by `agents/base_sweep.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} after the
original ad hoc sweep silently stopped; see intel/reports/base-2026-07-01-20.md for the last
pre-revival report.*
"""
    path = ic.write_report("base", body)
    summary = f"Base sweep: health {score}/10, TVL {ic.fmt_usd(tvl.get('tvl_usd'))} ({tvl.get('tvl_24h_change_pct', '—')}% 24h)."
    ic.log_sweep_memory("agents/base_sweep.py", str(score), summary, path, tags=["base"])
    print(f"[base_sweep] health={score} — wrote {os.path.relpath(path, ic.ROOT)}")
    return {"score": score, "path": path}


if __name__ == "__main__":
    run()
