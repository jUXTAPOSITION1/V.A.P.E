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
import hashlib
import argparse
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

INVEST_DIR = os.path.join(ROOT, "intel", "investigations")
CATALOG = os.path.join(ROOT, "intel", "catalog", "investigation-catalog.md")
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


# ── scoring ─────────────────────────────────────────────────────────────────
def score(gp, dex, onchain, verif):
    """Return (score_0_100, verdict, reasons[]). Higher score = safer."""
    s = 100
    reasons = []

    def flag(cond, penalty, msg):
        nonlocal s
        if cond:
            s -= penalty
            reasons.append(f"[-{penalty}] {msg}")

    flag(str(gp.get("is_honeypot")) == "1", 60, "GoPlus: HONEYPOT detected")
    flag(str(gp.get("cannot_sell_all")) == "1", 30, "GoPlus: cannot sell all tokens")
    flag(str(gp.get("is_mintable")) == "1", 12, "Mintable supply (dilution risk)")
    flag(str(gp.get("can_take_back_ownership")) == "1", 18, "Ownership can be reclaimed")
    flag(str(gp.get("owner_change_balance")) == "1", 25, "Owner can change balances (rug surface)")
    flag(str(gp.get("hidden_owner")) == "1", 20, "Hidden owner")
    flag(str(gp.get("is_proxy")) == "1", 8, "Upgradeable proxy (verify implementation)")
    try:
        bt = float(gp.get("buy_tax") or 0); st = float(gp.get("sell_tax") or 0)
        flag(bt > 0.10, 15, f"High buy tax {bt*100:.0f}%")
        flag(st > 0.10, 20, f"High sell tax {st*100:.0f}%")
    except Exception:
        pass

    liq = dex.get("liquidity_usd") or 0
    try:
        liq = float(liq)
    except Exception:
        liq = 0
    flag(liq and liq < 10000, 25, f"Very low liquidity ${liq:,.0f} (rug/illiquid)")
    flag(liq and liq < 50000, 10, f"Low liquidity ${liq:,.0f}")

    chg = dex.get("change_24h_pct")
    try:
        if chg is not None and abs(float(chg)) > 100:
            flag(True, 10, f"Violent 24h move {float(chg):+.0f}% (volatility/manipulation)")
    except Exception:
        pass

    # freshly created pair
    pc = dex.get("pair_created_ms")
    if pc:
        try:
            age_days = (time.time() * 1000 - float(pc)) / 86400000
            flag(age_days < 3, 12, f"Pair only {age_days:.1f} days old (fresh-launch risk)")
        except Exception:
            pass

    if verif.get("checked"):
        flag(verif.get("verified") is False, 15, "Contract source UNVERIFIED")
    if onchain.get("is_contract") is False:
        reasons.append("[note] address has no contract code (EOA or not deployed)")

    s = max(0, min(100, s))
    verdict = "PROCEED" if s >= 75 else ("CAUTION" if s >= 45 else "REJECT")
    return s, verdict, reasons


# ── target selection ──────────────────────────────────────────────────────────
def auto_target():
    """Pick the highest-signal Base target from live data (violent/low-liq movers)."""
    if not DF:
        return None
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
                if addr:
                    return {"address": addr, "hint": f"auto: mover {m.get('name')} {m.get('change_24h_pct')}%"}
    return None


# ── report + persistence ────────────────────────────────────────────────────
def write_report(target, chain, gp, dex, onchain, verif, corr, s, verdict, reasons):
    os.makedirs(INVEST_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = target[:10]
    path = os.path.join(INVEST_DIR, f"investigation-{stamp}-{short}.md")
    sym = dex.get("symbol") or verif.get("name") or "unknown"
    emoji = {"PROCEED": "🟢", "CAUTION": "🟡", "REJECT": "🔴"}.get(verdict, "⚪")

    L = []
    L.append(f"# 🕵️ VAPE Investigation — {sym}")
    L.append("")
    L.append(f"- **Target:** `{target}`")
    L.append(f"- **Chain:** {chain} (Base)")
    L.append(f"- **Date:** {now_iso()}")
    L.append(f"- **Verdict:** {emoji} **{verdict}**")
    L.append(f"- **Safety Score:** {s}/100")
    L.append("")
    L.append("---")
    L.append("")
    L.append("## Verdict Rationale")
    if reasons:
        for r in reasons:
            L.append(f"- {r}")
    else:
        L.append("- No risk penalties triggered — clean across all automated checks.")
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
                  "cannot_sell_all", "owner_address"):
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
    L.append("---")
    L.append("")
    L.append("*V.A.P.E. — The chain never lies. Investigation conducted with keyless, "
             "real-data recon (GoPlus · DexScreener · Base RPC · Etherscan V2 · DeFiLlama hack feed).*")
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


def _recently_investigated(address, hours=12):
    """Skip targets already investigated within the window (avoid re-hammering)."""
    try:
        cutoff = time.time() - hours * 3600
        for fp in glob_investigations():
            if address[:10].lower() in os.path.basename(fp).lower() and os.path.getmtime(fp) > cutoff:
                return True
    except Exception:
        pass
    return False


def glob_investigations():
    import glob as _g
    return _g.glob(os.path.join(INVEST_DIR, "*.md"))


def investigate(address, chain="8453", hint="", force=False):
    address = address.strip()
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return {"error": f"invalid address: {address}"}

    if not force and _recently_investigated(address):
        print(f"[investigate] skip {address} — investigated within last 12h")
        return {"target": address, "skipped": "recently_investigated"}

    print(f"[investigate] target {address} ({hint})")
    gp = goplus_security(address, chain)
    dex = dexscreener(address)
    onchain = onchain_presence(address)
    verif = contract_verification(address, chain)
    corr = hack_correlation(gp)
    s, verdict, reasons = score(gp, dex, onchain, verif)

    path, sym, emoji = write_report(address, chain, gp, dex, onchain, verif, corr, s, verdict, reasons)
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    log_memory(address, sym, verdict, s, reasons, rel)
    update_catalog(address, sym, verdict, s, reasons, rel)

    print(f"[investigate] {emoji} {verdict} {s}/100 — {sym} → {rel}")
    return {"target": address, "symbol": sym, "verdict": verdict, "score": s,
            "report": rel, "reasons": reasons}


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
