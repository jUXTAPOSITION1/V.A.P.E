"""
VAPE Base Chain Sweep — revives the "VAPE Base Chain Sweep" cron (see
intel/reports/base-*.md); same story as security_sweep.py's docstring:
ran as an ad hoc Claude Code session for 3 weeks, then silently stopped
2026-07-01 with no code left behind.

Real data: agents/data_fetchers.py's already-built, keyless DefiLlama/RPC
fetchers (TVL, top protocols, DEX volume, fees, gas, hack feed, Fear & Greed)
plus a live ETH balance check on VAPE's own wallet. BASE HEALTH SCORE is
computed deterministically from real TVL/gas movement, not eyeballed.
Several targeted web searches (general news, exploit/incident, this cycle's
real top protocol) add qualitative ecosystem news the numeric feeds can't
see, with a keyless RSS safety net if every search provider comes back
empty. Concentration risk, category breakdown, and 24h movers (already
computed by get_base_tvl_and_protocols but previously dropped) are rendered
in full, along with a rule-based Bounty/Security Surface section and a
light since-last-report comparison against the previous base-*.md.

Usage: python agents/base_sweep.py
"""
import glob
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import (  # noqa: E402
    get_base_tvl_and_protocols, get_chain_activity, get_base_fees,
    get_base_dex_volume, get_hack_feed, get_fear_greed,
)
from agents import intel_common as ic  # noqa: E402
from agents import research_engine  # noqa: E402


def compute_health_score(tvl, activity, protos=None):
    """0-10, starts at a neutral 5. Real thresholds, reproducible from the
    numbers printed in the report — see intel_common.py's module docstring
    for why this isn't an LLM guess. `protos` (optional) is the same
    fees+VAPE-Score-enriched top_protocols list run() builds — if present,
    the average protocol VAPE Score nudges the chain-level score too (small
    weight; skipped entirely when no protocol has a computed score)."""
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
    if protos:
        proto_scores = [p["vape_score"] for p in protos if isinstance(p.get("vape_score"), (int, float))]
        if proto_scores:
            avg = sum(proto_scores) / len(proto_scores)
            if avg >= 70:
                score += 1
            elif avg <= 40:
                score -= 1
    return max(0, min(10, round(score, 1)))


def compute_protocol_score(p):
    """0-100 VAPE Score for a single Base protocol — the same deterministic,
    neutral-start-at-50, skip-if-missing weighting as the site's client-side
    _protocolScore() (docs/assets/app.js), so the number VAPE reasons over
    here in its own report matches what a site visitor sees on the live
    dashboard. Built from TVL health (7d/1d change) + real fee/TVL yield —
    audits are skipped (that field lives on DefiLlama's per-protocol detail
    endpoint, not the /protocols list this data comes from)."""
    score = 50
    c7 = p.get("change_7d")
    if isinstance(c7, (int, float)):
        if c7 >= 10:
            score += 20
        elif c7 > 0:
            score += 10
        elif c7 <= -20:
            score -= 20
        elif c7 < 0:
            score -= 10
    c1 = p.get("change_1d")
    if isinstance(c1, (int, float)):
        if c1 >= 5:
            score += 10
        elif c1 > 0:
            score += 5
        elif c1 <= -10:
            score -= 10
        elif c1 < 0:
            score -= 5
    fees24h, base_tvl = p.get("fees_24h_usd"), p.get("base_tvl_usd")
    if isinstance(fees24h, (int, float)) and fees24h > 0 and isinstance(base_tvl, (int, float)) and base_tvl > 0:
        fee_yield = fees24h / base_tvl
        if fee_yield >= 0.001:
            score += 15
        elif fee_yield >= 0.0002:
            score += 8
        else:
            score += 3
    return max(0, min(100, round(score)))


def _load_previous_base_report():
    """Most recent previous intel/reports/base-*.md (if any), parsed for a
    light since-last-report comparison. Reads the same '| Label | Value |'
    table rows this report itself writes below — never invents a number:
    any field that isn't there or doesn't parse cleanly is left out of the
    comparison rather than guessed at."""
    paths = sorted(glob.glob(os.path.join(ic.REPORTS_DIR, "base-*.md")))
    if not paths:
        return None
    try:
        with open(paths[-1]) as f:
            text = f.read()
    except Exception:
        return None

    def _num(pattern):
        m = re.search(pattern, text)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", "").replace("$", ""))
        except ValueError:
            return None

    date_m = re.search(r"\*\*Date:\*\*\s*(.+)", text)
    return {
        "path": paths[-1],
        "date": date_m.group(1).strip() if date_m else os.path.basename(paths[-1]),
        "health_score": _num(r"## BASE HEALTH SCORE:\s*([\d.]+)\s*/\s*10"),
        "tvl_usd": _num(r"\|\s*Total TVL\s*\|\s*\$([\d,]+)\s*\|"),
        "fees_24h_usd": _num(r"\|\s*Fees 24h\s*\|\s*\$([\d,]+)\s*\|"),
    }


def _since_last_report_lines(prev, score, tvl, fees):
    """Deterministic delta clauses vs the previous report — same
    'compute a real clause per real field, skip it if either side is
    missing' idiom as data_fetchers.py's _market_overview_narrative()."""
    if not prev:
        return []
    lines = []
    if prev.get("health_score") is not None and isinstance(score, (int, float)):
        d = score - prev["health_score"]
        lines.append(f"- **BASE HEALTH SCORE:** {score}/10 ({'+' if d >= 0 else ''}{d:.1f} vs last report)")
    if prev.get("tvl_usd") is not None and isinstance(tvl.get("tvl_usd"), (int, float)):
        d = tvl["tvl_usd"] - prev["tvl_usd"]
        pct = f", {d / prev['tvl_usd'] * 100:+.1f}%" if prev["tvl_usd"] else ""
        lines.append(f"- **Total TVL:** {ic.fmt_usd(tvl['tvl_usd'])} ({'+' if d >= 0 else ''}{ic.fmt_usd(d)}{pct} vs last report)")
    if prev.get("fees_24h_usd") is not None and isinstance(fees.get("total_fees_24h_usd"), (int, float)):
        d = fees["total_fees_24h_usd"] - prev["fees_24h_usd"]
        pct = f", {d / prev['fees_24h_usd'] * 100:+.1f}%" if prev["fees_24h_usd"] else ""
        lines.append(f"- **24h Fees:** {ic.fmt_usd(fees['total_fees_24h_usd'])} ({'+' if d >= 0 else ''}{ic.fmt_usd(d)}{pct} vs last report)")
    return lines


def _bounty_security_surface(protos, hacks):
    """Rule-based flags, not an LLM guess — real thresholds off real fields
    already computed elsewhere in this module/data_fetchers.py: (a) a
    high-TVL protocol actively bleeding TVL, (b) a large protocol with a
    weak VAPE Score, (c) any DeFiLlama-confirmed Base-chain incident."""
    lines = []
    for p in protos:
        share = p.get("share_of_base_pct")
        if not isinstance(share, (int, float)) or share < 5:
            continue
        c1, c7 = p.get("change_1d"), p.get("change_7d")
        if (isinstance(c1, (int, float)) and c1 < 0) or (isinstance(c7, (int, float)) and c7 < 0):
            lines.append(
                f"- **{p['name']}** holds {share}% of Base TVL and is down "
                f"{c1 if c1 is not None else '—'}% (24h) / {c7 if c7 is not None else '—'}% (7d) — "
                f"watch for continued outflows."
            )
        vs = p.get("vape_score")
        if isinstance(vs, (int, float)) and vs < 40:
            lines.append(
                f"- **{p['name']}** ({share}% of Base TVL) carries a VAPE Score of {vs}/100 — "
                f"a large share of chain TVL sitting in a weakly-scored protocol."
            )
    for h in (hacks or {}).get("incidents") or []:
        technique = h.get("technique")
        tech_str = f" via {technique}" if technique else ""
        lines.append(f"- **{h.get('date')} — {h.get('name')}**: ${h.get('amount_usd_m')}M lost{tech_str}.")
    return lines


def run():
    tvl = get_base_tvl_and_protocols(top_n=8)
    activity = get_chain_activity()
    fees = get_base_fees()
    dex_vol = get_base_dex_volume()
    hacks = get_hack_feed(limit=5, chain="Base")
    fng = get_fear_greed()
    eth_balance = ic.get_vape_eth_balance()
    prev_report = _load_previous_base_report()

    protos = tvl.get("top_protocols") or []
    # fees and tvl are two separate DefiLlama calls that were previously
    # never merged — fees_by_name joins them by protocol name (both come
    # from the same DefiLlama Base universe) so each protocol row carries
    # its own real fees_24h + a computed VAPE Score, not just raw TVL.
    fees_by_name = {f["name"]: f.get("fees_24h_usd") for f in (fees.get("top_fee_protocols") or []) if f.get("name")}
    for p in protos:
        p["fees_24h_usd"] = fees_by_name.get(p["name"])
        p["vape_score"] = compute_protocol_score(p)

    if tvl.get("error"):
        score = None
    else:
        score = compute_health_score(tvl, activity, protos)

    # Several targeted queries instead of one generic one: general ecosystem
    # news, exploit/incident-specific, and (real, this-cycle) top-protocol-
    # specific — never a hardcoded protocol name, since which protocol is
    # actually #1 by TVL changes over time.
    queries = [
        "Base blockchain Coinbase L2 upgrade OR mainnet news this week",
        "Base Layer 2 exploit OR hack OR security incident",
    ]
    if protos and protos[0].get("name"):
        queries.append(f"{protos[0]['name']} Base protocol news update")

    seen_urls, combined_results, providers_used, any_available = set(), [], [], False
    for q in queries:
        res = ic.web_search_snippets(q, max_results=5)
        any_available = any_available or bool(res.get("available"))
        if res.get("provider") and res["provider"] not in providers_used:
            providers_used.append(res["provider"])
        for r in res.get("results", []):
            if r.get("url") and r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                combined_results.append(r)
    search = {"available": any_available, "provider": ", ".join(providers_used) or None,
              "results": combined_results[:12]}

    # Keyless safety net: if every search provider came back empty (no key
    # configured, quota exhausted, or the keyless DDG/SearXNG fallback is
    # unreachable from this host), fall back to real crypto-outlet RSS
    # feeds already wired for the news pipeline, filtered to items that
    # actually mention Base — still real, sourced headlines, never invented.
    if not combined_results:
        try:
            from agents.news_common import native_rss_feed, NATIVE_RSS_FEEDS
            rss_items = []
            for feed_url, source_name, _topic in NATIVE_RSS_FEEDS[:3]:
                rss_items.extend(native_rss_feed(feed_url, source_name, "Base", max_results=10))
            base_items = [it for it in rss_items if "base" in (it["title"] + " " + it["snippet"]).lower()][:5]
            if base_items:
                search = {
                    "available": True,
                    "provider": "keyless RSS safety net (CoinDesk/Cointelegraph/Decrypt)",
                    "results": [{"title": it["title"], "url": it["url"], "snippet": it["snippet"][:300]}
                                for it in base_items],
                }
        except Exception:
            pass

    proto_rows = "\n".join(
        f"| {p['name']} | ${p['base_tvl_usd']:,.0f} | {p.get('change_1d', '—')}% | {p.get('change_7d', '—')}% | "
        f"{p.get('change_1m', '—')}% | {ic.fmt_usd(p['fees_24h_usd']) if p.get('fees_24h_usd') is not None else '—'} | "
        f"{p.get('vape_score', '—')} | {p.get('category') or '—'} |"
        for p in protos
    ) or "| — | data unavailable this cycle | — | — | — | — | — | — |"

    concentration = tvl.get("concentration_risk") or "unavailable this cycle"
    category_pct = tvl.get("category_breakdown_pct") or {}
    category_rows = "\n".join(f"| {cat} | {pct}% |" for cat, pct in category_pct.items()) or "| — | data unavailable this cycle |"
    gainers = tvl.get("top_gainers_24h") or []
    losers = tvl.get("top_losers_24h") or []
    gainers_rows = "\n".join(f"| {g['name']} | +{g['change_1d']}% |" for g in gainers) or "| — | none this cycle |"
    losers_rows = "\n".join(f"| {lo['name']} | {lo['change_1d']}% |" for lo in losers) or "| — | none this cycle |"

    security_lines = _bounty_security_surface(protos, hacks)
    since_lines = _since_last_report_lines(prev_report, score, tvl, fees)

    grounding = (
        f"BASE HEALTH SCORE (already computed, do not change it): {score if score is not None else 'unavailable'}/10\n"
        f"TVL: {ic.fmt_usd(tvl.get('tvl_usd'))} ({tvl.get('tvl_24h_change_pct')}% 24h, {tvl.get('tvl_7d_change_pct')}% 7d, "
        f"source: {tvl.get('tvl_change_source', 'unavailable')})\n"
        f"DEX volume: {ic.fmt_usd(dex_vol.get('vol_24h_usd'))} 24h, {ic.fmt_usd(dex_vol.get('vol_7d_usd'))} 7d\n"
        f"Fees: {ic.fmt_usd(fees.get('total_fees_24h_usd'))} 24h, {ic.fmt_usd(fees.get('total_fees_7d_usd'))} 7d "
        f"({fees.get('change_24h_pct', '—')}% vs prior day)\n"
        f"Gas: {activity.get('gas_price_gwei', 'unavailable')} gwei, latest block {activity.get('latest_block', 'unavailable')}\n"
        f"Concentration risk: {concentration}\n"
        f"Category breakdown of Base TVL: {category_pct or 'unavailable'}\n"
        f"Top 24h gainers among tracked protocols: {gainers or 'none'}\n"
        f"Top 24h losers among tracked protocols: {losers or 'none'}\n"
        f"Bounty/security flags this cycle: {security_lines or 'none'}\n"
        f"Recent Base-linked DeFiLlama hack-feed incidents: {(hacks or {}).get('incidents') or 'none'}\n"
        f"Crypto Fear & Greed index: {fng if not fng.get('error') else 'unavailable'}\n"
        f"VAPE wallet ETH balance: {eth_balance if eth_balance is not None else 'unavailable'} ETH\n"
        f"Since last report ({prev_report['date'] if prev_report else 'no prior report found'}): {since_lines or 'no comparable prior metrics'}\n\n"
        f"Top protocols (TVL, 24h/7d/30d change, real fees_24h, VAPE Score 0-100):\n{proto_rows}\n\n"
        f"Web search across {len(queries)} targeted queries on recent Base ecosystem news/incidents:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in search.get('results', [])] or 'none available'}"
    )
    synth = research_engine.synthesize(
        {"topic": "Base L2 ecosystem health", "task_type": "market_intel",
         "known_facts": {}, "findings": [], "deep_extracts": [], "raw_user_block": grounding, "log": {}},
        role="autonomous on-chain analyst covering the Base L2 ecosystem",
        extra_instructions=(
            "Never invent TVL figures, protocol names, or upgrade dates beyond what's given. If the "
            "search results don't show anything new, say so rather than padding with generic L2 "
            "commentary. Write two sections in markdown, each starting with '### ':\n"
            "1. Ecosystem Highlights — what the TVL/gas/fees/DEX-volume numbers, concentration risk, "
            "movers, and search results together say about Base's current state, at whatever depth "
            "they support. Cite specific protocols/news items/incidents from the data above.\n"
            "2. Summary & Watch Items — action items for VAPE, grounded in the real data (as many as "
            "are genuinely warranted, not a fixed count). Weigh in on the bounty/security flags and "
            "since-last-report deltas above if they're substantive."
        ),
        trailers=[], max_tokens=2400, temperature=0.5,
    )
    narrative = ic.safe_narrative(synth["narrative"])
    provider = synth["provider"]

    since_section = ""
    if since_lines:
        since_section = (
            f"## Since Last Report ({prev_report['date']})\n\n" + "\n".join(since_lines) + "\n\n---\n\n"
        )

    tvl_note = ""
    if tvl.get("tvl_change_source") == "historical_fallback":
        tvl_note = ("\n_24h/7d TVL % change derived from DefiLlama's historical chain-TVL series "
                    "(the `/v2/chains` change fields were unavailable for Base this cycle)._\n")

    fng_row = ""
    if fng and not fng.get("error"):
        prev_bit = f" (prior: {fng.get('prev_value')} {fng.get('prev_classification')})" if fng.get("prev_value") is not None else ""
        fng_row = f"| Fear & Greed | {fng.get('value')} — {fng.get('classification')}{prev_bit} |\n"

    security_section = (
        "## Bounty / Security Surface\n\n"
        + ("\n".join(security_lines) if security_lines else
           "_No high-TVL negative movers, low-scored large protocols, or Base-linked incidents "
           "flagged this cycle._")
        + "\n\n---\n\n"
    )

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""# Base Blockchain Sweep Report

**Date:** {stamp}
**Chain:** Base (Coinbase Ethereum L2, Chain ID 8453)
**Wallet:** {ic.VAPE_WALLET}

---

{since_section}## BASE HEALTH SCORE: {score if score is not None else 'N/A'} / 10

Computed deterministically from real TVL 24h change ({tvl.get('tvl_24h_change_pct', '—')}%), gas
price ({activity.get('gas_price_gwei', '—')} gwei), and the average VAPE Score across the top
protocols below — see `agents/base_sweep.py::compute_health_score`.

---

## TVL & Chain Activity (real, DefiLlama + Base RPC)

| Metric | Value |
|--------|-------|
| Total TVL | {ic.fmt_usd(tvl.get('tvl_usd'))} |
| 24h Change | {tvl.get('tvl_24h_change_pct', '—')}% |
| 7d Change | {tvl.get('tvl_7d_change_pct', '—')}% |
| DEX Volume 24h | {ic.fmt_usd(dex_vol.get('vol_24h_usd'))} |
| DEX Volume 7d | {ic.fmt_usd(dex_vol.get('vol_7d_usd'))} |
| Fees 24h | {ic.fmt_usd(fees.get('total_fees_24h_usd'))} |
| Fees 7d | {ic.fmt_usd(fees.get('total_fees_7d_usd'))} |
| Gas Price | {activity.get('gas_price_gwei', '—')} gwei |
| Latest Block | {activity.get('latest_block', '—')} |
{fng_row}{tvl_note}
### Top Protocols by TVL

| Protocol | Base TVL | 24h Change | 7d Change | 30d Change | Fees 24h | VAPE Score | Category |
|----------|----------|------------|-----------|------------|----------|------------|----------|
{proto_rows}

---

## Concentration & Composition

**Concentration Risk:** {concentration}

### Category Breakdown (share of Base TVL)

| Category | Share |
|----------|-------|
{category_rows}

### Top Movers (24h, among tracked protocols)

**Gainers**

| Protocol | 24h Change |
|----------|------------|
{gainers_rows}

**Losers**

| Protocol | 24h Change |
|----------|------------|
{losers_rows}

---

{security_section}## VAPE Wallet Status

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
- DefiLlama TVL/protocols/fees/DEX-volume/hacks API — keyless
- Base RPC (`mainnet.base.org`) — keyless
- Alternative.me Fear & Greed index — keyless
- Live web search across {len(queries)} targeted queries ({search.get('provider') or 'unavailable'})
- Narrative synthesis: {'VAPE' if provider else 'unavailable this cycle'}

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
