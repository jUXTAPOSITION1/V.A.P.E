"""
VAPE Security Sweep — revives the "vape-security-sweep" cron that ran as an
ad hoc Claude Code session (never committed code) for 3 weeks before
silently stopping 2026-07-01 with no trace anywhere in git history — see
intel/reports/security-*.md for the historical reports this restores.

Real data: agents/data_fetchers.get_hack_feed() (DeFiLlama's keyless hacks
feed, already proven elsewhere in this repo) is the backbone — dated
incidents, real $ lost, real chain/technique. THREAT LEVEL is computed
DETERMINISTICALLY from that feed (never LLM-guessed — see intel_common.py's
module docstring). One bounded live web search adds framework-level
context (ERC-8183/ACP-specific news) the hacks feed can't see; the LLM's
only job is synthesizing what these real inputs mean for VAPE's own
operational surface, grounded in the real data passed to it.

Usage: python agents/security_sweep.py
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.data_fetchers import get_hack_feed  # noqa: E402
from agents import intel_common as ic  # noqa: E402
from agents import llm  # noqa: E402

RECENT_DAYS = 7
BIG_HACK_USD_M = 50
BIG_HACK_WINDOW_DAYS = 14

# Feeds docs/assets/attackfeed.js's homepage ticker + "Threat Ledger" section —
# more items than the report table shows (which stays short for readability),
# filtered to a real, dated lookback window rather than an arbitrary count so
# "past 2 months or so" is an honest, reproducible cutoff, not just "however
# many the API happened to return."
ATTACK_FEED_PATH = os.path.join(ic.ROOT, "data", "attack-feed.json")
ATTACK_FEED_LOOKBACK_DAYS = 56  # 8 weeks, exactly
# get_hack_feed() returns the top N most-recent hacks off the full DeFiLlama
# history, newest first — write_attack_feed then slices that down to the
# real 56-day window. 200 is a wide safety margin so a busy 8-week stretch
# never gets truncated before the date filter even runs.
ATTACK_FEED_FETCH_LIMIT = 200

# VAPE doesn't just report these incidents — for ones it can actually verify
# a target for, it runs its own real forensics pipeline against them (see
# attempt_incident_forensics() below). Scoped to Base only (investigate.py's
# real pipeline) and a real, resolved on-chain address only — never a
# fabricated one — so "investigating the attacks" means something checkable.
ATTACK_RESPONSE_STATE_PATH = os.path.join(ic.ROOT, "skillforge", "memory", "attack_response_state.json")
ATTACK_RESPONSE_LOOKBACK_DAYS = 14
_ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")

# VAPE's response to an incident isn't limited to "did I find an address to
# investigate" — it also asks "what class of bug was this, do I already
# check for it, and would my own scoring have caught it." This table is the
# rule-based half of that (VAPE's design law: a verdict is only ever LLM
# text when it's narrating something already decided by real data — see
# intel_common.py). Each `keywords` set is matched against the DeFiLlama
# feed's own `technique` string; `covered_by` cites the real investigate.py
# check that defends against this class, or is None when it's a genuine,
# named gap. Getting a `covered_by` claim wrong would be worse than saying
# nothing, so every one here is a check that actually exists in score()
# (agents/investigate.py) as of this writing — verify there before adding
# a new "covered" entry.
ATTACK_PATTERNS = [
    {
        "id": "access_control", "label": "Access control / compromised admin key",
        "keywords": ("access control", "admin key", "private key", "key compromise",
                     "compromised key", "predictable private key"),
        "prevention": "Multisig + timelock on every privileged function; alert in real time on owner/admin changes.",
        "covered_by": "investigate.py's score() flags an owner able to reclaim ownership or alter balances "
                       "(can_take_back_ownership / owner_change_balance).",
    },
    {
        "id": "proxy_upgrade", "label": "Malicious or unreviewed proxy upgrade",
        "keywords": ("proxy", "upgrad"),
        "prevention": "Timelocked upgrades with a public review window; re-verify the implementation address on every upgrade event.",
        "covered_by": "investigate.py's score() flags upgradeable proxy contracts (is_proxy) for manual review before trust is extended.",
    },
    {
        "id": "honeypot", "label": "Honeypot / restricted sell mechanics",
        "keywords": ("honeypot",),
        "prevention": "Simulate a sell before ever holding a position — reject anything that blocks or excessively taxes exit.",
        "covered_by": "investigate.py's score() runs exactly this GoPlus honeypot simulation before VAPE ever signs off on a target.",
    },
    {
        "id": "oracle_flashloan", "label": "Flashloan-driven price or oracle manipulation",
        "keywords": ("flashloan", "flash loan", "price oracle", "oracle manipulation", "price manipulation"),
        "prevention": "Use TWAP or multi-source oracles; never accept a single-block spot price for collateral or liquidation math.",
        "covered_by": None,
    },
    {
        "id": "reentrancy", "label": "Reentrancy",
        "keywords": ("reentrancy", "re-entrancy", "recursive call"),
        "prevention": "Checks-effects-interactions ordering plus a reentrancy guard on every external call that moves value.",
        "covered_by": None,
    },
    {
        "id": "signature", "label": "Broken or replayable signature verification",
        "keywords": ("signature", "replay"),
        "prevention": "EIP-712 domain separation with a nonce and expiry on every signed authorization; reject cross-chain replays.",
        "covered_by": None,
    },
    {
        "id": "governance", "label": "Malicious governance proposal or vote manipulation",
        "keywords": ("governance", "voting", "proposal"),
        "prevention": "Timelock + quorum thresholds on execution; auto-flag any proposal that grants broad fund/token-transfer rights.",
        "covered_by": None,
    },
    {
        "id": "deposit_proof", "label": "Missing or forged deposit/withdrawal proof validation",
        "keywords": ("proofless", "unchecked proof", "fake proof", "missing validation", "broken proof"),
        "prevention": "Validate every deposit/withdrawal proof on-chain against a trusted root; never trust client-supplied proof data unverified.",
        "covered_by": None,
    },
    {
        "id": "donation_inflation", "label": "First-depositor share-price / donation inflation attack",
        "keywords": ("donation attack", "share inflation", "first depositor"),
        "prevention": "Seed vaults with a minimum initial deposit or use virtual shares to block first-depositor share-price manipulation.",
        "covered_by": None,
    },
    {
        "id": "hook_manipulation", "label": "AMM hook / callback manipulation",
        "keywords": ("hook manipulation", "hook exploit"),
        "prevention": "Audit hook permissions and callback logic separately from core pool math; restrict who can register or upgrade a hook.",
        "covered_by": None,
    },
    {
        "id": "tokenomics_drain", "label": "Malicious tokenomics / reserve- or LP-draining mechanics",
        "keywords": ("burn-from-lp", "reserve poisoning", "deflationary"),
        "prevention": "Treat burn/rebase/deflationary hooks on LP or reserve balances as a hard red flag; simulate supply mechanics before trusting a pool.",
        "covered_by": None,
    },
    {
        "id": "bridge_exploit", "label": "Cross-chain bridge / message-verification exploit",
        "keywords": ("bridge",),
        "prevention": "Require independent verification of cross-chain messages from more than one relayer; avoid single-verifier bridge designs.",
        "covered_by": None,
    },
    {
        "id": "frontend_offchain", "label": "Front-end or off-chain infrastructure compromise",
        "keywords": ("front-end", "frontend", "dns hijack", "phishing"),
        "prevention": "Out of scope for on-chain analysis — the contract itself may be sound; the compromise sits in off-chain infrastructure.",
        "covered_by": None,
        "out_of_scope": True,
    },
]

ATTACK_LESSON_STATE_PATH = os.path.join(ic.ROOT, "skillforge", "memory", "attack_lessons_state.json")
# Same 14-day actionable window as incident forensics — the Threat Ledger
# still shows the full 8 weeks for context, but VAPE only logs a "lesson"
# for genuinely recent incidents, so a first backfill run doesn't dump
# decades of stale history into memory in one shot.
ATTACK_LESSON_LOOKBACK_DAYS = ATTACK_RESPONSE_LOOKBACK_DAYS


def _days_ago(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except Exception:
        return 9999


def compute_threat_level(incidents):
    """Deterministic: HIGH if a big hack landed recently or 3+ hacks this
    week; MEDIUM if any hack this week; else LOW. Real thresholds, not a
    vibe — a reader can recompute this from the table below."""
    recent = [h for h in incidents if _days_ago(h["date"]) <= RECENT_DAYS]
    big_recent = [h for h in incidents
                  if _days_ago(h["date"]) <= BIG_HACK_WINDOW_DAYS and h.get("amount_usd_m", 0) >= BIG_HACK_USD_M]
    if big_recent or len(recent) >= 3:
        return "HIGH", recent, big_recent
    if recent:
        return "MEDIUM", recent, big_recent
    return "LOW", recent, big_recent


def write_attack_feed(incidents, threat, source_report_path, lessons_by_id=None):
    """Real, dated-window slice of the same incident feed the report table
    draws from — powers the homepage ticker and the full Threat Ledger
    section. `source_report` is the exact report this run just wrote, so
    the site can link the feed straight back to its knowledge source.
    `lessons_by_id`, when given, attaches each incident's learn_from_incidents()
    verdict so the Threat Ledger can show what VAPE took away from it."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ATTACK_FEED_LOOKBACK_DAYS)
    recent = []
    for h in incidents:
        try:
            d = datetime.strptime(h["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if d >= cutoff:
            entry = dict(h)
            if lessons_by_id:
                lesson = lessons_by_id.get(f"{h['date']}:{h['name']}")
                if lesson:
                    entry["lesson"] = lesson
            recent.append(entry)
    payload = {
        "generated_at": ic.now_iso(),
        "source_report": os.path.relpath(source_report_path, ic.ROOT).replace(os.sep, "/"),
        "threat_level": threat,
        "lookback_days": ATTACK_FEED_LOOKBACK_DAYS,
        "incidents": recent,
    }
    os.makedirs(os.path.dirname(ATTACK_FEED_PATH), exist_ok=True)
    with open(ATTACK_FEED_PATH, "w") as f:
        json.dump(payload, f, indent=2)
    return len(recent)


def _load_attack_response_state():
    try:
        with open(ATTACK_RESPONSE_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_attack_response_state(state):
    os.makedirs(os.path.dirname(ATTACK_RESPONSE_STATE_PATH), exist_ok=True)
    with open(ATTACK_RESPONSE_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# Words too generic to trust as a name/symbol match on their own — "Lazy
# Summer Protocol" matching any contract whose name merely contains
# "Protocol" would defeat the point of cross-checking at all.
_GENERIC_NAME_WORDS = {
    "protocol", "finance", "labs", "dao", "swap", "network", "chain",
    "token", "coin", "capital", "official", "project", "foundation",
}


def _address_matches_incident(inv, address, incident_name):
    """Real on-chain cross-check that a candidate address is actually THIS
    incident's protocol, not merely some other address that happened to
    appear in the same search result (an attacker wallet, a victim's own
    unrelated token, a different protocol mentioned in the same writeup).
    Address proximity to a keyword in a search snippet is not evidence —
    the address's real, fetched on-chain name/symbol has to genuinely
    reference the incident's protocol name."""
    tokens = [t for t in re.split(r"[^a-z0-9]+", incident_name.lower())
              if len(t) >= 3 and t not in _GENERIC_NAME_WORDS]
    if not tokens:
        return False
    dex = inv.dexscreener(address, chain="8453")
    verif = inv.contract_verification(address, chain="8453")
    candidate_text = " ".join(str(x) for x in (dex.get("name"), dex.get("symbol"), verif.get("name")) if x).lower()
    if not candidate_text:
        return False
    return any(t in candidate_text for t in tokens)


def attempt_incident_forensics(incidents):
    """VAPE doesn't just narrate these incidents, it investigates the ones
    it can verify a real target for: for recent Base-chain hacks not
    already checked, search for the real on-chain address and, if one is
    found AND its real fetched name/symbol actually cross-checks against
    the incident's protocol name (see _address_matches_incident —
    proximity to a keyword in a search result is not enough evidence on
    its own), run investigate.py's actual forensics pipeline against it —
    producing a genuine investigation report, not a summary of someone
    else's. Never fabricates or guesses an address: if search doesn't
    surface one that verifiably matches, the incident is honestly recorded
    as unresolved and skipped. A state file makes this idempotent — each
    real incident is only ever searched once, not re-queried every 6 hours
    forever.
    """
    try:
        from agents import investigate as inv
    except Exception as e:
        print(f"[security_sweep] could not import investigate.py: {e}")
        return []

    state = _load_attack_response_state()
    cutoff = datetime.now(timezone.utc) - timedelta(days=ATTACK_RESPONSE_LOOKBACK_DAYS)
    outcomes = []
    for h in incidents:
        chains = [str(c).lower() for c in (h.get("chains") or [])]
        if "base" not in chains:
            continue
        try:
            d = datetime.strptime(h["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if d < cutoff:
            continue
        incident_id = f"{h['date']}:{h['name']}"
        if incident_id in state:
            continue  # already resolved-or-tried this exact real incident

        search = ic.web_search_snippets(f"{h['name']} exploit contract address Base Basescan", max_results=5)
        address = None
        for r in search.get("results", []):
            for m in _ADDR_RE.finditer(f"{r.get('title', '')} {r.get('snippet', '')}"):
                candidate = m.group(0)
                if _address_matches_incident(inv, candidate, h["name"]):
                    address = candidate
                    break
            if address:
                break

        if not address:
            state[incident_id] = {"checked_at": ic.now_iso(), "resolved": False}
            outcomes.append({"incident": incident_id, "resolved": False})
            continue

        hint = f"post-incident forensics: {h['name']} exploit ({h['date']}, ${h.get('amount_usd_m')}M, {h.get('technique')})"
        try:
            result = inv.investigate(address, chain="8453", hint=hint, force=False)
        except Exception as e:
            print(f"[security_sweep] investigate({address}) failed: {e}")
            state[incident_id] = {"checked_at": ic.now_iso(), "resolved": False, "error": str(e)}
            outcomes.append({"incident": incident_id, "resolved": False})
            continue

        state[incident_id] = {
            "checked_at": ic.now_iso(), "resolved": True, "address": address,
            "verdict": result.get("verdict") or result.get("skipped"),
            "report": result.get("report"),
        }
        outcomes.append({"incident": incident_id, "resolved": True, "address": address})

    _save_attack_response_state(state)
    return outcomes


def _load_attack_lesson_state():
    try:
        with open(ATTACK_LESSON_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_attack_lesson_state(state):
    os.makedirs(os.path.dirname(ATTACK_LESSON_STATE_PATH), exist_ok=True)
    with open(ATTACK_LESSON_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def _classify_technique(technique):
    """Deterministic keyword match against ATTACK_PATTERNS — the only kind
    of "verdict" this classifier is allowed to produce. Returns the first
    matching pattern, or None if nothing matches (an honest 'no lesson
    available' beats forcing a guess)."""
    t = (technique or "").lower()
    for pattern in ATTACK_PATTERNS:
        if any(k in t for k in pattern["keywords"]):
            return pattern
    return None


def learn_from_incidents(incidents):
    """VAPE's response to an incident doesn't stop at reporting or even
    investigating it: every genuinely recent incident (the same 14-day
    window attempt_incident_forensics() uses) whose technique matches a
    known vulnerability class gets a real lesson logged to Memory — the
    class of bug, a concrete prevention measure, and whether investigate.py
    already checks for it (citing a real, named check) or whether this is a
    genuine, admitted coverage gap. For any incident forensics resolved to a
    real Base address, this also backtests VAPE's own scoring model against
    the actual investigate.py verdict on that contract — if VAPE would have
    said PROCEED on something that then got exploited, that's logged as a
    real miss, not smoothed over. Idempotent via its own state file, same
    pattern as attempt_incident_forensics — each incident is only ever
    logged to Memory once.
    """
    try:
        from skillforge.memory.retriever import append_to_memory
    except Exception:
        append_to_memory = None

    response_state = _load_attack_response_state()  # has verdict+address for resolved Base incidents
    lesson_state = _load_attack_lesson_state()
    cutoff = datetime.now(timezone.utc) - timedelta(days=ATTACK_LESSON_LOOKBACK_DAYS)
    lessons_by_id = {}

    for h in incidents:
        try:
            d = datetime.strptime(h["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if d < cutoff:
            continue
        incident_id = f"{h['date']}:{h['name']}"
        pattern = _classify_technique(h.get("technique"))
        resolved = response_state.get(incident_id)
        has_backtest = bool(resolved and resolved.get("resolved")
                             and resolved.get("verdict") in ("PROCEED", "CAUTION", "REJECT"))
        if not pattern and not has_backtest:
            continue  # unclassified technique and no real forensics verdict — nothing to say

        if pattern:
            lesson = {
                "pattern": pattern["id"], "label": pattern["label"],
                "prevention": pattern["prevention"],
                "covered_by": pattern.get("covered_by"),
                "out_of_scope": pattern.get("out_of_scope", False),
            }
        else:
            # A real forensics verdict exists but the technique text didn't match
            # any known category — the backtest result is still real data and
            # shouldn't be discarded just because it can't be labeled.
            lesson = {"pattern": None, "label": "Unclassified technique",
                      "prevention": None, "covered_by": None, "out_of_scope": False}
        if has_backtest:
            lesson["backtest"] = {
                "address": resolved.get("address"),
                "verdict": resolved["verdict"],
                "would_have_flagged": resolved["verdict"] != "PROCEED",
            }
        lessons_by_id[incident_id] = lesson

        if incident_id in lesson_state:
            continue  # already logged this exact real incident to Memory
        if not append_to_memory:
            continue  # Memory unavailable this cycle — retry next run, don't mark as logged

        tags = ["security", "attack-lesson"]
        if pattern:
            if not pattern.get("covered_by") and not pattern.get("out_of_scope"):
                tags.append("coverage-gap")
            content = (f"{h['name']} ({h['date']}, ${h.get('amount_usd_m')}M via {h.get('technique')}) "
                       f"maps to: {pattern['label']}. Prevention: {pattern['prevention']} ")
            if pattern.get("covered_by"):
                content += f"Already covered: {pattern['covered_by']}"
            elif pattern.get("out_of_scope"):
                content += "Out of investigate.py's on-chain scope."
            else:
                content += "Not currently a standalone investigate.py check — a real coverage gap."
        else:
            content = (f"{h['name']} ({h['date']}, ${h.get('amount_usd_m')}M via {h.get('technique')}) "
                       "doesn't match a known attack-pattern category yet, but VAPE resolved a real "
                       "on-chain target and ran its own forensics on it.")
        if lesson.get("backtest"):
            bt = lesson["backtest"]
            content += (f" Backtest: VAPE's own investigate.py verdict on the resolved contract "
                        f"({bt['address']}) was {bt['verdict']} — "
                        + ("would have flagged it." if bt["would_have_flagged"]
                           else "would NOT have flagged it — a real model miss."))
            if not bt["would_have_flagged"]:
                tags.append("backtest-miss")

        try:
            entry = append_to_memory(
                category="finding",
                title=f"Attack lesson: {h['name']} → {lesson['label']}",
                content=content,
                source="agents/security_sweep.py",
                tags=tags,
                confidence=0.85,
                metadata={"incident": incident_id, "pattern": lesson["pattern"],
                          **({"backtest": lesson["backtest"]} if lesson.get("backtest") else {})},
            )
        except Exception as e:
            print(f"[security_sweep] could not log attack lesson: {e}")
            continue
        if entry:
            lesson_state[incident_id] = {"logged_at": ic.now_iso(), "pattern": lesson["pattern"]}

    _save_attack_lesson_state(lesson_state)
    return lessons_by_id


def _render_lessons_section(incidents, lessons_by_id):
    """Pure formatting over already-decided data — no LLM involved, so a
    reader can trust every claim in this section is grounded in either
    ATTACK_PATTERNS' fixed text or a real investigate.py backtest result."""
    if not lessons_by_id:
        return (f"No incidents in the last {ATTACK_LESSON_LOOKBACK_DAYS} days matched a known attack-pattern "
                "category this cycle — nothing new to log.")
    by_id = {f"{h['date']}:{h['name']}": h for h in incidents}
    lines = []
    for incident_id, lesson in lessons_by_id.items():
        h = by_id.get(incident_id, {})
        if lesson.get("prevention"):
            line = (f"- **{h.get('name', incident_id)}** ({h.get('date')}, ${h.get('amount_usd_m')}M) — "
                    f"technique matches **{lesson['label']}**. Prevention: {lesson['prevention']}")
            if lesson.get("covered_by"):
                line += f" *(already covered — {lesson['covered_by']})*"
            elif lesson.get("out_of_scope"):
                line += " *(out of investigate.py's on-chain scope)*"
            else:
                line += " *(not currently a standalone investigate.py check — real coverage gap)*"
        else:
            line = (f"- **{h.get('name', incident_id)}** ({h.get('date')}, ${h.get('amount_usd_m')}M) — "
                    "technique not yet classified, but VAPE resolved a real on-chain target and investigated it.")
        if lesson.get("backtest"):
            bt = lesson["backtest"]
            line += ("\n  Backtest: investigate.py's real verdict on the resolved contract was "
                      f"**{bt['verdict']}** — "
                      + ("would have flagged it." if bt["would_have_flagged"]
                         else "would NOT have flagged it — a real model miss."))
        lines.append(line)
    return "\n".join(lines)


def run():
    feed = get_hack_feed(limit=ATTACK_FEED_FETCH_LIMIT)
    incidents = feed.get("incidents", []) if isinstance(feed, dict) else []
    threat, recent, big_recent = compute_threat_level(incidents)

    search = ic.web_search_snippets("ERC-8183 ACP agent commerce protocol exploit vulnerability 2026", max_results=5)

    # Report table stays short for readability even though `incidents` now
    # holds up to ATTACK_FEED_FETCH_LIMIT entries (the ticker/Threat Ledger
    # want more history than a markdown table should show inline).
    table_rows = "\n".join(
        f"| {h['date']} | {h['name']} | ${h['amount_usd_m']}M | {h.get('technique') or '—'} | {', '.join(h.get('chains') or []) or '—'} |"
        for h in incidents[:15]
    ) or "| — | no incidents in feed this cycle | — | — | — |"

    system = (
        "You are VAPE, an autonomous on-chain security analyst. Write the analysis sections "
        "of a security sweep report using ONLY the real data provided — never invent dollar "
        "amounts, dates, or incidents beyond what's given. If the data is thin, say so plainly "
        "rather than padding with generic security advice. Focus specifically on how these real "
        "incidents relate to VAPE's own operational surface: Base chain, ERC-8183/ACP job "
        "escrow contracts, and AI-agent-operated wallets."
    )
    user = (
        f"THREAT LEVEL (already computed from real data, do not change it): {threat}\n"
        f"Incidents in the last {RECENT_DAYS} days: {len(recent)}\n"
        f"Incidents >= ${BIG_HACK_USD_M}M in the last {BIG_HACK_WINDOW_DAYS} days: {len(big_recent)}\n\n"
        f"Full incident feed (real, from DeFiLlama):\n{table_rows}\n\n"
        f"Web search results on ERC-8183/ACP-specific security news:\n"
        f"{[r['title'] + ': ' + r['snippet'] for r in search.get('results', [])] or 'none available'}\n\n"
        "Write three sections in markdown, each starting with '### ':\n"
        "1. Summary — 3-5 sentences on the current threat landscape from the real incidents above.\n"
        "2. VAPE Impact Assessment — how these specific incidents/techniques relate to ERC-8183 "
        "escrow, ACP agent wallets, and Base-deployed contracts. Say plainly if there's no direct relevance.\n"
        "3. Recommendations — 3-5 concrete, specific action items, grounded in the real incidents above."
    )
    narrative, provider = llm.ask_safe(system, user, tier="deep", max_tokens=1400)

    # Investigate and learn BEFORE the report body is assembled, so the
    # "Lessons Learned" section reflects this exact cycle's real forensics
    # and backtest results rather than being bolted on after the fact.
    forensics = attempt_incident_forensics(incidents)
    lessons_by_id = learn_from_incidents(incidents)
    lessons_section = _render_lessons_section(incidents, lessons_by_id)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    threat_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}[threat]
    body = f"""# VAPE Security Sweep Report

**Generated:** {stamp}
**Trigger:** `agents/security_sweep.py` (scheduled, GitHub Actions)

---

## THREAT LEVEL: {threat_emoji} {threat}

Computed deterministically: {len(recent)} incident(s) in the last {RECENT_DAYS} days across the
tracked feed, {len(big_recent)} of which exceeded ${BIG_HACK_USD_M}M within the last {BIG_HACK_WINDOW_DAYS} days.

---

## Recent DeFi/Crypto Incidents (real, DeFiLlama hacks feed)

| Date | Protocol | Amount Lost | Technique | Chain(s) |
|------|----------|-------------|-----------|----------|
{table_rows}

---

{narrative}

---

## Lessons Learned ({ATTACK_LESSON_LOOKBACK_DAYS}-day window, rule-based classification)

{lessons_section}

---

{ic.format_search_section("Web Signals — ERC-8183 / ACP", search)}

---

## Sources
- DeFiLlama hacks feed (`api.llama.fi/hacks`) — keyless, real-time
- Live web search ({search.get('provider') or 'unavailable'})
- LLM synthesis: {provider or 'unavailable this cycle'}

---

*Report generated by `agents/security_sweep.py` — revived {datetime.now(timezone.utc).strftime('%Y-%m-%d')} after the
original ad hoc sweep silently stopped; see intel/reports/security-2026-07-01-20.md for the last
pre-revival report.*
"""
    path = ic.write_report("security", body)
    summary = f"Security sweep: {threat} — {len(recent)} incident(s) in last {RECENT_DAYS}d, {len(big_recent)} >= ${BIG_HACK_USD_M}M."
    ic.log_sweep_memory("agents/security_sweep.py", threat, summary, path, tags=["security"])

    feed_count = write_attack_feed(incidents, threat, path, lessons_by_id=lessons_by_id)
    resolved = [o for o in forensics if o["resolved"]]
    if forensics:
        print(f"[security_sweep] incident forensics: {len(resolved)}/{len(forensics)} new Base incident(s) "
              f"resolved to a real address and investigated")

    print(f"[security_sweep] {threat} — wrote {os.path.relpath(path, ic.ROOT)}, "
          f"{feed_count} incident(s) in attack feed, {len(lessons_by_id)} lesson(s) matched")
    return {"threat": threat, "path": path, "feed_count": feed_count, "forensics": forensics,
            "lessons": len(lessons_by_id)}


if __name__ == "__main__":
    run()
