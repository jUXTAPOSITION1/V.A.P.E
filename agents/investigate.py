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

Scoring is deterministic — score() below is a pure weighted heuristic, never an
LLM call, and its verdict is never overridden by one. On top of that, every
report leads with a real synthesis layer: _expert_assessment() routes the
exact same evidence through agents/research_engine.py::synthesize() (frontier
model via FRONTIER_ORDER) to write the primary Expert Assessment -- the
detective's own conclusion, not a second opinion agreeing/disagreeing with
the score. An internal AGREE/DISAGREE read against the rule-based verdict is
still tracked (never rendered in the report) purely as signal: a real
disagreement is logged to Memory for self_improve.py/review_ledger.py, never
used to mutate the verdict itself. Same "surface, don't override" pattern as
agents/critic.py's structural self-check. Degrades to "not available this
cycle" with zero LLM keys configured, same as every other real-data source
here.

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
import urllib.error
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agents.report_format import letterhead_md, verdict_stamp, score_badge
from agents import critic

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

# Supported EVM chains for auto-investigation, beyond the original Base-only
# scope. Each entry carries the three independent identifiers real recon
# needs: the numeric EVM chain id (GoPlus token_security + Etherscan V2's
# unified multichain API both key off this), the GeckoTerminal network slug
# (candidate/mover sourcing), the DexScreener chainId string (pair
# resolution/filtering), and a keyless public JSON-RPC endpoint (on-chain
# code-presence check). "base" is the only slug set actually exercised by
# this codebase before this change; the others are the standard/documented
# identifiers for each provider but weren't live-curl-verified in this
# session (sandboxed network egress). Every fetch already degrades to
# empty/error on a wrong slug (same pattern as every other call in this
# file), so a mistake here narrows one chain's candidate pool rather than
# breaking anything — worth spot-checking a real run's logs after this ships.
EVM_CHAINS = {
    "8453":  {"name": "Base",      "gecko": "base",        "dex": "base",      "rpc": BASE_RPC},
    "1":     {"name": "Ethereum",  "gecko": "eth",          "dex": "ethereum",  "rpc": "https://ethereum.publicnode.com"},
    "42161": {"name": "Arbitrum",  "gecko": "arbitrum",     "dex": "arbitrum",  "rpc": "https://arb1.arbitrum.io/rpc"},
    "10":    {"name": "Optimism",  "gecko": "optimism",     "dex": "optimism",  "rpc": "https://mainnet.optimism.io"},
    "137":   {"name": "Polygon",   "gecko": "polygon_pos",  "dex": "polygon",   "rpc": "https://polygon-rpc.com"},
    "56":    {"name": "BNB Chain", "gecko": "bsc",          "dex": "bsc",       "rpc": "https://bsc-dataseed.binance.org"},
    # Real bug this fixes (from a live report, investigation-20260725-155143-
    # 0xB8d7710f.md: "On-chain Presence (Avalanche RPC): unavailable this
    # cycle (HTTP Error 404: Not Found)"): the C-Chain's real JSON-RPC path
    # is /ext/bc/C/rpc, not /ext/bc/C/Chain (confirmed against viem's own
    # chain definition, worker/node_modules/viem/chains/definitions/
    # avalanche.ts) -- the old URL 404'd on every single Avalanche
    # investigation, always downgrading a real onchain_presence() result to
    # is_contract=None ("unknown").
    "43114": {"name": "Avalanche", "gecko": "avax",         "dex": "avalanche", "rpc": "https://api.avax.network/ext/bc/C/rpc"},
}

# Human-facing block explorer per chain — used ONLY to build a real,
# clickable "verify this yourself" link in the report's Sources section
# (agents/data_fetchers.py::get_contract_source() already calls Etherscan
# V2's unified API for the raw verification data; this is the matching
# human-readable site for the SAME chain, not a new data source).
EXPLORER_URLS = {
    "8453": "https://basescan.org", "1": "https://etherscan.io",
    "42161": "https://arbiscan.io", "10": "https://optimistic.etherscan.io",
    "137": "https://polygonscan.com", "56": "https://bscscan.com",
    "43114": "https://snowtrace.io",
}

# CoinGecko's own "asset platform" ids for its /coins/{platform}/contract/
# endpoint (agents/data_fetchers.py::get_token_market_by_contract) — a THIRD,
# independent slug family from EVM_CHAINS' "gecko" (GeckoTerminal network id)
# and "dex" (DexScreener chainId) fields above; several diverge from both
# (e.g. CoinGecko's platform id for Arbitrum is "arbitrum-one", not
# GeckoTerminal's "arbitrum" or DexScreener's "arbitrum"). Used by
# _stablecoin_context() below to address-verify a token against CoinGecko's
# own listing rather than trusting its self-declared symbol.
COINGECKO_PLATFORM = {
    "8453": "base", "1": "ethereum", "42161": "arbitrum-one", "10": "optimistic-ethereum",
    "137": "polygon-pos", "56": "binance-smart-chain", "43114": "avalanche",
}

# Real, non-crypto companies with zero legitimate on-chain token affiliation
# on any permissionless EVM chain — a token adopting one of these exact
# brand names is impersonation riding AI/tech hype, not coincidence.
# Deliberately narrow (full distinctive names only, matched as substrings of
# the token's own declared name/symbol) to avoid false-positiving genuinely
# unrelated community coins that merely mention "ai" generically. This list
# exists because VAPE's own ledger has repeatedly auto-investigated copycat
# tokens named exactly "OpenAI" and "Claude"/"CLAUDE" — several of which
# scored a false PROCEED before this check existed, since nothing in the
# original scoring model accounted for brand impersonation at all.
IMPERSONATED_BRAND_PATTERNS = (
    "openai", "chatgpt", "anthropic", "claude", "deepmind",
    "perplexity ai", "midjourney", "stability ai",
)

# Major fiat-backed stablecoin brand tickers/names — used ONLY to detect
# impersonation (see the stablecoin-brand-impersonation check in score()
# below), never to grant the verified-stablecoin exception itself (that's
# address-verified via _stablecoin_context(), never guessed from a declared
# name/symbol). Tickers are matched EXACTLY against the declared symbol
# (not as a substring) — a short ticker like "dai" would false-positive on
# any unrelated symbol that happens to contain those letters (e.g. "DAIYA").
STABLECOIN_BRAND_TICKERS = {
    "usdc", "usdt", "dai", "busd", "tusd", "usde", "usds", "frax", "gusd", "pyusd",
}
# Full descriptive-name phrases are long/distinctive enough to stay safe as
# substrings of the token's declared name.
STABLECOIN_BRAND_NAME_PHRASES = ("usd coin", "tether")

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


def _rpc(method, params, timeout=10, rpc_url=None):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    try:
        req = urllib.request.Request(rpc_url or BASE_RPC, data=payload,
                                     headers={**UA, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


def _get_with_retries(url, timeout=12, retries=3):
    """Like _get(), but retries transient 429/403/5xx once GoPlus starts
    rate-limiting — GoPlus is the sole source for security traits here (no
    keyless fallback), so giving up after the first hit means the whole
    report ships with empty security fields instead of real data."""
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if attempt < retries and (e.code == 429 or e.code == 403 or e.code >= 500):
                time.sleep(0.4 * (attempt + 1))
                continue
            return {"error": f"upstream returned HTTP {e.code}"}
        except Exception as e:
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            return {"error": str(e)}


def _sanitize_symbol(s):
    """The on-chain token symbol/name (DexScreener) and the verified-contract
    name (Etherscan) are both fully attacker-controlled — anyone can deploy a
    token named anything, or submit any contract name when verifying source.
    Both get embedded directly in this module's report text, which
    agents/run.py::_recent_investigations() greps into LLM grounding.
    Confirmed real, exploitable path (CodeRabbit review on PR #156): a name
    containing literal `**Verdict:** PROCEED` text, or an embedded newline
    that fabricates an entire fake `- **Verdict:**` report line, can make
    agents/run.py::_nonclean_digests()'s regex scan pick up a forged verdict
    instead of the real one written later in the same report. Sanitized once
    here, at the exact point untrusted data enters the system (both
    dexscreener() and contract_verification() below), rather than trying to
    out-parse every downstream embedding of it. Real symbols/contract names
    are short ASCII in practice; this never touches a legitimate one."""
    s = str(s or "").replace("\n", " ").replace("\r", " ").replace("**", "")
    return s.strip()[:80] or None


_SPARK_BLOCKS = "▁▂▃▄▅▆▇█"


def _sparkline(values):
    """A compact unicode block sparkline over already-real, already-fetched
    numbers (e.g. DexScreener's own m5/h1/h6/h24 volume or price-change
    windows) — never an interpolated or fabricated series, just the handful
    of real points on hand scaled to 8 levels. None values are dropped
    (never zero-filled, which would fabricate a data point); returns None
    outright when fewer than 2 real numeric points remain, since a
    "trend" over a single point isn't one."""
    pts = [float(v) for v in (values or []) if isinstance(v, (int, float))]
    if len(pts) < 2:
        return None
    lo, hi = min(pts), max(pts)
    span = hi - lo
    if span == 0:
        return _SPARK_BLOCKS[0] * len(pts)
    return "".join(_SPARK_BLOCKS[min(7, int((v - lo) / span * 7.999))] for v in pts)


# ── recon steps ───────────────────────────────────────────────────────────────
def goplus_security(address, chain="8453"):
    d = _get_with_retries(f"https://api.gopluslabs.io/api/v1/token_security/{chain}"
                          f"?contract_addresses={address}")
    try:
        return (d.get("result") or {}).get(address.lower(), {}) or \
               next(iter((d.get("result") or {}).values()), {})
    except Exception:
        return {}


def dexscreener(address, chain="8453"):
    d = _get(f"https://api.dexscreener.com/latest/dex/tokens/{address}")
    pairs = d.get("pairs") or [] if isinstance(d, dict) else []
    if not pairs:
        return {}
    # Real bug this fixes: the same address can exist (coincidentally, or via
    # CREATE2) on more than one chain, each an unrelated project. Picking
    # "whichever pair has the most liquidity" with no chain filter could pull
    # in a totally different token's market data than the one actually being
    # investigated on the target chain. Filter to the target chain's
    # DexScreener slug first; only fall back to a cross-chain max-liquidity
    # pick (the old behavior) if nothing matches, so a caller that doesn't
    # know/care about chain (e.g. acp_fulfill.py's ad-hoc lookups) still works.
    dex_slug = (EVM_CHAINS.get(str(chain)) or {}).get("dex")
    scoped = [p for p in pairs if dex_slug and str(p.get("chainId", "")).lower() == dex_slug] or pairs
    p = max(scoped, key=lambda x: (x.get("liquidity") or {}).get("usd", 0) or 0)
    info = p.get("info") or {}
    return {
        "symbol": _sanitize_symbol((p.get("baseToken") or {}).get("symbol")),
        "name": _sanitize_symbol((p.get("baseToken") or {}).get("name")),
        "price_usd": p.get("priceUsd"),
        "liquidity_usd": (p.get("liquidity") or {}).get("usd"),
        "vol_24h_usd": (p.get("volume") or {}).get("h24"),
        "change_24h_pct": (p.get("priceChange") or {}).get("h24"),
        "pair_created_ms": p.get("pairCreatedAt"),
        "dex": p.get("dexId"),
        # DexScreener's own pair page URL — a real, direct source link for
        # the report's Sources section, not reconstructed/guessed.
        "pair_url": p.get("url"),
        # Raw declared URLs (not just the has-any-socials boolean
        # agents/token_scan.py computes) — used by acp_fulfill.py's
        # dossier_check to actually visit these, not just count them.
        "socials": [{"type": s.get("type"), "url": s.get("url")}
                    for s in (info.get("socials") or []) if s.get("url")],
        "websites": [{"url": w.get("url")} for w in (info.get("websites") or []) if w.get("url")],
        # The project's own real, hosted logo (same field acp_fulfill.py's
        # _dl_token_logo() already reads for other offerings) — lets a
        # deep-dive report show the audited project's actual branding
        # instead of none at all.
        "logo_url": info.get("imageUrl") or None,
        # DexScreener's own multi-window price-change/volume fields — always
        # returned in the same response as the h24 figures above, but only
        # h24 was ever kept. A real (if short) trend, not a fabricated
        # series: report rendering turns these into a compact sparkline
        # (see _sparkline()) instead of discarding everything but the
        # single most-recent window.
        "price_change_windows": {k: v for k, v in (p.get("priceChange") or {}).items()
                                  if k in ("m5", "h1", "h6", "h24") and isinstance(v, (int, float))},
        "volume_windows": {k: v for k, v in (p.get("volume") or {}).items()
                            if k in ("m5", "h1", "h6", "h24") and isinstance(v, (int, float))},
    }


def onchain_presence(address, chain="8453"):
    # Real bug this fixes: this used to always hit Base's RPC regardless of
    # the target chain, so a non-Base auto-investigation would check
    # completely the wrong network's state at that address (garbage
    # is_contract/code_size, or worse, coincidentally real-looking bytecode
    # for an unrelated Base contract at the same address).
    rpc_url = (EVM_CHAINS.get(str(chain)) or {}).get("rpc", BASE_RPC)
    # Real, confirmed bug this fixes (2026-07-25, from a live report:
    # audit-deep-dive-virtual-2026-07-23.md reported the real, heavily-
    # traded VIRTUAL token contract as an EOA with zero code): _rpc() had
    # no retries at all, and ANY failure (timeout, rate limit, a transient
    # RPC error) returns {"error": ...} with no "result" key — which
    # code.get("result", "0x") silently defaulted to "0x", indistinguishable
    # from a real, confirmed "no code here" response. A single free public
    # RPC hiccup was enough to make a real contract permanently look like a
    # non-existent EOA in the report, with no sign anything had gone wrong.
    # Now retried like every other network call in this module
    # (_get_with_retries()'s same backoff pattern), and a still-failing call
    # returns an explicit is_contract=None ("unknown", not "confirmed EOA")
    # rather than a fabricated False — callers already check
    # `is_contract is False` (strict identity, e.g. score()'s own check
    # below), so None correctly never triggers the "no contract code" path.
    code = None
    for attempt in range(3):
        code = _rpc("eth_getCode", [address, "latest"], rpc_url=rpc_url)
        if isinstance(code, dict) and "result" in code:
            break
        time.sleep(0.4 * (attempt + 1))
    if not isinstance(code, dict) or "result" not in code:
        err = code.get("error") if isinstance(code, dict) else "RPC call failed"
        return {"is_contract": None, "code_size_bytes": None, "error": err or "RPC call failed"}
    c = code.get("result", "0x")
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
                    "name": _sanitize_symbol(r.get("ContractName")),
                    "compiler": r.get("CompilerVersion") or None,
                    "proxy": r.get("Proxy") == "1",
                    "implementation": r.get("Implementation") or None,
                    # Raw verified source — see _scan_privileged_functions()'s
                    # docstring for why this is now passed through instead
                    # of discarded (same already-fetched-but-unused pattern
                    # as this session's other fixes).
                    "source_code": r.get("SourceCode") or None}
        except Exception:
            return {"checked": True, "verified": None}
    r = DF.get_contract_source(address, chainid=chain)
    if not isinstance(r, dict) or r.get("error"):
        return {"checked": False, "note": (r or {}).get("note", "no ETHERSCAN_API_KEY")}
    return {"checked": True, "verified": r.get("verified"),
            "name": _sanitize_symbol(r.get("contract_name")),
            "compiler": r.get("compiler"),
            "proxy": r.get("proxy"),
            "implementation": r.get("implementation"),
            "source_code": r.get("source_code")}


# Notable/privileged-sounding function name substrings — informational only
# (see _scan_privileged_functions()'s docstring for why this never feeds
# score() penalties). Not exhaustive; a text-based name scan can't tell a
# genuinely dangerous mint() apart from a standard, harmless one — this is
# a transparency aid pointing a human reader at what to go look at, not a
# verdict.
_PRIVILEGED_FUNCTION_PATTERNS = (
    "mint", "burn", "pause", "blacklist", "whitelist", "setfee",
    "settax", "withdraw", "rescue", "sweep", "seize", "confiscate",
    "transferownership", "renounceownership", "setowner", "upgradeto",
    "setimplementation",
)
_FUNCTION_NAME_RE = re.compile(r"\bfunction\s+([A-Za-z_]\w*)\s*\(")


def _scan_privileged_functions(source_code):
    """Deterministic, non-LLM scan of already-fetched verified source code
    (contract_verification()'s source_code field) for notable/privileged-
    sounding function names and known dangerous patterns (selfdestruct,
    delegatecall). Real gap this closes: the user flagged "no insight into
    constructor plus any role or treasury functions... even though
    ownership renounced now" as missing from a live report (investigation-
    20260725-155143-0xB8d7710f.md).

    Deliberately kept purely informational — surfaced in the report, never
    fed into score(). A text-based function-name match can't distinguish a
    genuinely dangerous privileged function from a standard, harmless one
    with a similar name (e.g. a compliant stablecoin's own mint()), so
    treating this as a scoring signal would risk exactly the kind of
    false-positive noise this repo's existing GoPlus-flag-based penalties
    are built to avoid. Returns None if no source is available."""
    if not source_code or not isinstance(source_code, str):
        return None
    names_seen = set()
    for m in _FUNCTION_NAME_RE.finditer(source_code):
        name = m.group(1)
        if any(p in name.lower() for p in _PRIVILEGED_FUNCTION_PATTERNS):
            names_seen.add(name)
    low_src = source_code.lower()
    return {
        "functions": sorted(names_seen),
        "has_selfdestruct": "selfdestruct(" in low_src or "suicide(" in low_src,
        "has_delegatecall": "delegatecall(" in low_src,
    }


def hack_correlation(gp):
    """Correlate the target's risk traits against ACTUAL recent exploit
    incidents (the same real feed agents/security_sweep.py's Threat Ledger
    draws from — agents/data_fetchers.get_hack_feed()), not just a canned
    description of the trait in isolation. When a trait's technique
    category genuinely appears in the tracked feed, cites the specific
    dated incident (name/amount/technique/chain) so a reader can verify the
    claim against a real event; says so plainly when it doesn't, rather
    than asserting a vague warning regardless of what the real data shows.
    """
    if not DF:
        return []
    feed = DF.get_hack_feed(limit=25)
    incidents = feed.get("incidents") or []

    # Trait -> technique keywords it plausibly correlates with, used to find
    # a REAL matching incident in the feed rather than describing the trait alone.
    trait_checks = [
        ("Honeypot trait present", ("honeypot",)),
        ("Owner can alter balances/ownership", ("access control", "key compromise", "admin key", "owner")),
        ("Proxy contract (upgradeable logic)", ("proxy", "upgrad")),
    ]
    active_traits = []
    if str(gp.get("is_honeypot")) == "1":
        active_traits.append(trait_checks[0])
    if str(gp.get("can_take_back_ownership")) == "1" or str(gp.get("owner_change_balance")) == "1":
        active_traits.append(trait_checks[1])
    if str(gp.get("is_proxy")) == "1":
        active_traits.append(trait_checks[2])

    hits = []
    for label, keywords in active_traits:
        match = next(
            (inc for inc in incidents if any(kw in (inc.get("technique") or "").lower() for kw in keywords)),
            None,
        )
        if match:
            hits.append(
                f"{label} — matches a real recent incident: {match['name']} (${match['amount_usd_m']}M, "
                f"{match['technique']}, {match['date']}, {', '.join(match.get('chains') or []) or 'unknown chain'})."
            )
        else:
            hits.append(f"{label} — no directly matching technique in the {len(incidents)} most recent tracked "
                         "incidents, but this remains a structural risk category.")
    return hits


# Strong, unambiguous scam-indicator keywords — deliberately narrow. Web
# search results are noisy and this is NOT run through an LLM to judge, so
# only react to language a human wouldn't mistake for anything else. This
# is meant to catch "this got rugged, discussed publicly" (real on-chain
# GoPlus/DexScreener data can't see that), not to score-judge sentiment.
_SCAM_KEYWORDS = ("rug pull", "rugpull", "rugged", "scam", "honeypot", "exit scam", "exploited", "hacked")


def _scrape_excerpt(url, max_len=400):
    """Escalate a search hit that already matched a scam keyword to a real
    full-page scrape (skillforge/research.py's Firecrawl -> Bright Data ->
    Apify -> keyless-fetch chain) instead of relying on the search engine's
    own ~200-char snippet. Deliberately only called for hits that already
    cleared the keyword bar — scraping is quota-limited (Firecrawl/Bright
    Data both cap well under their real free-tier ceilings, see
    skillforge/research.py's MONTHLY_QUOTA), so usage stays proportionate to
    actual signal instead of scraping every search result on every cycle."""
    try:
        from skillforge.research import scrape as web_scrape
    except Exception:
        return None
    try:
        res = web_scrape(url)
    except Exception:
        return None
    raw = res.get("raw")
    content = None
    if isinstance(raw, dict):
        content = raw.get("markdown") or raw.get("content") or raw.get("text")
    elif isinstance(raw, list) and raw and isinstance(raw[0], dict):
        content = raw[0].get("markdown") or raw[0].get("text") or raw[0].get("content")
    if not content:
        content = res.get("content")  # keyless-fetch shape (skillforge.research._fetch_keyless)
    if not isinstance(content, str) or not content.strip():
        return None
    return " ".join(content.split())[:max_len]


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
    scraped_one = False
    addr_lower = address.lower()
    sym_lower = (symbol or "").lower()
    for r in results[:5]:
        if not isinstance(r, dict):
            continue
        title = str(r.get("title") or "")
        snippet = str(r.get("content") or r.get("snippet") or r.get("description") or "")
        url = str(r.get("url") or "")
        normalized.append({"title": title, "url": url, "snippet": snippet[:200]})
        blob = f"{title} {snippet}".lower()
        # A broad OR-query like "... rug pull OR scam OR honeypot" reliably
        # surfaces popular GENERIC scam-education pages (a 2022 explainer
        # video, a rug-pull category page, etc.) for virtually any token,
        # since search engines don't literally AND every quoted term. Require
        # the result to actually reference THIS token (address, or a
        # reasonably specific symbol) before treating a keyword match as
        # real evidence — otherwise every token gets the same generic hits
        # and a false -25 penalty regardless of any real incident.
        mentions_target = addr_lower in blob or (len(sym_lower) >= 3 and sym_lower in blob)
        if mentions_target and any(kw in blob for kw in _SCAM_KEYWORDS):
            hit = f"Public web result flags this project: \"{title}\" — {url}"
            # Only escalate the first flagged hit per investigation to a real
            # scrape — a 200-char search snippet is thin evidence for a real
            # accusation, but scrape quota is shared across every hourly
            # investigation this cycle runs, so this stays proportionate.
            if not scraped_one and url:
                scraped_one = True
                excerpt = _scrape_excerpt(url)
                if excerpt:
                    hit += f"\n  - Scraped evidence: {excerpt}"
            hits.append(hit)
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
def score(gp, dex, onchain, verif, web_rep=None, deployer_repeat_offender=None, defillama=None,
          deployer_cluster_size=None, coingecko_contract=None):
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

    flag(str(gp.get("is_honeypot")) == "1", 60, "HONEYPOT detected")
    flag(str(gp.get("cannot_sell_all")) == "1", 30, "Cannot sell all tokens")
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

    # Recognized major stablecoin — real, address-verified (see
    # _coingecko_contract_intel()/_stablecoin_context()'s docstrings for the
    # exact real gap this closes: USDT scored 45/100 REJECT purely because
    # mint/owner-controlled-blacklist/unrenounced-owner are the DEFINING,
    # expected architecture of a compliant fiat-backed stablecoin — real
    # redemption mint/burn and sanctions-list freezing, not a rug surface —
    # yet tripped the exact same flags at full weight as an anonymous meme
    # token's identical-looking function signatures. Refunds those three
    # SPECIFIC penalties (never touches honeypot/hidden-owner/pausable-
    # transfers/tax/liquidity/etc., which stay real red flags for any token,
    # stablecoin or not) rather than skipping the flag() calls above, so the
    # raw GoPlus observation stays visible in `reasons` for transparency.
    stable_ctx = _stablecoin_context(coingecko_contract)
    if stable_ctx:
        refund = 0
        if str(gp.get("is_mintable")) == "1":
            refund += 12
        if str(gp.get("owner_change_balance")) == "1":
            refund += 25
        if owner_present:
            refund += 10
        if refund:
            s += refund
            reasons.append(
                f"[+{refund}] Verified major stablecoin ({stable_ctx['name']}, "
                f"${stable_ctx['market_cap_usd']:,.0f} circulating, ${stable_ctx['price_usd']:.4f} peg) — "
                "mint/owner-controlled-freeze/retained-ownership are standard compliance mechanisms for "
                "this category, not rug indicators; penalties above refunded"
            )
        signal(True, f"Verified as a real, market-data-recognized major stablecoin "
                     f"(${stable_ctx['market_cap_usd']:,.0f} circulating, ${stable_ctx['price_usd']:.4f} peg)")

    # Meme-factory template detection — real, deterministic (see
    # MEME_FACTORY_NAME_PATTERNS above), not a heuristic guess.
    cname = (verif.get("name") or "").lower()
    is_factory_template = any(p in cname for p in MEME_FACTORY_NAME_PATTERNS)
    flag(is_factory_template, 20,
         f"Deployed via a permissionless meme-token factory template ({verif.get('name')}) "
         "— no team vetting by design; this pattern strongly correlates with abandoned/rugged tokens")

    # Brand impersonation — real, deterministic (see IMPERSONATED_BRAND_PATTERNS
    # above). Confirmed real gap: VAPE's own investigation ledger has repeated
    # copycat tokens named exactly "OpenAI"/"Claude"/"CLAUDE" that scored
    # false PROCEEDs (78-92/100) because nothing previously checked whether a
    # clean-looking contract's declared name/symbol impersonates a real,
    # unaffiliated company riding AI/tech hype.
    dex_name_l = (dex.get("name") or "").lower()
    dex_sym_l = (dex.get("symbol") or "").lower()
    is_brand_impersonation = any(p in dex_name_l or p in dex_sym_l for p in IMPERSONATED_BRAND_PATTERNS)
    flag(is_brand_impersonation, 35,
         f"Token name/symbol ({dex.get('name')} / {dex.get('symbol')}) impersonates a real company "
         "with no on-chain affiliation — a hype-riding impersonation pattern, not coincidence")

    # Stablecoin-brand impersonation — the inverse of the verified-stablecoin
    # exception above. Real gap this closes: a token self-declaring symbol
    # "USDC" scored only 68/100 CAUTION (intel/investigations/investigation-
    # 20260725-041324-0x8dB2be2b.md) despite actually being "United States of
    # Doge CashCat," trading at $0.0001865 — nowhere near the real $1 peg it
    # trades on the strength of its stolen ticker — and never verified by
    # CoinGecko as the genuine address. Deliberately requires BOTH a matching
    # brand name/symbol AND a real, far-off-peg (or missing) price — not just
    # "unverified by CoinGecko," which a legitimate but thinly-tracked
    # bridged/wrapped stablecoin variant could also trip. A genuine ~$1 asset
    # that merely isn't in CoinGecko's contract index stays neutral here
    # (no bonus, no penalty); only an unmistakable price mismatch trips this.
    # Exact-symbol match (not substring) for short tickers — "dai" as a raw
    # substring would false-positive on any unrelated symbol that happens to
    # contain those three letters (e.g. "DAIYA"); the full descriptive-name
    # phrases ("usd coin", "tether") are long/distinctive enough to stay
    # safe as substrings of the declared name.
    dex_sym_stripped = dex_sym_l.strip()
    claims_stablecoin_brand = (
        dex_sym_stripped in STABLECOIN_BRAND_TICKERS
        or any(p in dex_name_l for p in STABLECOIN_BRAND_NAME_PHRASES)
    )
    if claims_stablecoin_brand and not stable_ctx:
        try:
            dex_price = float(dex.get("price_usd") or 0)
        except (TypeError, ValueError):
            dex_price = 0.0
        price_off_peg = dex_price <= 0 or abs(dex_price - 1.0) > 0.15
        flag(price_off_peg, 40,
             f"Token name/symbol ({dex.get('name')} / {dex.get('symbol')}) claims a major stablecoin "
             f"brand but trades at ${dex_price:.6f}, nowhere near the real $1 peg, and is not the "
             "independently-verified real asset at this address — brand impersonation, not a real stablecoin")

    # Deployer repeat-offender — real, ledger-derived (see
    # _deployer_repeat_offender() in the target-selection section below).
    # Confirmed real gap: several of the impersonation tokens above shared a
    # deployer fingerprint (same CREATE2 vanity address suffix) but were each
    # scored as a fully independent, unrelated target — this connects them.
    if deployer_repeat_offender:
        flag(True, 30, f"Same deployer has a prior CAUTION/REJECT verdict on record: "
                        f"{deployer_repeat_offender} — likely the same serial campaign")

    # Deployer factory-scale — a DISTINCT signal from the repeat-offender flag
    # above (see skillforge/memory/graph.py::sibling_tokens()). That flag only
    # fires once a prior token from this deployer already tripped CAUTION/
    # REJECT; a mass-token-factory deployer can rack up several tokens with
    # mixed early verdicts before any single one gets unlucky enough to hit
    # that bar. Deploy VOLUME itself, independent of those verdicts, is a real
    # risk signal a genuine one-off legitimate project won't have.
    if deployer_cluster_size:
        flag(True, 15, f"Deployer has {deployer_cluster_size} other token(s) on record "
                       "— mass-token-factory deployment pattern, independent of their individual verdicts")

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

    # Real top-holder concentration + LP-lock status — both already sitting
    # in GoPlus's own response every cycle (see _holder_concentration()/
    # _lp_lock_status() docstrings) but never previously read. Deliberately
    # moderate weights (smaller than the honeypot/mint/proxy penalties
    # above) since this is a newly-wired signal on a GoPlus response shape
    # this sandbox couldn't verify live — conservative until a real
    # production cycle confirms the field shapes match.
    concentration = _holder_concentration(gp)
    if concentration:
        top_pct = concentration["top_holders_pct"]
        flag(top_pct >= 70, 15, f"Top {concentration['holders_counted']} non-LP/burn holders control "
                                f"{top_pct:.0f}% of supply — concentrated, easily manipulated")
        flag(50 <= top_pct < 70, 8, f"Top {concentration['holders_counted']} non-LP/burn holders control "
                                    f"{top_pct:.0f}% of supply — meaningful concentration")
        signal(top_pct < 20, f"Top holders control only {top_pct:.0f}% of supply — broad distribution")

    lp_lock = _lp_lock_status(gp)
    if lp_lock:
        locked_pct = lp_lock["locked_pct"]
        flag(locked_pct < 50, 15, f"Only {locked_pct:.0f}% of liquidity is locked — "
                                  "the deployer can pull the rest at any time")
        signal(locked_pct >= 80, f"{locked_pct:.0f}% of liquidity is locked — reduced rug-pull risk")

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

    # DefiLlama cross-source signals — an INDEPENDENT oracle, not the same
    # DexScreener/GoPlus data re-counted. Two genuinely new, non-double-counting
    # checks: (1) DefiLlama's first-ever recorded price is a longevity source
    # that's harder to spoof than a DEX pair-creation timestamp (a token can
    # spin up a fresh pair but can't retroactively invent price history);
    # (2) DefiLlama's own price-confidence score flags thinly/unreliably priced
    # tokens the on-chain checks can't see.
    if defillama:
        fp = defillama.get("first_price") or {}
        dl_age = fp.get("age_days")
        if isinstance(dl_age, (int, float)):
            signal(dl_age >= 90, f"DefiLlama has priced this token for {dl_age:.0f}+ days — "
                                 "independent longevity corroboration")
        pr = defillama.get("price") or {}
        conf = pr.get("confidence")
        if isinstance(conf, (int, float)):
            flag(conf < 0.5, 8, f"DefiLlama price confidence low ({conf:.2f}) — "
                                "thinly or unreliably priced across venues")

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
    # NOTE: these 80/50 bands are mirrored by agents/critic.py::_verdict_for_score()
    # (its verdict/score-band consistency check needs its own copy to detect
    # drift here) — if you change these thresholds, update that function too.
    # tests/test_critic.py's zero-false-positive tests will fail loudly if
    # the two ever fall out of sync.
    verdict = "PROCEED" if s >= 80 else ("CAUTION" if s >= 50 else "REJECT")
    return s, verdict, reasons, positive_signals


# ── ephemeral assessment (no persistence) ───────────────────────────────────
# Same recon + scoring pipeline as investigate() (steps 1-3 of this module's
# own docstring), minus the report/ledger/memory/catalog writes — used by
# agents/acp_fulfill.py's paid dossier_check offering so a customer's
# on-demand call reuses VAPE's real heuristic engine (score, meme-factory
# detection, hack correlation, web-reputation search) without polluting the
# free investigation ledger/fail-caution-pass lists a paid, on-demand call
# has no business writing to.
def quick_assess(address, chain="8453"):
    address = address.strip()
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return {"error": f"invalid address: {address}"}
    gp = goplus_security(address, chain)
    dex = dexscreener(address, chain)
    onchain = onchain_presence(address, chain)
    verif = contract_verification(address, chain)
    corr = hack_correlation(gp)
    prelim_sym = dex.get("symbol") or verif.get("name") or "unknown"
    web_rep = web_reputation_check(prelim_sym, address)
    deployer_repeat = _deployer_repeat_offender(gp.get("creator_address"), chain, address)
    cg_contract = _coingecko_contract_intel(address, chain)
    s, verdict, reasons, positive_signals = score(gp, dex, onchain, verif, web_rep, deployer_repeat,
                                                   coingecko_contract=cg_contract)
    cname = (verif.get("name") or "").lower()
    is_factory_template = any(p in cname for p in MEME_FACTORY_NAME_PATTERNS)
    return {
        "address": address, "chain": chain, "symbol": prelim_sym,
        "score": s, "verdict": verdict, "reasons": reasons, "positive_signals": positive_signals,
        "gp": gp, "dex": dex, "onchain": onchain, "verif": verif,
        "hack_correlation": corr, "web_reputation": web_rep,
        "meme_factory_template": is_factory_template,
    }


# ── target selection ──────────────────────────────────────────────────────────
# Base stays the plurality/default chain (VAPE's core identity is Base +
# Virtuals), but the old version ONLY ever looked at Base — one single
# GeckoTerminal page, one chain, forever. Confirmed real consequence: weeks
# of hourly auto-cycles produced only 13 ever-investigated addresses total,
# several of them trivial copycat variants of the same brand-impersonation
# campaign, because the candidate pool was this narrow. Rotating across
# chains by hour-of-day (same technique already used in run.py's
# _repo_snapshot_for_review() for file coverage) opens real diversity —
# roughly 2 out of every 3 hourly cycles still check Base, the remaining
# third round-robins through the other supported EVM chains.
_OTHER_CHAINS = [c for c in EVM_CHAINS if c != "8453"]


def _pick_chain_for_hour(hour):
    if hour % 3 != 0 or not _OTHER_CHAINS:
        return "8453"
    return _OTHER_CHAINS[(hour // 3) % len(_OTHER_CHAINS)]


def auto_target(chain=None):
    """Pick the highest-signal target from live data (violent/low-liq movers)
    on the selected chain (rotates across all of EVM_CHAINS by hour if not
    given explicitly) that VAPE hasn't already reached a real verdict on —
    skip anything already in the ledger so auto mode never wastes a cycle
    re-discovering a target it's just going to turn around and skip anyway.
    Falls back to Base if the rotated-to chain's candidate pool comes up
    empty (e.g. thin GeckoTerminal coverage for that network), so a single
    exotic chain never silently zeroes out a whole cycle's auto-investigation."""
    if not DF:
        return None
    chain = chain or _pick_chain_for_hour(datetime.now(timezone.utc).hour)
    # Real bug this fixes: with 260+ investigations already in the ledger, a
    # bare top-10-movers pool on a single chain (or two) now frequently comes
    # up fully exhausted (every candidate already investigated) — confirmed
    # directly in production: two consecutive real cycles (2026-07-20 17:03
    # and 19:13 UTC) both logged "no auto target found this cycle" with
    # chains_to_try == ["8453"] only, silently starving agents/data_agent.py
    # (Base-only) of any recruitment opportunity for hours. Base is always
    # tried first-or-second (whichever the hour-rotation didn't already
    # pick), then every other known chain gets a turn too, so a temporarily
    # exhausted pool on any single chain never zeroes out a whole cycle —
    # "no target anywhere" is now a true last resort, not a common outcome.
    chains_to_try = list(dict.fromkeys([chain, "8453"] + list(EVM_CHAINS.keys())))

    ledger = _load_ledger()
    for cid in chains_to_try:
        chain_info = EVM_CHAINS.get(cid)
        if not chain_info:
            continue
        get_movers = getattr(DF, "get_evm_movers", None)
        # limit bumped 10 -> 40 for the same reason — a deeper well of
        # candidates before a chain's pool counts as exhausted.
        movers = get_movers(chain_info["gecko"], limit=40) if get_movers else (
            DF.get_base_movers(limit=40) if cid == "8453" else {})
        cands = movers.get("biggest_movers") or []
        for m in cands:
            # movers from GeckoTerminal are pool-named; we need a token address, so we
            # search DexScreener for the symbol to resolve an address.
            name = (m.get("name") or "").split("/")[0].strip()
            if not name:
                continue
            d = _get(f"https://api.dexscreener.com/latest/dex/search?q={urllib.parse.quote(name)}")
            for p in (d.get("pairs") or []) if isinstance(d, dict) else []:
                if str(p.get("chainId", "")).lower() == chain_info["dex"]:
                    addr = (p.get("baseToken") or {}).get("address")
                    if addr and not ledger.get(_ledger_key(addr, cid)) and not (
                            cid == "8453" and addr.lower() in ledger):
                        return {"address": addr, "chain": cid,
                                "hint": f"auto: {chain_info['name']} mover {m.get('name')} {m.get('change_24h_pct')}%"}
    return None


# Ordered (category, keywords) buckets for _categorize_report_reasons() below
# — order matters, first match wins, so more specific categories are listed
# before general ones (e.g. a stablecoin-peg reason mentions "supply" too,
# but "peg"/"stablecoin" should bucket it under Tokenomics, not Distribution).
_RISK_CATEGORIES = (
    ("Security & Contract Risk", (
        "honeypot", "mintable", "mint function", "ownership can be reclaimed",
        "take back ownership", "change balances", "hidden owner", "proxy",
        "pausable", "buy tax", "sell tax", "not renounced", "renounced",
    )),
    ("Tokenomics & Track Record", (
        "peg", "stablecoin", "impersonat", "days old", "track record", "violent",
        "volatility", "24h move", "fdv", "dilution",
    )),
    ("Holder Distribution & Liquidity", (
        "holder", "liquidity", "supply", "locked", "concentrat", "distribution",
        "manipulated",
    )),
    ("Transparency & Provenance", (
        "audit", "verified source", "unverified", "factory", "template",
        "deployer", "web search", "scam", "rug", "eoa", "no contract code",
    )),
)


def _bucket_for_report_reason(text):
    """First category (in _RISK_CATEGORIES' declared order) whose keyword
    appears in `text`, or "Other" if none match. Used by
    _categorize_report_reasons() below for the report's "Risk Breakdown by
    Category" section."""
    low = text.lower()
    for name, keywords in _RISK_CATEGORIES:
        if any(k in low for k in keywords):
            return name
    return "Other"


def _categorize_report_reasons(reasons, positive_signals):
    """Buckets score()'s already-computed reasons/positive_signals into
    named risk categories, purely for report presentation — no new data
    fetched, no scoring change; the multi-dimensional "how does this rank"
    view requested directly by the user, built from what score() already
    produces. Never raises — an unexpected reason string just falls through
    to "Other" rather than crashing report generation."""
    buckets = {name: {"flags": [], "signals": []} for name, _ in _RISK_CATEGORIES}
    buckets["Other"] = {"flags": [], "signals": []}
    for r in reasons or []:
        buckets[_bucket_for_report_reason(r)]["flags"].append(r)
    for p in positive_signals or []:
        buckets[_bucket_for_report_reason(p)]["signals"].append(p)
    # Preserve category declaration order, then "Other" last; drop empty ones.
    ordered_names = [name for name, _ in _RISK_CATEGORIES] + ["Other"]
    return [(name, buckets[name]) for name in ordered_names
            if buckets[name]["flags"] or buckets[name]["signals"]]


# Matches score()'s own flag()/stablecoin-refund reason-string convention:
# "[-N] ..." for a penalty, "[+N] ..." for the stablecoin-exception refund.
# Does NOT match "[capped at N] ..." (the global legitimacy cap) — that's a
# whole-score adjustment, not attributable to any one category.
_REASON_WEIGHT_RE = re.compile(r"^\[([+-])(\d+)\]")


# ── Scoring Dashboard: weighted, multi-factor category scores ──────────────
# Replaces the old flat Executive Summary table (100 minus whichever of
# score()'s flags happened to keyword-bucket into that name — real weights
# from score()'s own penalty magnitudes, but blind to anything score() itself
# never scores; there was no way to show low narrative/social proof as a
# category weak point when no rule ever flagged it). This still isn't a
# second scoring engine — score()'s own number/verdict stays the one
# authoritative source of truth — but each category here draws on real,
# direct signals beyond score()'s reason strings where those exist (declared
# website/social presence, whether a real project narrative was actually
# established), not just a keyword-matched net of the same flags every other
# view already shows.
_CATEGORY_WEIGHTS = (
    ("Contract Security & Controls", 0.25),
    ("Liquidity Health & Lock Quality", 0.20),
    ("Holder Distribution & Concentration", 0.15),
    ("Transparency & Provenance", 0.15),
    ("Narrative Strength & Social Proof", 0.15),
    ("Longevity & Clean Track Record", 0.10),
)

# Short badge labels for the Scoring Dashboard's score_badge() column — the
# full category name is already the table's row label, so the badge itself
# only needs a compact, distinct tag.
_CATEGORY_SHORT_LABEL = {
    "Contract Security & Controls": "security",
    "Liquidity Health & Lock Quality": "liquidity",
    "Holder Distribution & Concentration": "holders",
    "Transparency & Provenance": "transparency",
    "Narrative Strength & Social Proof": "narrative",
    "Longevity & Clean Track Record": "longevity",
}

# Keyword buckets for the 5 categories that DO have real coverage in
# score()'s own reasons/positive_signals — first match wins, most specific
# first. Deliberately excludes "Narrative Strength & Social Proof": score()
# has no rule that ever produces a narrative/social reason string (that's
# exactly the gap this dashboard closes), so that category is built entirely
# from direct signals in _compute_category_scores() below instead.
_CATEGORY_KEYWORDS = (
    ("Contract Security & Controls", (
        "honeypot", "cannot sell", "mintable", "mint function",
        "ownership can be reclaimed", "take back ownership", "change balances",
        "hidden owner", "proxy", "pausable", "buy tax", "sell tax",
        "not renounced", "renounced",
    )),
    ("Liquidity Health & Lock Quality", ("liquidity", "locked")),
    ("Holder Distribution & Concentration", ("holder", "concentrat", "distribution", "manipulated", "supply")),
    ("Transparency & Provenance", (
        "audit", "verified source", "unverified", "factory", "template",
        "deployer", "web search", "scam", "rug", "eoa", "no contract code",
        "peg", "stablecoin", "impersonat", "fdv", "dilution",
    )),
    ("Longevity & Clean Track Record", (
        "days old", "track record", "violent", "volatility", "24h move", "defillama",
    )),
)


def _bucket_for_category_dashboard(text):
    low = text.lower()
    for name, keywords in _CATEGORY_KEYWORDS:
        if any(k in low for k in keywords):
            return name
    return None


def _category_rationale(name, score, hits):
    """One short, human-readable sentence per category row — the user's
    explicit ask that each row carry a real rationale, not just a bare
    number. Built from the same hits (flags/signals/direct notes) the score
    itself was netted against, so the sentence can never say something the
    number doesn't back up."""
    if not hits:
        return "No signal either way this cycle." if score == 100 else "Derived from the evidence above."
    return "; ".join(hits[:3]) + ("." if not hits[0].endswith(".") else "")


def _compute_category_scores(reasons, positive_signals, dex=None, project_narrative=None, web_rep=None):
    """Six weighted 0-100 category scores + a one-line rationale each, for
    the report's Scoring Dashboard. Presentation-layer instrumentation, same
    as _category_subscores() above — score()'s deterministic number/verdict
    is never derived FROM these, only alongside them, so a caller can't
    accidentally let a report's headline verdict drift from the one real
    scoring engine. Never raises; missing evidence just leaves a category at
    its neutral baseline rather than crashing report generation."""
    totals = {name: 100.0 for name, _ in _CATEGORY_WEIGHTS}
    hits = {name: [] for name, _ in _CATEGORY_WEIGHTS}

    for r in reasons or []:
        m = _REASON_WEIGHT_RE.match(r)
        if not m:
            continue
        name = _bucket_for_category_dashboard(r)
        if not name:
            continue
        delta = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
        totals[name] += delta
        if delta < 0:
            hits[name].append(r.split("]", 1)[-1].strip())
    for p in positive_signals or []:
        name = _bucket_for_category_dashboard(p)
        if name:
            hits[name].append(f"(+) {p}")

    # Narrative Strength & Social Proof — the one category score() has no
    # rule for at all. A real anonymous/undocumented token starts LOW here
    # (missing narrative/social surface is itself a disclosed risk, the
    # same "absence of evidence isn't evidence of safety" principle score()
    # already applies via its legitimacy cap), not neutral at 100 the way
    # an untouched keyword bucket would default to.
    narrative_score = 20.0
    narrative_hits = []
    site_links = [w.get("url") for w in ((dex or {}).get("websites") or []) if w.get("url")]
    social_links = [soc for soc in ((dex or {}).get("socials") or []) if soc.get("url")]
    if site_links:
        narrative_score += 25
        narrative_hits.append("has a declared project website")
    if social_links:
        narrative_score += 15 * min(2, len(social_links))
        narrative_hits.append(f"{len(social_links)} declared social link(s)")
    if project_narrative and project_narrative.get("text"):
        if project_narrative.get("address_identity_verified"):
            narrative_score += 25
            narrative_hits.append("a real, address-verified project narrative was established")
        else:
            narrative_score += 10
            narrative_hits.append("a narrative exists but this contract's affiliation with it is unverified")
    else:
        narrative_hits.append("no coherent project narrative could be established this cycle")
    if web_rep and web_rep.get("available") and not web_rep.get("hits"):
        narrative_score += 5
    totals["Narrative Strength & Social Proof"] = narrative_score
    hits["Narrative Strength & Social Proof"] = narrative_hits

    result = {}
    for name, weight in _CATEGORY_WEIGHTS:
        score = max(0, min(100, round(totals[name])))
        result[name] = {"score": score, "weight": weight,
                         "rationale": _category_rationale(name, score, hits[name])}
    return result


# ── report + persistence ────────────────────────────────────────────────────
def write_report(target, chain, gp, dex, onchain, verif, corr, s, verdict, reasons, positive_signals, web_rep=None,
                 defillama=None, deployer_siblings=None, critic_result=None, data_agent_intel=None,
                 expert_assessment=None, coingecko_contract=None, project_narrative=None):
    os.makedirs(INVEST_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    short = target[:10]
    path = os.path.join(INVEST_DIR, f"investigation-{stamp}-{short}.md")
    # dex["symbol"]/verif["name"] are sanitized at the source (dexscreener()/
    # contract_verification() below) — safe to embed directly everywhere.
    sym = dex.get("symbol") or verif.get("name") or "unknown"
    # Real, currently-live production bug fixed here: PR #78 (2026-07-05)
    # replaced the in-body emoji badges with verdict_stamp()'s image badge
    # but never updated this function's `return path, sym, emoji` (or the
    # caller's unpacking / print statement) to match — `emoji` was never
    # assigned anywhere, so every single call to write_report() has been
    # raising an unconditional NameError on its own return statement ever
    # since. Confirmed real consequence: since this crash happens AFTER the
    # .md report is written but BEFORE investigate() reaches log_memory()/
    # update_catalog()/_update_ledger(), every real auto-cycle and
    # review_ledger.py re-check for the past ~33 hours wrote a report file
    # but never recorded it in the ledger — which is exactly why
    # review_ledger.py's "oldest-checked first" sampler kept re-selecting
    # the same frozen-timestamp address over and over (six re-investigations
    # of one address in 13 hours, observed directly in intel/investigations/).
    emoji = {"PROCEED": "🟢", "CAUTION": "🟡", "REJECT": "🔴"}.get(verdict, "⚪")

    L = []
    L.extend(letterhead_md(f"Investigation — {sym}"))
    L.append(verdict_stamp(verdict, s))
    L.append("")
    # Plain-text bullets (not just the badge above) — agents/run.py's
    # _recent_investigations() greps for lines starting with "# " or
    # "- **" to build LLM grounding context, so the verdict has to exist in
    # that form somewhere too, not only as a "![...]" badge image line.
    L.append(f"- **Target:** `{target}`")
    chain_display = (EVM_CHAINS.get(str(chain)) or {}).get("name", "unknown")
    L.append(f"- **Chain:** {chain} ({chain_display})")
    L.append(f"- **Date:** {now_iso()}")
    L.append(f"- **Verdict:** {verdict} ({s}/100)")
    L.append("")
    L.append("---")
    L.append("")
    # Real gap this closes: the Expert Assessment used to sit halfway down
    # the report, framed as a second opinion "agreeing/disagreeing" with the
    # verdict above it — two agents seemingly arguing, instead of the
    # detective's own primary conclusion. It's the first substantive section
    # now (right after the header), and never surfaces agree/disagree
    # language — that internal signal still exists and still feeds
    # self_improve.py/review_ledger.py (see _log_expert_disagreement()), it
    # just isn't published as a rendered tag anymore. The categorized
    # rule-based numbers below are supporting instrumentation for this
    # judgment, not the other way around.
    L.append("## Expert Assessment")
    if expert_assessment and expert_assessment.get("text"):
        L.append(expert_assessment["text"])
    else:
        L.append("- Expert assessment not available this cycle.")
    L.append("")
    # Real gap this closes: a single flat score/verdict doesn't show WHERE a
    # token is strong vs. weak, and there was no top-level composite view at
    # all — the user's explicit template ask ("Executive Summary + Overall
    # Ranking Score, composite with category breakdown ... -> overall
    # rank"). Replaces that flat "100 minus whichever flags happened to
    # keyword-bucket here" table with real per-category weights and a
    # one-line rationale each (_compute_category_scores()'s docstring) --
    # still purely presentation-layer: score()'s own number/verdict above
    # remains the one authoritative source of truth, never derived from
    # this weighted sum.
    L.append("## Scoring Dashboard")
    L.append(f"**Overall: {s}/100 — {verdict}** {score_badge(s, label='overall')}")
    L.append("")
    L.append("| Category | Weight | Score | Rationale |")
    L.append("|---|---|---|---|")
    categories = _compute_category_scores(reasons, positive_signals, dex=dex,
                                          project_narrative=project_narrative, web_rep=web_rep)
    for name, cat in categories.items():
        badge = score_badge(cat["score"], label=_CATEGORY_SHORT_LABEL.get(name, name))
        L.append(f"| {name} | {cat['weight']*100:.0f}% | {badge} | {cat['rationale']} |")
    L.append("")
    L.append("*Weighted, multi-factor category view for where the risk actually concentrates — "
             "the Overall score above, computed by the full deterministic scoring engine, is the "
             "authoritative verdict; these categories are supporting instrumentation, not a second "
             "scoring engine.*")
    L.append("")
    # Real gap this closes: the user's explicit template ask for a "Project
    # Overview & Narrative" section (what it is, utility, traction, history/
    # turnaround) and "Team, Community & Social Signals" -- neither existed
    # anywhere in this report before. Grounded in a real, dedicated web
    # search + frontier LLM synthesis (see _project_narrative()'s docstring
    # for why this is a separate call from Expert Assessment below, not a
    # restatement of it) — degrades to an honest "not available" line
    # rather than a fabricated placeholder when the search/LLM path fails.
    L.append("## Project Overview & Narrative")
    if project_narrative and project_narrative.get("text"):
        # Real gap this closes (CodeRabbit, PR #282): the LLM is instructed to
        # open its own narrative with an unverified-identity caveat when
        # address_identity_verified is False, but relying solely on the model
        # to remember and phrase that correctly every time is fragile — a
        # reader should see this warning even if the model's own text buries
        # or softens it. Rendered here, independent of the LLM's output, from
        # the same signal (_project_narrative()'s CoinGecko /contract/{address}
        # check — see its docstring) that drove the prompt instruction.
        if not project_narrative.get("address_identity_verified"):
            L.append("> ⚠️ **Unverified identity**: this contract's affiliation with the "
                     "project described below has NOT been independently confirmed. The "
                     "name/symbol is only self-declared by the token — the search results "
                     "and narrative below could describe a real but unrelated project whose "
                     "name/branding this contract has simply reused.")
            L.append("")
        L.append(project_narrative["text"])
        if project_narrative.get("sources"):
            L.append("")
            L.append("Sources: " + ", ".join(project_narrative["sources"]))
    else:
        L.append("- Not available this cycle (web search/LLM path unavailable, or no relevant "
                 "results found) — absence noted, not fabricated.")
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
    # Real gap this closes: a flat single score/verdict doesn't tell a reader
    # WHERE a token is strong vs. weak (e.g. clean security but concentrated
    # holders, or the reverse) -- flagged directly by the user as a missing
    # "rank across categories, not just pass/fail" view. Pure presentation
    # over the exact reasons/positive_signals already computed above; no new
    # scoring, no new data.
    L.append("## Risk Breakdown by Category")
    categorized = _categorize_report_reasons(reasons, positive_signals)
    if categorized:
        for name, bucket in categorized:
            L.append(f"**{name}** — {len(bucket['flags'])} flag(s), {len(bucket['signals'])} positive signal(s)")
            for r in bucket["flags"]:
                L.append(f"  - {r}")
            for p in bucket["signals"]:
                L.append(f"  - (positive) {p}")
        L.append("")
    else:
        L.append("- Nothing to categorize this cycle.")
        L.append("")
    L.append("## Market & Liquidity")
    if dex:
        L.append(f"- Symbol/Name: {dex.get('symbol')} / {dex.get('name')}")
        L.append(f"- Price: ${dex.get('price_usd')}")
        L.append(f"- Liquidity: ${dex.get('liquidity_usd')}")
        L.append(f"- 24h Volume: ${dex.get('vol_24h_usd')}")
        L.append(f"- 24h Change: {dex.get('change_24h_pct')}%")
        L.append(f"- DEX: {dex.get('dex')}")
        # Real gap this closes: DexScreener's own multi-window (m5/h1/h6/h24)
        # price-change and volume fields were already fetched but only the
        # single h24 figure ever survived into the report -- a real, if
        # short, trend line existed and was discarded every cycle. Rendered
        # as a compact sparkline (_sparkline()'s docstring) over exactly
        # those real points, oldest-to-newest; never shown when fewer than 2
        # real windows are on hand, never interpolated.
        pcw = dex.get("price_change_windows") or {}
        vw = dex.get("volume_windows") or {}
        window_order = ("m5", "h1", "h6", "h24")
        pcw_keys = [k for k in window_order if k in pcw]
        vw_keys = [k for k in window_order if k in vw]
        pcw_spark = _sparkline([pcw[k] for k in pcw_keys])
        vw_spark = _sparkline([vw[k] for k in vw_keys])
        if pcw_spark:
            L.append(f"- Price-change trend ({'/'.join(pcw_keys)}): `{pcw_spark}` "
                     f"({', '.join(f'{k}: {pcw[k]:+.1f}%' for k in pcw_keys)})")
        if vw_spark:
            L.append(f"- Volume trend ({'/'.join(vw_keys)}): `{vw_spark}` "
                     f"({', '.join(f'{k}: ${vw[k]:,.0f}' for k in vw_keys)})")
        # Real gap this closes: liquidity and market cap were both already
        # fetched (DexScreener + CoinGecko contract lookup, the same call
        # already used for the Tokenomics section below) but the ratio
        # between them -- a standard "how deep is this market relative to
        # its size" metric -- was never computed. Only shown when both real
        # numbers are on hand; never estimated.
        try:
            liq_val = float(dex.get("liquidity_usd") or 0)
        except (TypeError, ValueError):
            liq_val = 0
        mcap_val = coingecko_contract.get("market_cap_usd") if isinstance(coingecko_contract, dict) else None
        if liq_val > 0 and isinstance(mcap_val, (int, float)) and mcap_val > 0:
            ratio_pct = (liq_val / mcap_val) * 100
            L.append(f"- Liquidity/Market-cap ratio: {ratio_pct:.1f}% — "
                     f"{'thin relative to market cap' if ratio_pct < 3 else 'reasonable depth for its size'}")
    else:
        L.append("- No DEX pair data (illiquid / not listed).")
    L.append("")
    # Real gap this closes: dexscreener()'s "websites"/"socials"/"logo_url"
    # fields were already fetched every single cycle but never rendered
    # anywhere in this free report -- only the paid deep-dive audit surfaced
    # them (agents/deep_dive_audit.py). A real report has to name what the
    # project actually is and link to its own claimed official presence
    # (confirmed missing: investigation-20260725-155143-0xB8d7710f.md, an
    # ARENA/Avalanche report with no official links at all despite
    # DexScreener tracking a real website + X account for it).
    L.append("## Project Links")
    site_links = [w.get("url") for w in (dex.get("websites") or []) if w.get("url")]
    social_links = [f"{soc.get('type') or 'link'}: {soc.get('url')}"
                    for soc in (dex.get("socials") or []) if soc.get("url")]
    if site_links or social_links:
        for u in site_links:
            L.append(f"- Website: {u}")
        for s_line in social_links:
            L.append(f"- {s_line}")
    else:
        L.append("- No official website/social links declared for this token.")
    L.append("")
    # Real gap this closes: get_token_market_by_contract() already fetches
    # CoinGecko's full contract-address response (needed for the stablecoin-
    # verification check above) but used to discard supply/FDV/description --
    # exactly the "tokenomics" and "what is this" context a real report needs
    # and this one previously had none of. Only rendered when CoinGecko
    # actually tracks this exact address -- absence stays an honest "not
    # available", never a fabricated number.
    L.append("## Tokenomics (address-verified)")
    if coingecko_contract and isinstance(coingecko_contract, dict):
        cg = coingecko_contract
        had_any = False
        if cg.get("circulating_supply") is not None:
            L.append(f"- Circulating supply: {cg['circulating_supply']:,.0f} {cg.get('symbol', '').upper()}")
            had_any = True
        if cg.get("total_supply") is not None:
            L.append(f"- Total supply: {cg['total_supply']:,.0f}")
            had_any = True
        if cg.get("max_supply") is not None:
            L.append(f"- Max supply: {cg['max_supply']:,.0f}")
            had_any = True
        if cg.get("market_cap_usd") is not None:
            L.append(f"- Market cap: ${cg['market_cap_usd']:,.0f}")
            had_any = True
        if cg.get("fdv_usd") is not None:
            L.append(f"- Fully diluted valuation: ${cg['fdv_usd']:,.0f}")
            had_any = True
        if cg.get("market_cap_usd") and cg.get("fdv_usd"):
            ratio = cg["fdv_usd"] / cg["market_cap_usd"] if cg["market_cap_usd"] else None
            if ratio:
                L.append(f"- FDV/Market-cap ratio: {ratio:.2f}x — "
                         f"{'a meaningful share of supply is still non-circulating (dilution risk)' if ratio > 1.3 else 'most of supply is already circulating'}")
                had_any = True
        if cg.get("homepage"):
            L.append(f"- Homepage: {cg['homepage']}")
            had_any = True
        if cg.get("twitter"):
            L.append(f"- X/Twitter: https://x.com/{cg['twitter']}")
            had_any = True
        if cg.get("description"):
            L.append("")
            L.append(f"> {cg['description']}")
            had_any = True
        if not had_any:
            L.append("- This address is tracked but returned no supply/valuation fields this cycle.")
    else:
        L.append("- Not available this cycle (no tokenomics data tracked for this exact contract "
                 "address, or the token isn't indexed yet) — absence noted, not penalized.")
    L.append("")
    L.append("## Token Security")
    if gp:
        for k in ("is_honeypot", "buy_tax", "sell_tax", "is_mintable", "is_proxy",
                  "can_take_back_ownership", "owner_change_balance", "hidden_owner",
                  "cannot_sell_all", "transfer_pausable", "holder_count", "owner_address"):
            if k in gp:
                L.append(f"- {k}: `{gp.get(k)}`")
    else:
        L.append("- No security profile available for this token this cycle.")
    L.append("")
    # Real gap this closes: GoPlus's own "holders"/"lp_holders" arrays
    # (per-address concentration, per-LP-holder lock status) were already
    # fetched inside `gp` every cycle but never surfaced anywhere -- a raw
    # holder_count alone can't distinguish broad organic distribution from
    # a few whales plus a long dust tail, and no report ever showed whether
    # liquidity was actually locked. See _holder_concentration()/
    # _lp_lock_status() docstrings for the honest-degradation caveat on
    # GoPlus's exact field shape.
    L.append("## Holder Distribution & Liquidity Lock")
    concentration = _holder_concentration(gp)
    lp_lock = _lp_lock_status(gp)
    if concentration:
        L.append(f"- Top {concentration['holders_counted']} non-LP/burn holders control "
                 f"{concentration['top_holders_pct']:.1f}% of supply")
    else:
        L.append("- Top-holder concentration not available this cycle.")
    if lp_lock:
        L.append(f"- {lp_lock['locked_pct']:.1f}% of tracked liquidity-pool tokens are locked "
                 f"(across {lp_lock['lp_holders_counted']} LP holder(s))")
    else:
        L.append("- Liquidity-lock status not available this cycle.")
    L.append("")
    L.append(f"## On-chain Presence ({chain_display} RPC)")
    if onchain.get("is_contract") is None:
        L.append(f"- Is contract: unavailable this cycle ({onchain.get('error', 'RPC call failed')})")
    else:
        L.append(f"- Is contract: {onchain.get('is_contract')}")
        L.append(f"- Code size: {onchain.get('code_size_bytes')} bytes")
    L.append("")
    L.append("## Contract Verification")
    if verif.get("checked"):
        L.append(f"- Verified: {verif.get('verified')}")
        L.append(f"- Name: {verif.get('name')} · Compiler: {verif.get('compiler')}")
        L.append(f"- Proxy: {verif.get('proxy')} · Implementation: {verif.get('implementation')}")
        # Real gap this closes: the verified source was already fetched
        # (same call, no extra API cost) but discarded -- the user flagged
        # "no insight into constructor plus any role or treasury functions"
        # as missing from a live report. Purely informational: a text-based
        # function-name scan can't tell a dangerous privileged function
        # apart from a harmless one with a similar name, so this is never
        # fed into score() (see _scan_privileged_functions()'s docstring).
        scan = _scan_privileged_functions(verif.get("source_code"))
        if scan:
            if scan["functions"]:
                L.append(f"- Notable functions found in verified source (informational, not scored): "
                         f"{', '.join(scan['functions'])}")
            else:
                L.append("- No notable privileged-sounding function names found in verified source.")
            if scan["has_selfdestruct"]:
                L.append("- ⚠️ Verified source contains a `selfdestruct`-family call.")
            if scan["has_delegatecall"]:
                L.append("- Verified source contains `delegatecall` (expected for proxies; worth a manual look otherwise).")
        else:
            L.append("- Verified source not available to scan this cycle.")
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
    L.append("## DefiLlama Cross-Source (independent oracle)")
    if defillama:
        pr = defillama.get("price") or {}
        fp = defillama.get("first_price") or {}
        if pr:
            conf = pr.get("confidence")
            L.append(f"- Price: ${pr.get('price')} · confidence: "
                     f"{conf if conf is not None else 'n/a'} · symbol: {pr.get('symbol')}")
        if fp:
            L.append(f"- First DefiLlama price: {fp.get('first_seen_iso')} "
                     f"({fp.get('age_days')} days ago) — independent longevity source")
        if not pr and not fp:
            L.append("- DefiLlama does not price this token (obscure / not yet on the oracle) "
                     "— absence noted, not penalized.")
    else:
        L.append("- DefiLlama cross-source not fetched this cycle.")
    L.append("")
    L.append("## Data Agent Intel (VAPE's own x402 spend)")
    if data_agent_intel and data_agent_intel.get("hired"):
        paid_n = sum(1 for h in data_agent_intel["hired"] if h["paid"])
        L.append(f"- DATA AGENT hired {len(data_agent_intel['hired'])} of VAPE's own x402 "
                 f"market-data offerings against this token (real USDC on Base, {paid_n} settled, "
                 f"${data_agent_intel.get('cost_usd', 0):.2f} total):")
        for h in data_agent_intel["hired"]:
            tag = "settled" if h["paid"] else "failed"
            fac = f", {h['facilitator']}" if h.get("facilitator") else ""
            L.append(f"  - **{h['offering']}** ({tag}{fac}) — {_fmt_data_agent_deliverable(h['deliverable'])}")
    elif data_agent_intel and data_agent_intel.get("note"):
        L.append(f"- {data_agent_intel['note']}")
    else:
        L.append("- Data agent not recruited this cycle.")
    L.append("")
    L.append("## Deployer Network (skillforge/memory/graph.py)")
    if deployer_siblings:
        L.append(f"- This deployer has **{len(deployer_siblings)}** other token(s) on record "
                 "(worst-verdict-first):")
        for sib in deployer_siblings:
            L.append(f"  - `{sib['address']}` — {sib.get('symbol')} — {sib.get('verdict')} "
                     f"({sib.get('score')}/100)")
    else:
        L.append("- No other tokens from this deployer on record yet.")
    L.append("")
    L.append("## Critic Self-Audit (agents/critic.py)")
    if critic_result and not critic_result.get("ok", True):
        L.append("- ⚠️ **Consistency issue(s) flagged** — this investigation's own reasons/signals "
                 "did not fully agree with the raw evidence or score()'s own invariants:")
        for issue in critic_result["issues"]:
            L.append(f"  - {issue}")
        L.append("  - Logged to Memory for self_improve.py triage.")
    else:
        L.append("- No structural inconsistencies found — reasons, positive signals, verdict and "
                 "score all agree with the raw evidence and score()'s own invariants.")
    L.append("")
    # Real gap this closes: every claim above was already backed by a real
    # source, but none of those sources were ever linked for a reader to
    # independently re-verify -- confirmed missing in a live report,
    # investigation-20260725-155143-0xB8d7710f.md ("Sources, Methodology,
    # Limitations" flagged as absent). Every link here is either a direct,
    # already-known field (DexScreener's own pair URL) or built from a
    # static, versioned map (EXPLORER_URLS) -- never a guessed/constructed
    # third-party URL.
    L.append("## Sources & Verification Links")
    explorer = EXPLORER_URLS.get(str(chain))
    if explorer:
        L.append(f"- Block explorer: {explorer}/address/{target}")
    if dex and dex.get("pair_url"):
        L.append(f"- Market pair: {dex['pair_url']}")
    if coingecko_contract and coingecko_contract.get("coingecko_id"):
        L.append(f"- Market data: https://www.coingecko.com/en/coins/{coingecko_contract['coingecko_id']}")
    L.append("- On-chain security, contract-verification, and market-data sources were queried "
             "directly for the sections above; this list only covers human-clickable pages for "
             "independent re-verification.")
    L.append("")
    L.append("---")
    L.append("")
    L.append("*V.A.P.E. — investigation conducted with keyless, "
             "real-data recon (on-chain token-safety data, market/liquidity data, contract "
             "verification, and a cross-chain hack-incident feed) plus a real web search for "
             "public reputation signals.*")
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


def log_memory(target, sym, verdict, s, reasons, report_rel, chain="8453"):
    if not append_to_memory:
        return
    chain_tag = (EVM_CHAINS.get(str(chain)) or {}).get("gecko", "base")
    try:
        append_to_memory(
            category="finding",
            title=f"Investigation: {sym} ({target[:10]}) → {verdict} {s}/100",
            content="; ".join(reasons)[:1800] or "clean across automated checks",
            source="agents/investigate.py",
            tags=["investigation", chain_tag, verdict.lower(), sym.lower()],
            confidence=0.9 if verdict != "CAUTION" else 0.75,
            metadata={"target": target, "chain": str(chain), "score": s, "verdict": verdict, "report": report_rel},
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


def _ledger_key(address, chain="8453"):
    # Chain-qualified so the same address on two different EVM chains (rare,
    # but real via CREATE2 or coincidence) doesn't collide in the ledger.
    return f"{chain}:{address.lower()}"


def ledger_entry(address, chain="8453"):
    ledger = _load_ledger()
    entry = ledger.get(_ledger_key(address, chain))
    if entry is not None:
        return entry
    # Legacy fallback: every entry written before multi-chain support was
    # keyed by bare lowercase address (implicitly Base). Without this, the
    # migration would silently re-investigate every address already on
    # record the first time this runs post-upgrade.
    if str(chain) == "8453":
        return ledger.get(address.lower())
    return None


def _deployer_repeat_offender(creator_address, chain, exclude_address):
    """Scan the ledger for another address (excluding this one) sharing the
    same deployer/creator with a prior CAUTION or REJECT verdict. Returns a
    short description if found, else None. This is what connects serial
    copycat campaigns (same deployer, different vanity address each time)
    instead of scoring every variant as a fully independent unknown target."""
    if not creator_address:
        return None
    creator_l = creator_address.lower()
    exclude_key = _ledger_key(exclude_address, chain)
    for key, entry in _load_ledger().items():
        if key == exclude_key:
            continue
        if (entry.get("creator_address") or "").lower() != creator_l:
            continue
        if entry.get("last_verdict") in ("CAUTION", "REJECT"):
            return f"{entry.get('symbol', '?')} ({entry.get('address', key)}) — {entry.get('last_verdict')} {entry.get('last_score')}/100"
    return None


def _update_ledger(address, sym, verdict, s, report_rel, chain="8453", creator_address=None):
    ledger = _load_ledger()
    key = _ledger_key(address, chain)
    # Migrate a legacy bare-address entry to the chain-qualified key on first
    # re-touch, rather than leaving a stale duplicate behind.
    legacy_key = address.lower()
    prior = ledger.pop(legacy_key, None) if str(chain) == "8453" and legacy_key in ledger else None
    entry = ledger.get(key) or prior or {"first_investigated": now_iso(), "times_investigated": 0, "history": []}
    entry["address"] = address  # original checksum/case, for display — key stays lowercase for lookup
    entry["chain"] = str(chain)
    entry["symbol"] = sym
    if creator_address:
        entry["creator_address"] = creator_address
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
                 "", "| Symbol | Chain | Address | Score | Times Checked | Last Investigated |",
                 "|--------|-------|---------|-------|----------------|--------------------|"]
        for addr, entry in rows:
            chain_name = (EVM_CHAINS.get(str(entry.get("chain", "8453"))) or {}).get("name", entry.get("chain", "Base"))
            lines.append(f"| {entry.get('symbol', '?')} | {chain_name} | `{entry.get('address', addr)}` | {entry.get('last_score')}/100 | "
                          f"{entry.get('times_investigated', 1)} | {entry.get('last_investigated', '?')} |")
        with open(path, "w") as f:
            f.write("\n".join(lines) + "\n")


def _defillama_intel(address, chain):
    """Best-effort DefiLlama cross-source for a token, or None. Maps VAPE's
    numeric chain id to DefiLlama's chain slug (same slug DexScreener uses,
    already in EVM_CHAINS['dex']). Never raises — a DefiLlama outage or an
    untracked token must never sink an investigation."""
    slug = (EVM_CHAINS.get(str(chain)) or {}).get("dex")
    if not slug:
        return None
    try:
        from agents import defillama as dl
        return dl.token_intel(slug, address)
    except Exception as e:
        print(f"[investigate] defillama intel unavailable: {e}")
        return None


def _coingecko_contract_intel(address, chain):
    """Best-effort CoinGecko contract-address lookup, or None. Real gap this
    closes: score() previously had no way to tell "an anonymous token that
    happens to have a mint function" apart from "a globally recognized,
    fiat-backed stablecoin whose mint/blacklist/admin-key design is the
    DEFINING, expected architecture of its category" — both tripped the
    exact same is_mintable/owner_change_balance/owner-not-renounced flags at
    full weight (confirmed real: USDT scored 45/100 REJECT on exactly this).

    Deliberately verifies the ADDRESS, not just the declared symbol —
    CoinGecko's /coins/{platform}/contract/{address} endpoint only returns
    real market data when this EXACT address is the one it has independently
    listed as that asset. A copycat contract self-declaring symbol "USDT"
    gets either a 404 or its own (different, likely illiquid) CoinGecko
    listing, never Tether's real data — closing the brand-impersonation
    loophole a symbol-only check would have opened. Never raises — a
    CoinGecko outage or an untracked token must never sink an investigation,
    and this is intentionally silent about which of those two happened
    (both mean "no real evidence either way," treated identically by
    _stablecoin_context() below)."""
    platform = COINGECKO_PLATFORM.get(str(chain))
    if not platform:
        return None
    try:
        from agents import data_fetchers as DF
        result = DF.get_token_market_by_contract(address, platform=platform)
        return result if isinstance(result, dict) and not result.get("error") else None
    except Exception as e:
        print(f"[investigate] coingecko contract intel unavailable: {e}")
        return None


# $100M matches agents/defillama.py::stablecoins()'s own quality bar for a
# "real, major" stablecoin (as opposed to a thin/failed stablecoin
# experiment) — one threshold, not two independently-chosen numbers.
STABLECOIN_MIN_MCAP_USD = 1e8
# A stablecoin trading meaningfully off its $1 peg is either already
# depegging (a real, live risk, not a reason to waive anything) or the
# CoinGecko match is wrong for some other reason — either way, not a case
# for the compliance-mechanism exception below.
STABLECOIN_PEG_TOLERANCE = 0.03


def _stablecoin_context(cg_contract):
    """Real, address-verified evidence that this exact contract is a live,
    major, near-$1-pegged asset per CoinGecko's own data — or None if that
    evidence doesn't exist. Never guessed from the token's own declared
    name/symbol (see _coingecko_contract_intel()'s docstring for why that
    matters)."""
    if not isinstance(cg_contract, dict):
        return None
    price = cg_contract.get("price_usd")
    mcap = cg_contract.get("market_cap_usd")
    if not isinstance(price, (int, float)) or not isinstance(mcap, (int, float)):
        return None
    if mcap < STABLECOIN_MIN_MCAP_USD:
        return None
    if abs(price - 1.0) > STABLECOIN_PEG_TOLERANCE:
        return None
    return {"name": cg_contract.get("name"), "symbol": cg_contract.get("symbol"),
            "market_cap_usd": mcap, "price_usd": price}


# Addresses whose held balance is permanently removed from circulation, not
# a whale who can dump — must be excluded from concentration math or a
# healthy burn/deflationary mechanism would score as a whale-risk red flag.
_BURN_ADDRESSES = {
    "0x0000000000000000000000000000000000000000",
    "0x000000000000000000000000000000000000dead",
}


def _holder_concentration(gp):
    """Real top-holder concentration from GoPlus's own per-holder "holders"
    array (percent of supply per address) — a genuine, already-fetched
    signal that used to sit completely unused: every investigation already
    calls goplus_security() and gets this back inside the raw dict, but only
    the scalar holder_count was ever read, never the per-holder breakdown
    that would reveal whether "40k holders" means broad organic distribution
    or a handful of whales plus a long dust tail (flagged directly as a
    missing factor against a live report, investigation-20260725-155143-
    0xB8d7710f.md, where a raw holder count was the ONLY distribution signal
    available). Excludes burn addresses (that supply can never move) and
    addresses GoPlus itself tags as an LP/pool (that's liquidity, not a
    whale). Returns None on any missing/malformed shape — GoPlus's exact
    schema couldn't be verified against a live response from this sandbox
    (network access is blocked here, same as every other external API in
    this repo), so this degrades honestly to "no signal" rather than ever
    guessing wrong. Never raises."""
    holders = gp.get("holders") if isinstance(gp, dict) else None
    if not isinstance(holders, list) or not holders:
        return None
    total_pct = 0.0
    counted = 0
    for h in holders[:10]:
        if not isinstance(h, dict):
            continue
        addr = str(h.get("address") or "").lower()
        if addr in _BURN_ADDRESSES:
            continue
        tag = str(h.get("tag") or "").lower()
        if "lp" in tag or "pool" in tag or "burn" in tag:
            continue
        try:
            pct = float(h.get("percent") or 0)
        except (TypeError, ValueError):
            continue
        # GoPlus reports percent as a 0-1 fraction in this API family (same
        # convention as buy_tax/sell_tax elsewhere in this file); guard
        # against a 0-100 shape too so a schema surprise never inflates
        # 10x instead of silently misreading.
        if pct > 1:
            pct = pct / 100.0
        total_pct += pct
        counted += 1
    if counted == 0:
        return None
    return {"top_holders_pct": total_pct * 100.0, "holders_counted": counted}


def _lp_lock_status(gp):
    """Real liquidity-lock status from GoPlus's own "lp_holders" array
    (is_locked per LP-token holder) — the classic, concrete "can the dev
    just pull liquidity and rug" check, already fetched every cycle via
    goplus_security() and never read. Returns None on any missing/malformed
    shape (see _holder_concentration()'s docstring for why — same
    unverified-live-schema caveat, same honest-degradation rule)."""
    lp_holders = gp.get("lp_holders") if isinstance(gp, dict) else None
    if not isinstance(lp_holders, list) or not lp_holders:
        return None
    total_pct = 0.0
    locked_pct = 0.0
    counted = 0
    for h in lp_holders:
        if not isinstance(h, dict):
            continue
        try:
            pct = float(h.get("percent") or 0)
        except (TypeError, ValueError):
            continue
        if pct > 1:
            pct = pct / 100.0
        total_pct += pct
        if str(h.get("is_locked")) == "1":
            locked_pct += pct
        counted += 1
    if counted == 0 or total_pct <= 0:
        return None
    return {"locked_pct": (locked_pct / total_pct) * 100.0, "lp_holders_counted": counted}


def _data_agent_intel(address, chain):
    """Best-effort recruitment of BOTH DATA AGENT instances (agents/
    data_agent.py, CDP-pinned; agents/data_agent_vapor.py, VAPOR-pinned) to
    each independently try to hire one of VAPE's own x402 market-data
    offerings (up to agents.data_agent.MAX_OFFERING_PRICE_USD each) against
    this token, paid for with the same real, funded wallet
    — the same rail an external buyer uses, just recruited internally. Each
    instance has its own 30m/48-per-day gate, so either, both, or neither may
    actually fire this cycle. Never raises and never blocks the investigation
    on a payment/network failure or a missing key."""
    results = []
    try:
        from agents import data_agent
        results.append(("cdp", data_agent.run_for_investigation(address, chain)))
    except Exception as e:
        print(f"[investigate] data agent (cdp) unavailable: {e}")
    try:
        from agents import data_agent_vapor
        results.append(("vapor", data_agent_vapor.run_for_investigation(address, chain)))
    except Exception as e:
        print(f"[investigate] data agent (vapor) unavailable: {e}")

    if not results:
        return None

    hired = []
    notes = []
    cost_usd = 0.0
    for facilitator, r in results:
        for h in r.get("hired", []):
            hired.append({**h, "facilitator": facilitator})
        if r.get("note"):
            notes.append(f"{facilitator}: {r['note']}")
        cost_usd += r.get("cost_usd", 0)

    out = {"hired": hired, "cost_usd": round(cost_usd, 2)}
    if notes:
        out["note"] = "; ".join(notes)
    return out


def _fmt_data_agent_deliverable(d):
    """Short, generic summary of a market-data deliverable's top-level
    scalar fields — offerings vary wildly in shape (token_intel vs bridges
    vs stablecoins), so this reports whatever real fields came back rather
    than a bespoke per-offering formatter."""
    if not isinstance(d, dict):
        return str(d)
    if d.get("error"):
        return f"error — {d['error']}"
    parts = []
    for k, v in d.items():
        if k in ("logo", "ts", "chain", "address"):
            continue
        if isinstance(v, list):
            parts.append(f"{k}: {len(v)} item(s)")
        elif isinstance(v, dict):
            continue
        elif v is not None:
            parts.append(f"{k}={v}")
        if len(parts) >= 6:
            break
    return "; ".join(parts) if parts else "no notable fields"


def _expert_assessment(target, sym, chain, verdict, s, reasons, positive_signals,
                             gp, dex, onchain, verif, corr, web_rep, defillama,
                             deployer_siblings, data_agent_intel):
    """Real synthesis of everything gathered this cycle — score() already
    produces a deterministic rule-based verdict, but write_report() below
    otherwise just lists each source's raw fields with no reasoning
    connecting them. This gives the frontier model (OCI Grok 4.3 primary,
    via agents/research_engine.py::synthesize() — see below) the same
    evidence a human reviewer would see and has it write an actual
    investigation into what this project/token really is, not a
    restatement of the fields or a rubber-stamp AGREE/DISAGREE tag. Never
    overrides score()'s verdict — same "surface disagreement, never
    mutate" pattern as agents/critic.py's structural self-check; a real
    disagreement here is signal for self_improve.py/review_ledger.py, not
    a verdict change. Never raises.

    Routed through research_engine.synthesize() (not a bare LLM call) since
    that engine now offers the features this function needed to migrate
    onto the shared implementation rather than keep a parallel one:
    `evidence_lines` (a caller-supplied, already-gathered evidence list —
    this function never needed research_engine's own web-search discovery
    layer, since callers upstream already ran GoPlus/DexScreener/on-chain/
    web-reputation checks) and a generic, declarative `trailers` spec
    requesting a VERDICT ALIGNMENT AGREE|DISAGREE trailer after GAPS_JSON —
    this function's anti-injection fix (PR #277) generalized inside
    synthesize() itself rather than hand-rolled here. The underlying
    evidence, grounding rules, and anti-injection parsing are unchanged;
    the picked-up bonus is an explicit gaps/confidence read appended to
    every real investigation.

    Real, previously-live bug this fixes (confirmed 2026-07-25 from a live
    report, investigation-20260725-101257-0xdCf51302.md): this call used to
    pass search=True, which — per agents/llm.py::ask_oci_grok()'s own
    docstring — routes AROUND OCI Grok/Vertex entirely (neither has a
    search-grounding equivalent) into the free FRONTIER_ORDER chain. The
    usage log for that exact report shows it landed on groq's free
    llama-3.3-70b-versatile with a 138-token completion, producing a
    generic "AGREE: ...suggests a level of legitimacy..." paragraph that
    just restated the evidence already listed above it — not a real
    investigation, and not OCI Grok 4.3. The prompt below no longer claims
    a live-search capability the OCI Grok/Vertex primary route doesn't
    have; it leans on the real evidence already gathered (including
    web_rep, itself from a real pre-fetched keyless search elsewhere in
    this pipeline) plus the model's own trained knowledge, clearly marked
    as background when used."""
    try:
        from agents import research_engine
    except Exception:
        return None

    evidence = [f"Target: {sym} ({target}) on chain {chain}",
                f"Rule-based verdict: {verdict} ({s}/100)"]
    if reasons:
        evidence.append("Risk factors: " + "; ".join(reasons))
    if positive_signals:
        evidence.append("Positive signals: " + "; ".join(positive_signals))
    if gp:
        evidence.append(f"Token-safety data: honeypot={gp.get('is_honeypot')}, "
                         f"buy_tax={gp.get('buy_tax')}, sell_tax={gp.get('sell_tax')}, "
                         f"mintable={gp.get('is_mintable')}, proxy={gp.get('is_proxy')}, "
                         f"owner={gp.get('owner_address')}, holders={gp.get('holder_count')}")
    if dex:
        evidence.append(f"Market: {dex.get('symbol')}/{dex.get('name')}, price=${dex.get('price_usd')}, "
                         f"liquidity=${dex.get('liquidity_usd')}, 24h_vol=${dex.get('vol_24h_usd')}, "
                         f"24h_change={dex.get('change_24h_pct')}%, dex={dex.get('dex')}")
    if onchain:
        evidence.append(f"On-chain: is_contract={onchain.get('is_contract')}, "
                         f"code_size={onchain.get('code_size_bytes')}B")
    if verif and verif.get("checked"):
        evidence.append(f"Verification: verified={verif.get('verified')}, name={verif.get('name')}, "
                         f"proxy={verif.get('proxy')}")
    if corr:
        evidence.append("Threat correlation: " + "; ".join(corr))
    if web_rep and web_rep.get("available") and web_rep.get("hits"):
        evidence.append("Web-reputation flags: " + "; ".join(web_rep["hits"]))
    if defillama:
        pr = defillama.get("price") or {}
        fp = defillama.get("first_price") or {}
        if pr or fp:
            evidence.append(f"Market-data aggregator: price=${pr.get('price')}, "
                             f"first_seen={fp.get('first_seen_iso')} ({fp.get('age_days')} days ago)")
    if deployer_siblings:
        evidence.append(f"Deployer has {len(deployer_siblings)} other token(s) on record: "
                         + "; ".join(f"{sib.get('symbol')}={sib.get('verdict')}"
                                     for sib in deployer_siblings[:5]))
    if data_agent_intel and data_agent_intel.get("hired"):
        paid = [h for h in data_agent_intel["hired"] if h["paid"]]
        if paid:
            evidence.append("Data agent bought " + "; ".join(
                f"{h['offering']}={_fmt_data_agent_deliverable(h['deliverable'])}" for h in paid))

    # Rewritten per a direct, concrete critique of a live report: the old
    # instructions asked for detective work but still forced a framing where
    # this section reads as a second opinion "agreeing/disagreeing" with the
    # rule-based verdict above it — two agents seemingly arguing about the
    # same evidence instead of one detective owning the full judgment. This
    # is now told explicitly to BE the primary synthesis (write_report()
    # moves it to the top of the report, right after the header), with the
    # rule-based score/categories as its supporting instrumentation, not a
    # peer to agree or disagree with. The AGREE/DISAGREE trailer request
    # below is UNCHANGED and still real — see this function's own docstring
    # for why (a genuine disagreement is signal for self_improve.py/
    # review_ledger.py) — it's just never allowed to leak into the model's
    # own prose anymore.
    extra_instructions = (
        "You are the lead investigator writing the primary Expert Assessment for this "
        "investigation — the detective's own conclusion, not a second opinion checking someone "
        "else's grade. The rule-based score/category breakdown elsewhere in this report is "
        "supporting instrumentation for what you write here, not a verdict you are agreeing or "
        "disagreeing with. Never frame your response that way, and never use the words "
        "\"agree\"/\"disagree\"/\"the verdict above\" — own the judgment outright.\n\n"
        "Structure your assessment in this order, as tight prose (short paragraphs, no "
        "restating raw fields you're given):\n"
        "1. Bottom-line posture in one clear sentence — your real stance on risk and legitimacy.\n"
        "2. What the evidence actually supports — technical hygiene, ownership/lock quality, "
        "holder distribution, longevity, and any other real positive signals; be specific and "
        "quantitative, not vague.\n"
        "3. Primary residual risks and missing surface, ranked by importance — explicitly call "
        "out thin narrative/social proof, low absolute liquidity, concentration, or missing "
        "team/provenance signals when the evidence shows them, don't let a clean security sweep "
        "alone read as low risk.\n"
        "4. Confidence and what would change the view — state your confidence in the technical "
        "safety read separately from your confidence in the overall investment thesis, and name "
        "the concrete signals that would raise or lower either one.\n"
        "5. Actionable stance — a practical recommendation with size/exposure context (e.g. "
        "\"acceptable only as a small, high-risk speculative position\", \"acceptable for "
        "moderate size if liquidity deepens\", \"avoid until X improves\") and what would trigger "
        "a re-check.\n\n"
        "If you recognize this specific project, token, or deployer from your own training, "
        "bring that background in explicitly — clearly marked as your own prior knowledge, not "
        "something this cycle's evidence itself showed, since it wasn't independently "
        "re-verified this run. Never invent facts, team members, utility, or history not in the "
        "evidence or clearly marked as background knowledge. Never name the specific third-party "
        "API/vendor a piece of evidence came from (e.g. don't write 'according to GoPlus' or "
        "'per DexScreener') — describe it by what it measures instead (token-safety data, "
        "market/liquidity data, etc.). Write in a direct, high-signal, professional style suited "
        "to a real security dossier."
    )
    result = {
        "topic": f"{sym} ({target})", "task_type": "investigation", "known_facts": {},
        "findings": [], "deep_extracts": [], "evidence_lines": evidence, "log": {},
    }
    # research_engine.synthesize() tries OCI-hosted Grok 4.3 first, falling
    # back to VAPE's Vertex-tuned model (if VAPE_VERTEX_ACCESS_TOKEN is set),
    # falling back further to the same frontier tier/order as before — a run
    # with neither configured behaves identically to before this change.
    # search intentionally never enters this path — see this function's own
    # docstring for why passing it would defeat the point of this call.
    # max_tokens raised (750 -> 900) and temperature tightened (0.4 -> 0.35)
    # to give the now-5-part primary synthesis real room without drifting
    # into looser, less evidence-anchored prose.
    synth = research_engine.synthesize(
        result, role="lead investigator", extra_instructions=extra_instructions,
        trailers=[{"type": "json", "name": "gaps", "label": "GAPS_JSON"},
                  {"type": "enum", "name": "verdict", "label": "VERDICT ALIGNMENT",
                   "options": ("AGREE", "DISAGREE")}],
        max_tokens=900, temperature=0.35,
    )
    text = (synth.get("narrative") or "").strip()
    if not text or text.startswith("_Synthesis unavailable"):
        return None
    # Real anti-injection fix this preserves (CodeRabbit, PR #277): the verdict
    # is only ever read from the absolute last line of the response, inside
    # synthesize() itself now — untrusted evidence quoted/echoed earlier in the
    # model's own analysis (or, worse, prompt-injected content) can't hijack it.
    disagrees = synth.get("verdict") == "DISAGREE"
    gaps_section = research_engine.render_gaps_section(synth.get("gaps") or [])
    text = f"{text}\n\n{gaps_section}".strip()
    return {"text": text, "disagrees": disagrees}


def _project_narrative(symbol, name, dex, coingecko_contract, address, chain):
    """Real, grounded synthesis of what this project actually IS — identity,
    utility, traction, history (relaunches/incidents/team changes), and any
    real team/community/social signals — the "Project Overview & Narrative"
    and "Team, Community & Social Signals" template sections the user
    explicitly asked for. Real gap this closes: _expert_assessment() only
    reasons over already-structured evidence (GoPlus/DexScreener/etc.) plus
    the model's own (possibly stale) training knowledge — it never runs a
    fresh, targeted web search for a project's actual current narrative/
    history/team, so a post-training-cutoff relaunch/turnaround (the real
    "Stars Arena -> The Arena" history flagged by the user against a live
    report) is invisible to it.

    Runs its OWN, separate web search (skillforge/research.py's provider
    chain — same Tavily/Brave/quota-capped router as web_reputation_check(),
    but a distinct project-identity-focused query — deliberately not reused
    from the scam-check query, which would pollute both result sets), then
    asks the frontier model (via agents/research_engine.py::synthesize() —
    same route as _expert_assessment()) to synthesize ONLY
    from those real search-snippet results plus already-known declared data
    (CoinGecko description, DexScreener websites/socials) — explicitly told
    to say the search was thin rather than invent a history/team/utility
    claim with no source. Deliberately does NOT escalate to a full-page
    scrape (unlike web_reputation_check(), which only scrapes a hit that
    already cleared a real scam-keyword bar) — this function's search
    always runs, so an unconditional scrape here would roughly double this
    pipeline's per-cycle scrape-quota consumption against
    skillforge/research.py's shared, capped provider pool (CodeRabbit,
    PR #282); the 300-char search snippets already grounding this synthesis
    are proportionate to a narrative section, not a security scrape escalation.

    Real, non-security-graded caveat this function must carry: the search
    query is built from this token's own DECLARED name/symbol, which a
    copycat/impersonation token can set to anything — including a real,
    legitimate project's name (the exact "brand impersonation" pattern this
    codebase already penalizes for stablecoins, see STABLECOIN_BRAND_*
    above). Search results found for that name could therefore describe a
    real but UNRELATED project, not this specific contract (CodeRabbit,
    PR #282). Requiring search results to literally cite the on-chain
    address would make this feature return "unavailable" for nearly every
    real, legitimate project too (ordinary coverage almost never quotes a
    contract address) — so instead, this function checks whether
    `coingecko_contract` is populated (i.e. CoinGecko's own /contract/
    {address} lookup, called with the exact address, independently confirms
    THIS address really is listed under this name/symbol — see
    _coingecko_contract_intel()'s docstring) and both instructs the model to
    caveat unverified identity in its own text AND has the report render an
    explicit, prominent warning banner whenever that address-level
    verification is absent, so a reader is never left assuming the narrative
    below was confirmed to describe this exact contract.

    Search results are untrusted external content, not instructions, framed
    identically to every other web-sourced input this pipeline already
    treats that way. Never raises; returns None on any unavailable search/
    LLM path (same honest-degradation law as every other optional recon
    step here)."""
    try:
        from agents import research_engine
    except Exception:
        return None

    query_name = (name or symbol or "").strip()
    if not query_name:
        return None

    # Real gap this closes (confirmed against a live report,
    # investigation-20260802-203111-0xd7A73942.md): this function used to
    # hard-bail to None the moment the web search itself failed or came back
    # empty, EVEN WHEN the token had a real declared website/Twitter/
    # Telegram (or a CoinGecko-tracked description) sitting right there in
    # already-fetched data — a real, if thinner, narrative was always
    # possible from that alone. Only bail when there's truly nothing to
    # synthesize from at all: no fresh search hits AND no declared presence.
    has_declared_data = bool(
        (dex and (dex.get("websites") or dex.get("socials")))
        or (coingecko_contract and (coingecko_contract.get("description") or coingecko_contract.get("homepage")))
    )

    query = f'"{query_name}" crypto token project what is'
    normalized = []
    try:
        from skillforge.research import search as web_search
        res = web_search(query, max_results=5)
        raw = res.get("raw") if isinstance(res, dict) else None
        results = []
        if isinstance(raw, dict):
            results = raw.get("results") or raw.get("data") or []
        elif isinstance(raw, list):
            results = raw
        if not isinstance(results, list):
            results = []
        if not results and isinstance(res, dict) and res.get("results"):
            results = res["results"]  # keyless fallback shape
        for r in results[:5]:
            if not isinstance(r, dict):
                continue
            title = str(r.get("title") or "")
            snippet = str(r.get("content") or r.get("snippet") or r.get("description") or "")
            url = str(r.get("url") or "")
            if title or snippet:
                normalized.append({"title": title, "url": url, "snippet": snippet[:300]})
    except Exception:
        normalized = []  # search unavailable this cycle -- fall through to declared-data-only below
    if not normalized and not has_declared_data:
        return None

    # True only when CoinGecko's own /contract/{address} lookup — called
    # with THIS EXACT address, never guessed from the declared name/symbol
    # (see _coingecko_contract_intel()'s docstring) — independently confirms
    # this contract really is the project being searched for. False means
    # everything below rests on the token's own self-declared name, which an
    # impersonator can set to any real project's name.
    address_identity_verified = bool(coingecko_contract)

    evidence = [f"Project/token name: {query_name} (${symbol})"]
    evidence.append(
        "Address-level identity verification: "
        + ("CONFIRMED — an independent market-data lookup verified this exact contract address as "
           "this project."
           if address_identity_verified else
           "NOT CONFIRMED — this name/symbol is only self-declared by the token; it has not been "
           "independently verified that this contract is actually affiliated with the project the "
           "search below describes.")
    )
    if coingecko_contract and coingecko_contract.get("description"):
        evidence.append(f"Declared project description: {coingecko_contract['description']}")
    if coingecko_contract and coingecko_contract.get("homepage"):
        evidence.append(f"Declared homepage: {coingecko_contract['homepage']}")
    if dex and dex.get("websites"):
        sites = ", ".join(w.get("url") for w in dex["websites"] if w.get("url"))
        if sites:
            evidence.append(f"Declared website(s): {sites}")
    if dex and dex.get("socials"):
        socials = ", ".join(f"{s.get('type')}: {s.get('url')}" for s in dex["socials"] if s.get("url"))
        if socials:
            evidence.append(f"Declared social(s): {socials}")
    if normalized:
        evidence.append("Real web search results:")
        for r in normalized:
            evidence.append(f"- \"{r['title']}\" ({r['url']}): {r['snippet']}")
    else:
        evidence.append("Real web search results: none this cycle (search unavailable or returned nothing "
                         "relevant) — synthesize from the declared data above only, and say so plainly "
                         "rather than inventing detail to fill the gap.")

    grounding = "=== REAL EVIDENCE THIS CYCLE ===\n" + "\n".join(f"- {e}" for e in evidence)
    synth = research_engine.synthesize(
        {"topic": f"{query_name} project identity", "task_type": "investigation",
         "known_facts": {}, "findings": [], "deep_extracts": [], "raw_user_block": grounding, "log": {}},
        role="due-diligence researcher on project identity, history, and team/community signals",
        extra_instructions=(
            "You are researching what this specific crypto project/token actually IS, for a real "
            "due-diligence report — identity and context, not a security grade (a separate process "
            "already handles security). Write a short, grounded narrative covering: what the "
            "project actually does/its real utility, any real traction (users, volume, notable "
            "integrations) the evidence supports, any history worth flagging (a relaunch, rebrand, "
            "past incident and how it was handled, a team change), and any real, named team/"
            "leadership or community/social signals the search actually surfaced. IMPORTANT: this "
            "search was run against the token's own DECLARED name/symbol, not a verified identity — "
            "if the evidence above says address-level identity verification is NOT CONFIRMED, you "
            "MUST open your narrative by explicitly flagging that this contract's affiliation with "
            "the project described below is unconfirmed and the name could be reused by an "
            "unrelated or impersonating token, before describing what the search found. Never name "
            "the specific third-party data provider behind a piece of already-known declared data "
            "— describe it generically (e.g. 'declared project description', not 'per CoinGecko')."
        ),
        trailers=[], max_tokens=500, temperature=0.4,
    )
    text = (synth.get("narrative") or "").strip()
    if not text or text.startswith("_Synthesis unavailable"):
        return None
    sources = [r["url"] for r in normalized if r["url"]]
    if not sources:
        # No fresh search hit to cite -- fall back to the token's own
        # declared links so a reader still has somewhere real to click,
        # rather than an empty Sources line under a real narrative.
        if dex and dex.get("websites"):
            sources.extend(w["url"] for w in dex["websites"] if w.get("url"))
        if coingecko_contract and coingecko_contract.get("homepage"):
            sources.append(coingecko_contract["homepage"])
    return {"text": text, "sources": sources,
            "address_identity_verified": address_identity_verified}


def _log_expert_disagreement(target, chain, sym, verdict, s, assessment_text):
    """Best-effort: a real verdict disagreement from the expert assessment
    is signal for self_improve.py/review_ledger.py, not just report color —
    log it the same way agents/critic.py logs a structural inconsistency."""
    if not append_to_memory:
        return
    try:
        append_to_memory(
            category="lesson",
            title=f"Expert assessment disagreed with {sym} ({target[:10]}) verdict {verdict} ({s}/100)",
            content=assessment_text[:1800],
            source="agents/investigate.py",
            tags=["expert-assessment", "verdict-disagreement"],
            confidence=0.7,
            metadata={"target": target, "chain": str(chain), "verdict": verdict, "score": s},
        )
    except Exception as e:
        print(f"[investigate] expert-assessment disagreement memory log failed: {e}")


def _deployer_graph_intel(creator_address, address):
    """Best-effort deployer relationship lookup via
    skillforge/memory/graph.py — a real generalization of
    _deployer_repeat_offender() into a full cluster: every OTHER token on
    record from the same deployer, regardless of their individual verdicts.
    Returns (cluster_size, siblings_list); (None, []) when the deployer isn't
    on record, has deployed nothing else, or the graph is unavailable for any
    reason. Never raises — this is enrichment, not a load-bearing check."""
    if not creator_address:
        return None, []
    try:
        from skillforge.memory.graph import sibling_tokens
        siblings = sibling_tokens(address)
        return (len(siblings) if len(siblings) >= 2 else None), siblings
    except Exception as e:
        print(f"[investigate] deployer graph unavailable: {e}")
        return None, []


def investigate(address, chain="8453", hint="", force=False):
    address = address.strip()
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return {"error": f"invalid address: {address}"}

    existing = ledger_entry(address, chain)
    if not force and existing:
        print(f"[investigate] skip {address} — already on record: {existing['last_verdict']} "
              f"{existing['last_score']}/100 on {existing['last_investigated']} "
              f"({existing.get('times_investigated', 1)}x checked). Use --address to force a re-check "
              "(hire / deep-dive exception).")
        return {"target": address, "skipped": "already_investigated",
                "last_verdict": existing["last_verdict"], "last_score": existing["last_score"]}

    print(f"[investigate] target {address} on {(EVM_CHAINS.get(str(chain)) or {}).get('name', chain)} ({hint})")
    gp = goplus_security(address, chain)
    dex = dexscreener(address, chain)
    onchain = onchain_presence(address, chain)
    verif = contract_verification(address, chain)
    corr = hack_correlation(gp)
    prelim_sym = dex.get("symbol") or verif.get("name") or "unknown"
    web_rep = web_reputation_check(prelim_sym, address)
    creator_address = gp.get("creator_address")
    deployer_repeat = _deployer_repeat_offender(creator_address, chain, address)
    dl_intel = _defillama_intel(address, chain)
    cluster_size, siblings = _deployer_graph_intel(creator_address, address)
    data_agent_intel = _data_agent_intel(address, chain)
    cg_contract = _coingecko_contract_intel(address, chain)
    s, verdict, reasons, positive_signals = score(gp, dex, onchain, verif, web_rep, deployer_repeat,
                                                  dl_intel, cluster_size, coingecko_contract=cg_contract)

    # Same-cycle structural self-check (agents/critic.py) — deterministic,
    # never mutates the verdict; only surfaces a real internal inconsistency
    # into Memory + the report the moment it happens.
    critic_result = critic.verify(gp, verif, s, verdict, reasons, positive_signals)
    if not critic_result["ok"]:
        print(f"[investigate] CRITIC FLAGGED {address}: {critic_result['issues']}")
        critic.log_finding(address, chain, prelim_sym, critic_result["issues"])

    expert_assessment = _expert_assessment(address, prelim_sym, chain, verdict, s, reasons,
                                               positive_signals, gp, dex, onchain, verif, corr,
                                               web_rep, dl_intel, siblings, data_agent_intel)
    if expert_assessment and expert_assessment["disagrees"]:
        print(f"[investigate] EXPERT ASSESSMENT DISAGREES with {verdict} verdict for {address}")
        _log_expert_disagreement(address, chain, prelim_sym, verdict, s, expert_assessment["text"])

    project_narrative = _project_narrative(prelim_sym, dex.get("name"), dex, cg_contract, address, chain)

    path, sym, emoji = write_report(address, chain, gp, dex, onchain, verif, corr, s, verdict, reasons,
                                    positive_signals, web_rep, dl_intel, siblings, critic_result,
                                    data_agent_intel, expert_assessment, coingecko_contract=cg_contract,
                                    project_narrative=project_narrative)
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    log_memory(address, sym, verdict, s, reasons, rel, chain)
    update_catalog(address, sym, verdict, s, reasons, rel)
    ledger = _update_ledger(address, sym, verdict, s, rel, chain, creator_address)
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
    chain = args.chain
    if args.address:
        target = args.address
    elif args.auto:
        picked = auto_target()
        if picked:
            target, hint, chain = picked["address"], picked.get("hint", ""), picked.get("chain", args.chain)
        else:
            print("[investigate] no auto target found this cycle"); return
    else:
        ap.print_help(); return

    result = investigate(target, chain, hint, force=bool(args.address))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
