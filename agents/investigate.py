#!/usr/bin/env python3
"""
VAPE Deep Investigation Engine — autonomous, thorough, real-data-only.

Runs a full detective investigation on a Base target (token/contract) and produces:
  - intel/investigations/investigation-<UTC>-<short>.md   (full report)
  - intel/investigations/investigation-<UTC>-<short>.pdf  (same evidence, letterheaded PDF)
  - a `finding` entry in skillforge/memory/findings.jsonl  (Memory log)
  - a row appended to intel/catalog/investigation-catalog.md (status/verdict)

Pipeline (all keyless where possible, graceful degradation):
  1. Target selection  — explicit addr, or auto-pick from live signals (violent
     movers / low-liquidity pools / top Base protocols not recently investigated).
  2. Recon            — GoPlus token security, DexScreener liquidity/volume,
     Base RPC (code presence/age), contract verification (if ETHERSCAN_API_KEY),
     recent-hack correlation by technique.
  3. Scoring          — weighted risk score -> verdict PROCEED / CAUTION / REJECT.
  4. Persist          — write report, log to Memory, update catalog, dedup-aware.

Zero-LLM: this is deterministic analysis. The narrative report is templated from
the evidence. (The local agent cron can optionally add an LLM narrative layer.)

CLI:
  python agents/investigate.py --address 0x... [--chain 8453]
  python agents/investigate.py --auto            # pick the highest-signal target
"""
import os
import re
import sys
import json
import time
import argparse
import urllib.request
import urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.report_format import letterhead_md, verdict_stamp

INVEST_DIR = os.path.join(ROOT, "intel", "investigations")
CATALOG = os.path.join(ROOT, "intel", "catalog", "investigation-catalog.md")
LEDGER_PATH = os.path.join(INVEST_DIR, "ledger.json")
LIST_PATHS = {
    "REJECT": os.path.join(INVEST_DIR, "fail-list.md"),
    "CAUTION": os.path.join(INVEST_DIR, "caution-list.md"),
    "PROCEED": os.path.join(INVEST_DIR, "pass-list.md"),
}
BASE_RPC = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
UA = {"User-Agent": "VAPE-PrivateEye/1.0"}

try:
    from agents import data_fetchers as DF
except Exception:
    try:
        import data_fetchers as DF
    except Exception:
        DF = None

try:
    from skillforge.memory.retriever import append_to_memory, search_memory
except Exception:
    append_to_memory = None
    search_memory = None


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def _rpc(method, params, timeout=10):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    try:
        req = urllib.request.Request(BASE_RPC, data=payload,
                                     headers={**UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


# ── recon steps ───────────────────────────────────────────────────────────────
def goplus_security(address, chain="8453"):
    d = _get(f"https://api.gopluslabs.io/api/v1/token_security/{chain}"
             f"?contract_addresses={address}")
    try:
        return (d.get("result") or {}).get(address.lower(), {}) or \
               next(iter((d.get("result") or {}).values()), {})
    except Exception:
        return {}


def dexscreener(address):
    d = _get(f"https://api.dexscreener.com/latest/dex/tokens/{address}")
    pairs = d.get("pairs") or [] if isinstance(d, dict) else []
    if not pairs:
        return {}
    p = max(pairs, key=lambda x: (x.get("liquidity") or {}).get("usd", 0) or 0)
    return {
        "symbol": (p.get("baseToken") or {}).get("symbol"),
        "name": (p.get("baseToken") or {}).get("name"),
        "price_usd": p.get("priceUsd"),
        "liquidity_usd": (p.get("liquidity") or {}).get("usd"),
        "vol_24h_usd": (p.get("volume") or {}).get("h24"),
        "change_24h_pct": (p.get("priceChange") or {}).get("h24"),
        "pair_created_ms": p.get("pairCreatedAt"),
        "dex": p.get("dexId"),
    }


def onchain_presence(address):
    code = _rpc("eth_getCode", [address, "latest"])
    c = code.get("result", "0x") if isinstance(code, dict) else "0x"
    return {"is_contract": bool(c and c != "0x"), "code_size_bytes": max(0, (len(c) - 2) // 2)}


def contract_verification(address, chain="8453"):
    # Was its own uncached _get() call to the same Etherscan endpoint
    # data_fetchers.get_contract_source() already hits with a 1h cache —
    # every hourly `--auto` run, every async deep-dive, and every weekly/
    # monthly review-ledger re-check was paying for a duplicate live call.
    # Route through the cached helper instead and remap its field names to
    # this function's existing return shape (checked/name/... — several
    # callers below depend on those exact keys).
    if not DF:
        key = os.getenv("ETHERSCAN_API_KEY")
        if not key:
            return {"checked": False, "note": "no ETHERSCAN_API_KEY"}
        d = _get(f"https://api.etherscan.io/v2/api?chainid={chain}&module=contract"
                 f"&action=getsourcecode&address={address}&apikey={key}")
        try:
            r = (d.get("result") or [{}])[0]
            return {"checked": True, "verified": bool(r.get("SourceCode")),
                    "name": r.get("ContractName") or None,
                    "compiler": r.get("CompilerVersion") or None,
                    "proxy": r.get("Proxy") == "1",
                    "implementation": r.get("Implementation") or None}
        except Exception:
            return {"checked": True, "verified": None}
    r = DF.get_contract_source(address, chainid=chain)
    if not isinstance(r, dict) or r.get("error"):
        return {"checked": False, "note": (r or {}).get("note", "no ETHERSCAN_API_KEY")}
    return {"checked": True, "verified": r.get("verified"),
            "name": r.get("contract_name"),
            "compiler": r.get("compiler"),
            "proxy": r.get("proxy"),
            "implementation": r.get("implementation")}


def hack_correlation(gp):
    """Correlate the target's risk traits against recent real exploit techniques."""
    if not DF:
        return []
    feed = DF.get_hack_feed(limit=25)
    techniques = {}
    for inc in (feed.get("incidents") or []):
        t = (inc.get("technique") or "").lower()
        if t:
            techniques[t] = techniques.get(t, 0) + 1
    hits = []
    # crude trait->technique matches
    if str(gp.get("is_honeypot")) == "1":
        hits.append("Honeypot trait present — matches recurring honeypot/rug incidents.")
    if str(gp.get("can_take_back_ownership")) == "1" or str(gp.get("owner_change_balance")) == "1":
        hits.append("Owner can alter balances/ownership — access-control exploit surface (seen in recent key-compromise hacks).")
    if str(gp.get("is_proxy")) == "1":
        hits.append("Proxy contract — upgradeable logic; verify implementation isn't swappable to malicious code.")
    return hits


# Strong, unambiguous scam-indicator keywords — deliberately narrow. Web
# search results are noisy and this is NOT run through an LLM to judge, so
# only react to language a human wouldn't mistake for anything else. This
# is meant to catch "this got rugged, discussed publicly" (real on-chain
# GoPlus/DexScreener data can't see that), not to score-judge sentiment.
_SCAM_KEYWORDS = ("rug pull", "rugpull", "rugged", "scam", "honeypot", "exit scam", "exploited", "hacked")


def web_reputation_check(symbol, address):
    """Real web search for public reputation signals GoPlus/DexScreener can't
    see — has this project been publicly called out as a rug/scam anywhere
    indexed? Uses skillforge/research.py's provider router (Tavily -> Brave
    -> keyless DDG/SearXNG fallback, quota-capped) — gracefully returns
    empty on any import/network failure, exactly like every other recon
    step here degrades rather than blocking the investigation."""
    try:
        from skillforge.research import search as web_search
    except Exception:
        return {"available": False, "hits": [], "results": []}
    query = f'"{symbol}" {address} rug pull OR scam OR honeypot OR exploit'
    try:
        res = web_search(query, max_results=5)
    except Exception:
        return {"available": False, "hits": [], "results": []}
    raw = res.get("raw")
    results = []
    if isinstance(raw, dict):
        results = raw.get("results") or raw.get("data") or []
    elif isinstance(raw, list):
        results = raw
    if not isinstance(results, list):
        results = []
    if not results and res.get("results"):  # keyless fallback shape
        results = res["results"]

    hits = []
    normalized = []
    for r in results[:5]:
        if not isinstance(r, dict):
            continue
        title = str(r.get("title") or "")
        snippet = str(r.get("content") or r.get("snippet") or r.get("description") or "")
        url = str(r.get("url") or "")
        normalized.append({"title": title, "url": url, "snippet": snippet[:200]})
        blob = f"{title} {snippet}".lower()
        if any(kw in blob for kw in _SCAM_KEYWORDS):
            hits.append(f"Public web result flags this project: \"{title}\" — {url}")
    return {"available": True, "provider": res.get("provider"), "hits": hits, "results": normalized}


# Known permissionless meme-token factory templates on Base — deployed via
# bot/one-click flows with zero team vetting by design (e.g. Clanker, a
# Farcaster-integrated bot: reply to a cast, get an ERC-20). A contract's
# verified NAME matching one of these is a real, deterministic signal, not a
# guess — GoPlus/Etherscan report the deployer's own declared contract name,
# and factory templates all share the same name across every token they spit
# out. This list is deliberately conservative (confirmed patterns only); it
# should grow only as more are confirmed, never padded to look thorough.
MEME_FACTORY_NAME_PATTERNS = ("clanker",)


# ── scoring ─────────────────────────────────────────────────────────────────
def score(gp, dex, onchain, verif, web_rep=None):
    """Return (score_0_100, verdict, reasons[], positive_signals[]).
    Higher score = safer.

    CertiK-style posture: risk is the default state for an anonymous/young
    token, not the exception. The old version started at 100 and only ever
    subtracted for explicit red flags, so a token with NO known red flags but
    also NO known legitimacy — no age, no holders, no audit, deployed via a
    zero-vetting factory template — still scored 90+. That's backwards: the
    ABSENCE of evidence isn't evidence of safety. This version still starts
    at 100 and subtracts for red flags, but also tracks positive_signals
    (real, observed legitimacy evidence) and caps the final score below
    PROCEED tier when too few of those were found, regardless of how clean
    the red-flag checks came back.
    """
    s = 100
    reasons = []
    positive_signals = []

    def flag(cond, penalty, msg):
        nonlocal s
        if cond:
            s -= penalty
            reasons.append(f"[-{penalty}] {msg}")

    def signal(cond, msg):
        if cond:
            positive_signals.append(msg)

    flag(str(gp.get("is_honeypot")) == "1", 60, "GoPlus: HONEYPOT detected")
    flag(str(gp.get("cannot_sell_all")) == "1", 30, "GoPlus: cannot sell all tokens")
    flag(str(gp.get("is_mintable")) == "1", 12, "Mintable supply (dilution risk)")
    flag(str(gp.get("can_take_back_ownership")) == "1", 18, "Ownership can be reclaimed")
    flag(str(gp.get("owner_change_balance")) == "1", 25, "Owner can change balances (rug surface)")
    flag(str(gp.get("hidden_owner")) == "1", 20, "Hidden owner")
    flag(str(gp.get("is_proxy")) == "1", 8, "Upgradeable proxy (verify implementation)")
    flag(str(gp.get("transfer_pausable")) == "1", 15, "Transfers can be paused by owner")
    try:
        bt = float(gp.get("buy_tax") or 0); st = float(gp.get("sell_tax") or 0)
        flag(bt > 0.10, 15, f"High buy tax {bt*100:.0f}%")
        flag(st > 0.10, 20, f"High sell tax {st*100:.0f}%")
    except Exception:
        pass

    # Ownership renouncement — real GoPlus owner_address field, same signal
    # agents/token_scan.py's lighter-weight scan already uses; investigate.py
    # previously never checked this at all despite reporting owner_address
    # in every investigation's raw data section.
    owner = (gp.get("owner_address") or "").lower()
    zero_addr = "0x0000000000000000000000000000000000000000"
    owner_present = bool(owner) and owner != zero_addr
    flag(owner_present, 10, f"Owner not renounced ({gp.get('owner_address')}) — can still act on the contract")
    signal(bool(owner) and not owner_present, "Ownership renounced")

    # Meme-factory template detection — real, deterministic (see
    # MEME_FACTORY_NAME_PATTERNS above), not a heuristic guess.
    cname = (verif.get("name") or "").lower()
    is_factory_template = any(p in cname for p in MEME_FACTORY_NAME_PATTERNS)
    flag(is_factory_template, 20,
         f"Deployed via a permissionless meme-token factory template ({verif.get('name')}) "
         "— no team vetting by design; this pattern strongly correlates with abandoned/rugged tokens")

    # Holder concentration — real GoPlus holder_count. Thin distribution
    # means a handful of wallets can move the price or exit-liquidity anyone
    # who buys in; CertiK-style diligence treats this as a first-class risk
    # factor, not an afterthought.
    holders = None
    try:
        if gp.get("holder_count") not in (None, ""):
            holders = int(gp.get("holder_count"))
    except Exception:
        holders = None
    if holders is not None:
        flag(holders < 50, 20, f"Very few holders ({holders}) — thin, easily manipulated distribution")
        flag(50 <= holders < 200, 8, f"Low holder count ({holders})")
        signal(holders >= 500, f"{holders} holders — reasonably distributed")
    else:
        flag(True, 5, "Holder count unavailable — cannot assess distribution")

    liq = dex.get("liquidity_usd") or 0
    try:
        liq = float(liq)
    except Exception:
        liq = 0
    flag(liq and liq < 10000, 25, f"Very low liquidity ${liq:,.0f} (rug/illiquid)")
    flag(liq and liq < 50000, 10, f"Low liquidity ${liq:,.0f}")
    signal(liq >= 500000, f"Deep liquidity (${liq:,.0f})")

    chg = dex.get("change_24h_pct")
    try:
        if chg is not None and abs(float(chg)) > 100:
            flag(True, 10, f"Violent 24h move {float(chg):+.0f}% (volatility/manipulation)")
    except Exception:
        pass

    # Track record length, tiered — CertiK-style caution: a week-old token
    # has no proven track record. The old single "<3 days" check let
    # anything even slightly older than that pass with zero penalty.
    pc = dex.get("pair_created_ms")
    age_days = None
    if pc:
        try:
            age_days = (time.time() * 1000 - float(pc)) / 86400000
        except Exception:
            age_days = None
    if age_days is not None:
        flag(age_days < 3, 15, f"Pair only {age_days:.1f} days old (extreme fresh-launch risk)")
        flag(3 <= age_days < 14, 10, f"Pair {age_days:.1f} days old — under two weeks, no track record yet")
        flag(14 <= age_days < 30, 5, f"Pair {age_days:.1f} days old — under a month, still unproven")
        signal(age_days >= 90, f"Trading {age_days:.0f}+ days without a known incident in this scan")
    else:
        flag(True, 8, "No pair-creation timestamp available — cannot establish track record length")

    if verif.get("checked"):
        flag(verif.get("verified") is False, 15, "Contract source UNVERIFIED")
        signal(verif.get("verified") is True and not is_factory_template,
               "Custom verified source (not a mass-produced factory template)")
    if onchain.get("is_contract") is False:
        reasons.append("[note] address has no contract code (EOA or not deployed)")

    # Honest absence-of-audit framing: VAPE has no third-party audit-database
    # access, so audit status is always genuinely unknown unless real
    # evidence contradicts that. For an anonymous/young/template-deployed
    # token, treating "unknown" as neutral (as the old scoring silently did)
    # is exactly the gap this rework closes — unknown audit status on an
    # otherwise-unproven project is itself a real, disclosed risk factor.
    unproven = is_factory_template or (age_days is not None and age_days < 30) or (holders is not None and holders < 200)
    flag(unproven, 10, "No known third-party audit or verifiable team identity found — "
                       "treated as unaudited/anonymous by default")

    # Real web search for public reputation signals — GoPlus/DexScreener are
    # on-chain-only and can't see "this got called out as a rug on X/a forum
    # somewhere." See web_reputation_check()'s narrow keyword list (title/
    # snippet must contain unambiguous language like "rug pull"/"scam"/
    # "honeypot") — this is real, disclosed evidence with a source link in
    # the report, not a sentiment guess.
    if web_rep and web_rep.get("hits"):
        flag(True, 25, f"Public web search surfaced {len(web_rep['hits'])} unambiguous "
                        f"scam/rug mention(s) — see Public Web Signals section")

    # Legitimacy cap: don't let a clean red-flag sweep alone buy a PROCEED
    # verdict. Real positive evidence (renounced ownership + deep liquidity +
    # real holder base + real track record + genuinely custom verified code)
    # has to be present — the absence of red flags is not the same thing as
    # the presence of trust.
    cap = None
    if len(positive_signals) == 0:
        cap = 55
    elif len(positive_signals) == 1:
        cap = 70
    if cap is not None and s > cap:
        reasons.append(f"[capped at {cap}] Only {len(positive_signals)} positive legitimacy "
                        f"signal(s) found — score capped even though few explicit red flags triggered")
        s = cap

    s = max(0, min(100, s))
    verdict = "PROCEED" if s >= 80 else ("CAUTION" if s >= 50 else "REJECT")
    return s, verdict, reasons, positive_signals


# ── target selection ──────────────────────────────────────────────────────────
def auto_target():
    """Pick the highest-signal Base target from live data (violent/low-liq movers)
    that VAPE hasn't already reached a real verdict on — skip anything already
    in the ledger so auto mode never wastes a cycle re-discovering a target
    it's just going to turn around and skip anyway."""
    if not DF:
        return None
    ledger = _load_ledger()
    movers = DF.get_base_movers(limit=10)
    cands = movers.get("biggest_movers") or []
    # prefer big movers with a resolvable token; fall back to top volume pools
    for m in cands:
        # movers from GeckoTerminal are pool-named; we need a token address, so we
        # search DexScreener for the symbol to resolve an address.
        name = (m.get("name") or "").split("/")[0].strip()
        if not name:
            continue
        d = _get(f"https://api.dexscreener.com/latest/dex/search?q={urllib.parse.quote(name)}")
        for p in (d.get("pairs") or []) if isinstance(d, dict) else []:
            if str(p.get("chainId", "")).lower() == "base":
                addr = (p.get("baseToken") or {}).get("address")
                if addr and addr.lower() not in ledger:
                    return {"address": addr, "hint": f"auto: mover {m.get('name')} {m.get('change_24h_pct')}%"}
    return None


# ── report + persistence ────────────────────────────────────────────────────
def write_report(target, chain, gp, dex, onchain, verif, corr, s, verdict, reasons, positive_signals, web_rep=None):
    os.makedirs(INVEST_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = target[:10]
    path = os.path.join(INVEST_DIR, f"investigation-{stamp}-{short}.md")
    sym = dex.get("symbol") or verif.get("name") or "unknown"

    L = []
    L.extend(letterhead_md(f"Investigation — {sym}"))
    L.append(verdict_stamp(verdict, s))
    L.append("")
    # Plain-text bullets (not just the badge above) — agents/run.py's
    # _recent_investigations() greps for lines starting with "# " or
    # "- **" to build LLM grounding context, so the verdict has to exist in
    # that form somewhere too, not only as a "![...]" badge image line.
    L.append(f"- **Target:** `{target}`")
    L.append(f"- **Chain:** {chain} (Base)")
    L.append(f"- **Date:** {now_iso()}")
    L.append(f"- **Verdict:** {verdict} ({s}/100)")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Verdict Rationale (risk factors)")
    if reasons:
        for r in reasons:
            L.append(f"- {r}")
    else:
        L.append("- No risk penalties triggered — clean across all automated checks.")
    L.append("")
    L.append("## Positive Signals (real legitimacy evidence found)")
    if positive_signals:
        for p in positive_signals:
            L.append(f"- {p}")
    else:
        L.append("- None found. Absence of red flags is not evidence of safety — a clean sweep "
                  "with zero positive signals still caps the score below PROCEED tier.")
    L.append("")
    L.append("## Market & Liquidity (DexScreener)")
    if dex:
        L.append(f"- Symbol/Name: {dex.get('symbol')} / {dex.get('name')}")
        L.append(f"- Price: ${dex.get('price_usd')}")
        L.append(f"- Liquidity: ${dex.get('liquidity_usd')}")
        L.append(f"- 24h Volume: ${dex.get('vol_24h_usd')}")
        L.append(f"- 24h Change: {dex.get('change_24h_pct')}%")
        L.append(f"- DEX: {dex.get('dex')}")
    else:
        L.append("- No DEX pair data (illiquid / not listed).")
    L.append("")
    L.append("## Token Security (GoPlus)")
    if gp:
        for k in ("is_honeypot", "buy_tax", "sell_tax", "is_mintable", "is_proxy",
                  "can_take_back_ownership", "owner_change_balance", "hidden_owner",
                  "cannot_sell_all", "transfer_pausable", "holder_count", "owner_address"):
            if k in gp:
                L.append(f"- {k}: `{gp.get(k)}`")
    else:
        L.append("- GoPlus returned no security profile for this token.")
    L.append("")
    L.append("## On-chain Presence (Base RPC)")
    L.append(f"- Is contract: {onchain.get('is_contract')}")
    L.append(f"- Code size: {onchain.get('code_size_bytes')} bytes")
    L.append("")
    L.append("## Contract Verification")
    if verif.get("checked"):
        L.append(f"- Verified: {verif.get('verified')}")
        L.append(f"- Name: {verif.get('name')} · Compiler: {verif.get('compiler')}")
        L.append(f"- Proxy: {verif.get('proxy')} · Implementation: {verif.get('implementation')}")
    else:
        L.append(f"- {verif.get('note', 'not checked')}")
    L.append("")
    L.append("## Threat Correlation")
    if corr:
        for c in corr:
            L.append(f"- {c}")
    else:
        L.append("- No correlation to recent exploit techniques.")
    L.append("")
    L.append("## Public Web Signals")
    if web_rep and web_rep.get("available"):
        if web_rep.get("hits"):
            for h in web_rep["hits"]:
                L.append(f"- **Flag:** {h}")
        else:
            L.append("- No unambiguous scam/rug mentions found in the top web search results.")
        if web_rep.get("results"):
            L.append("")
            L.append(f"<details><summary>Raw search results ({web_rep.get('provider', '?')})</summary>\n")
            for r in web_rep["results"]:
                L.append(f"- [{r['title'] or r['url']}]({r['url']}) — {r['snippet']}")
            L.append("\n</details>")
    else:
        L.append("- Web search unavailable this cycle (no research provider configured/reachable).")
    L.append("")
    L.append("---")
    L.append("")
    L.append("*V.A.P.E. — The chain never lies. Investigation conducted with keyless, "
             "real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed) "
             "plus a real web search for public reputation signals.*")
    with open(path, "w") as f:
        f.write("\n".join(L))

    # PDF is a value-add rendering of the same evidence above — never let a
    # PDF-layout failure (e.g. unexpected data shape) break the real report.
    try:
        from agents.report_pdf import build_investigation_pdf
        build_investigation_pdf(
            path[:-3] + ".pdf", target, chain, sym, verdict, s, reasons,
            gp, dex, onchain, verif, corr, now_iso(),
        )
    except Exception as e:
        print(f"[investigate] PDF generation failed (non-fatal): {e}")

    return path, sym, emoji


def log_memory(target, sym, verdict, s, reasons, report_rel):
    if not append_to_memory:
        return
    try:
        append_to_memory(
            category="finding",
            title=f"Investigation: {sym} ({target[:10]}) → {verdict} {s}/100",
            content="; ".join(reasons)[:1800] or "clean across automated checks",
            source="agents/investigate.py",
            tags=["investigation", "base", verdict.lower(), sym.lower()],
            confidence=0.9 if verdict != "CAUTION" else 0.75,
            metadata={"target": target, "score": s, "verdict": verdict, "report": report_rel},
        )
    except Exception as e:
        print(f"[investigate] memory log failed: {e}")


def update_catalog(target, sym, verdict, s, reasons, report_rel):
    if not os.path.exists(CATALOG):
        return
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = reasons[0].split("] ", 1)[-1] if reasons else "clean"
    row = (f"| {date} | auto | {target} ({sym}) | deep_investigation | "
           f"{verdict} ({s}/100) | {key[:80]} | +7d |")
    with open(CATALOG, "a") as f:
        f.write("\n" + row + "\n")


# ── ledger: permanent record of every real verdict, keyed by address ────────
# The single database VAPE checks before ever auto-investigating a target
# again, and the source of truth for the fail/caution/pass lists below.
# Replaces the old _recently_investigated() 12-hour window, which only
# prevented re-hammering a target within half a day — it said nothing about
# a token VAPE had already reached a real verdict on a week ago, which is
# exactly the repeat-investigation loop this was built to stop. Auto mode
# checks this and skips permanently; --address (a human/paying-job-driven
# hire, or a deliberate deep-dive) always passes force=True and can still
# re-investigate on demand — the two documented, legitimate exceptions.
def _load_ledger():
    try:
        with open(LEDGER_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_ledger(ledger):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, indent=2, sort_keys=True)
        f.write("\n")


def ledger_entry(address):
    return _load_ledger().get(address.lower())


def _update_ledger(address, sym, verdict, s, report_rel):
    ledger = _load_ledger()
    key = address.lower()
    entry = ledger.get(key, {"first_investigated": now_iso(), "times_investigated": 0, "history": []})
    entry["address"] = address  # original checksum/case, for display — key stays lowercase for lookup
    entry["symbol"] = sym
    entry["last_investigated"] = now_iso()
    entry["times_investigated"] = entry.get("times_investigated", 0) + 1
    entry["last_verdict"] = verdict
    entry["last_score"] = s
    entry.setdefault("history", []).append({"ts": now_iso(), "verdict": verdict, "score": s, "report": report_rel})
    entry["history"] = entry["history"][-20:]  # cap per-address history, this is a ledger not a full replay log
    ledger[key] = entry
    _save_ledger(ledger)
    return ledger


def regenerate_lists(ledger):
    """Real, regenerated-every-run views VAPE (and anyone else) can read
    without touching the raw ledger: every address currently on record,
    grouped by its LAST real verdict. This is the fail/caution/pass list."""
    by_verdict = {"REJECT": [], "CAUTION": [], "PROCEED": []}
    for addr, entry in ledger.items():
        v = entry.get("last_verdict")
        if v in by_verdict:
            by_verdict[v].append((addr, entry))

    titles = {"REJECT": "Fail List (REJECT)", "CAUTION": "Caution List (CAUTION)", "PROCEED": "Pass List (PROCEED)"}
    for verdict, path in LIST_PATHS.items():
        rows = sorted(by_verdict[verdict], key=lambda kv: kv[1].get("last_investigated", ""), reverse=True)
        lines = [f"# VAPE {titles[verdict]}", "",
                 f"_Regenerated {now_iso()} — {len(rows)} address(es) currently on record with a last verdict of {verdict}._",
                 "", "| Symbol | Address | Score | Times Checked | Last Investigated |",
                 "|--------|---------|-------|----------------|--------------------|"]
        for addr, entry in rows:
            lines.append(f"| {entry.get('symbol', '?')} | `{entry.get('address', addr)}` | {entry.get('last_score')}/100 | "
                          f"{entry.get('times_investigated', 1)} | {entry.get('last_investigated', '?')} |")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")


def investigate(address, chain="8453", hint="", force=False):
    address = address.strip()
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return {"error": f"invalid address: {address}"}

    existing = ledger_entry(address)
    if not force and existing:
        print(f"[investigate] skip {address} — already on record: {existing['last_verdict']} "
              f"{existing['last_score']}/100 on {existing['last_investigated']} "
              f"({existing.get('times_investigated', 1)}x checked). Use --address to force a re-check "
              "(hire / deep-dive exception).")
        return {"target": address, "skipped": "already_investigated",
                "last_verdict": existing["last_verdict"], "last_score": existing["last_score"]}

    print(f"[investigate] target {address} ({hint})")
    gp = goplus_security(address, chain)
    dex = dexscreener(address)
    onchain = onchain_presence(address)
    verif = contract_verification(address, chain)
    corr = hack_correlation(gp)
    prelim_sym = dex.get("symbol") or verif.get("name") or "unknown"
    web_rep = web_reputation_check(prelim_sym, address)
    s, verdict, reasons, positive_signals = score(gp, dex, onchain, verif, web_rep)

    path, sym, emoji = write_report(address, chain, gp, dex, onchain, verif, corr, s, verdict, reasons, positive_signals, web_rep)
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    log_memory(address, sym, verdict, s, reasons, rel)
    update_catalog(address, sym, verdict, s, reasons, rel)
    ledger = _update_ledger(address, sym, verdict, s, rel)
    regenerate_lists(ledger)

    print(f"[investigate] {emoji} {verdict} {s}/100 — {sym} → {rel}")
    return {"target": address, "symbol": sym, "verdict": verdict, "score": s,
            "report": rel, "reasons": reasons, "positive_signals": positive_signals}


def main():
    ap = argparse.ArgumentParser(description="VAPE Deep Investigation Engine")
    ap.add_argument("--address", help="target contract/token address (0x...)")
    ap.add_argument("--chain", default="8453", help="chain id (default Base 8453)")
    ap.add_argument("--auto", action="store_true", help="auto-select highest-signal target")
    args = ap.parse_args()

    target = None
    hint = ""
    if args.address:
        target = args.address
    elif args.auto:
        picked = auto_target()
        if picked:
            target, hint = picked["address"], picked.get("hint", "")
        else:
            print("[investigate] no auto target found this cycle"); return
    else:
        ap.print_help(); return

    result = investigate(target, args.chain, hint, force=bool(args.address))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
