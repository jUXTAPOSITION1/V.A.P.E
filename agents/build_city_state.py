#!/usr/bin/env python3
"""
VAPE City State Builder — zero-LLM, zero-network, pure aggregation.

Mirrors agents/build_security_dashboard.py's pattern (pure re-projection of
real, already-produced artifacts, no LLM call, no API call, fully-
regenerated output every run) one level further: it reads five snapshots
this repo already maintains and re-projects them into one building manifest
for the site's interactive city visualization (docs/assets/cityscape.js) —

  data/security-dashboard.json           -- 10 automated security lanes
  data/attack-feed.json                  -- on-chain attack/incident intel
  data/intel-index.json                  -- investigations, news, tools
  intel/bounty-radar/opportunities.json  -- bounty-radar tracked programs
  data/reputation.json                   -- verifiable self-build activity

into data/city-state.json: 10 uniform "lane checkpoint" buildings (one per
real security lane, deliberately equal-sized — mirrors securitydashboard.js's
signal-ring principle that position/color/status carry meaning while size
never does, since there's no honest per-lane volume to compare) plus 7
"landmark" buildings sized by real relative volume against each other.

Every number here traces to one of the five files above. A source that
can't be read degrades to nulls/zeros for its own landmark, never a
fabricated placeholder — same rule as every other aggregator in this repo.
"""
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SECDASH_PATH = os.path.join(ROOT, "data", "security-dashboard.json")
ATTACK_FEED_PATH = os.path.join(ROOT, "data", "attack-feed.json")
INTEL_INDEX_PATH = os.path.join(ROOT, "data", "intel-index.json")
OPPORTUNITIES_PATH = os.path.join(ROOT, "intel", "bounty-radar", "opportunities.json")
REPUTATION_PATH = os.path.join(ROOT, "data", "reputation.json")
OUT_PATH = os.path.join(ROOT, "data", "city-state.json")

LIVE_STATUSES = {"live", "active"}

# Hand-laid grid position/footprint per building id — pure presentation
# (roads/layout are city infrastructure, not a data claim), kept here rather
# than in docs/assets/cityscape.js so a future renderer (the walkable 3D
# version this is deliberately laying groundwork for) can read positions
# straight from this same data file instead of a JS-only layout table.
LAYOUT = {
    "mint-x402": {"gridX": 12, "gridY": 0, "footprint": [1, 1]},
    "precinct-investigations": {"gridX": 0, "gridY": 2, "footprint": [2, 2]},
    "tower-bounty": {"gridX": 20, "gridY": 2, "footprint": [2, 2]},
    "foundry": {"gridX": 10, "gridY": 7, "footprint": [3, 3]},
    "newsroom": {"gridX": 0, "gridY": 13, "footprint": [2, 2]},
    "watchtower-threat": {"gridX": 20, "gridY": 13, "footprint": [2, 2]},
    "vault-ledger": {"gridX": 12, "gridY": 17, "footprint": [1, 1]},
}
# 10 lane-checkpoint slots ringed around the Foundry (center ~11.5,8.5) at a
# wider radius than the landmarks sit at -- hand-placed (not trig-computed
# at runtime) so positions stay stable and collision-free against the
# landmarks above regardless of lane order. Spread out from the original
# tightly-packed ring so real roads read as an actual street grid with
# proper block spacing instead of everything crowding one hub tile.
LANE_RING = [
    (8, 4), (11, 3), (14, 4), (17, 6), (17, 10),
    (14, 13), (11, 14), (8, 13), (5, 10), (5, 6),
]


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default if default is not None else {}


def lane_status(lane):
    """Mirrors securitydashboard.js's _laneStatus(): 'ok' on a successful
    last run, 'alert' on any other real conclusion, 'unknown' when no run
    has ever been observed. Every building kind in this file shares this
    same 3-state (+ 'warn') vocabulary so cityscape.js needs exactly one
    status->color mapping regardless of building kind."""
    conclusion = lane.get("last_run_conclusion")
    if conclusion is None:
        return "unknown"
    return "ok" if conclusion == "success" else "alert"


def build_lane_checkpoints(lanes):
    """One uniform-size checkpoint building per real lane. LANE_RING has
    exactly 10 hand-placed, collision-free slots -- as many as this repo's
    real security lanes currently number. A lane beyond that is skipped
    (with a warning) rather than silently wrapping via modulo, which would
    draw two checkpoints on top of each other."""
    checkpoints = []
    for i, lane in enumerate(lanes):
        if i >= len(LANE_RING):
            print(f"warning: lane {lane.get('id')!r} exceeds LANE_RING capacity ({len(LANE_RING)}), skipping", file=sys.stderr)
            continue
        pos = LANE_RING[i]
        checkpoints.append({
            "id": f"lane-{lane.get('id')}",
            "kind": "checkpoint",
            "title": lane.get("label") or lane.get("id"),
            "status": lane_status(lane),
            "tier": 1,
            "gridX": pos[0],
            "gridY": pos[1],
            "footprint": [1, 1],
            "stat_primary": {"label": "last run", "value": lane.get("headline")},
            "last_run_at": lane.get("last_run_at"),
            "source_workflow": lane.get("source_workflow"),
            "link": "index.html#security-dashboard",
        })
    return checkpoints


def tier_for(value, all_values):
    """Relative 1-4 density tier from real magnitude vs. the other landmark
    buildings in this same snapshot — never an absolute/fabricated scale.
    A non-positive or incomparable value always reports the lowest tier
    rather than an artificially inflated one."""
    positives = sorted(v for v in all_values if isinstance(v, (int, float)) and v > 0)
    if not positives or not isinstance(value, (int, float)) or value <= 0:
        return 1
    rank = sum(1 for v in positives if v <= value) / len(positives)
    if rank >= 0.9:
        return 4
    if rank >= 0.6:
        return 3
    if rank >= 0.3:
        return 2
    return 1


def build_landmarks(secdash, attack_feed, intel_index, opportunities, reputation):
    investigations = intel_index.get("investigations") or []
    news = intel_index.get("news") or []
    verdict_counts = {"REJECT": 0, "CAUTION": 0, "PROCEED": 0}
    for inv in investigations:
        v = str(inv.get("verdict") or "").upper()
        if v in verdict_counts:
            verdict_counts[v] += 1

    opp_list = opportunities if isinstance(opportunities, list) else []
    live_count = sum(1 for o in opp_list if str(o.get("status") or "").lower() in LIVE_STATUSES)
    platforms = {o.get("platform") for o in opp_list if o.get("platform")}

    incidents = attack_feed.get("incidents") or []
    threat_level = attack_feed.get("threat_level")

    verifiable_activity = (reputation or {}).get("verifiable_activity") or {}
    tools_built = verifiable_activity.get("tools_built")
    tools_total = verifiable_activity.get("tools_total")

    ledger = secdash.get("ledger_integrity") or {}
    findings_total = sum((secdash.get("findings_by_severity") or {}).values())

    volumes = {
        "precinct-investigations": len(investigations),
        "tower-bounty": len(opp_list),
        "newsroom": len(news),
        "watchtower-threat": len(incidents),
        "foundry": tools_built or 0,
        "vault-ledger": findings_total,
    }
    all_volumes = list(volumes.values())

    threat_status = (
        "alert" if threat_level == "HIGH" else
        "warn" if threat_level == "MEDIUM" else
        "ok" if threat_level == "LOW" else
        "unknown"
    )
    chain_intact = ledger.get("chain_intact")
    vault_status = "ok" if chain_intact else "alert" if chain_intact is False else "unknown"

    return [
        {
            "id": "precinct-investigations", "kind": "precinct",
            "title": "Investigations Precinct", "status": "ok",
            "tier": tier_for(volumes["precinct-investigations"], all_volumes),
            "stat_primary": {"label": "tracked", "value": len(investigations)},
            "stat_secondary": [
                {"label": "reject", "value": verdict_counts["REJECT"]},
                {"label": "caution", "value": verdict_counts["CAUTION"]},
                {"label": "proceed", "value": verdict_counts["PROCEED"]},
            ],
            "link": "investigations.html",
        },
        {
            "id": "tower-bounty", "kind": "tower",
            "title": "Bounty Ops Tower", "status": "ok",
            "tier": tier_for(volumes["tower-bounty"], all_volumes),
            "stat_primary": {"label": "tracked", "value": len(opp_list)},
            "stat_secondary": [
                {"label": "live", "value": live_count},
                {"label": "platforms", "value": len(platforms)},
            ],
            "link": "bounty.html",
        },
        {
            "id": "newsroom", "kind": "newsroom",
            "title": "Newsroom", "status": "ok",
            "tier": tier_for(volumes["newsroom"], all_volumes),
            "stat_primary": {"label": "published", "value": len(news)},
            "stat_secondary": [],
            "link": "news.html",
        },
        {
            "id": "watchtower-threat", "kind": "watchtower",
            "title": "Watchtower", "status": threat_status,
            "tier": tier_for(volumes["watchtower-threat"], all_volumes),
            "stat_primary": {"label": "incidents (56d)", "value": len(incidents)},
            "stat_secondary": [{"label": "threat level", "value": threat_level}],
            "link": "bounty.html#threat-ledger",
        },
        {
            # No repo-committed snapshot backs this one — the worker settles
            # x402 jobs live, sub-minute, so its real numbers only exist
            # client-side (docs/assets/x402feed.js's own /x402/stats fetch).
            # cityscape.js fills stat_primary in at runtime; this entry only
            # carries this building's fixed position/link.
            "id": "mint-x402", "kind": "mint",
            "title": "The Mint", "status": "unknown", "tier": 2,
            "stat_primary": None, "stat_secondary": [], "live_only": True,
            "link": "index.html#x402-ledger",
        },
        {
            "id": "foundry", "kind": "foundry",
            "title": "The Foundry", "status": "ok",
            "tier": tier_for(volumes["foundry"], all_volumes),
            "stat_primary": {"label": "self-built tools", "value": tools_built},
            "stat_secondary": [{"label": "verified tools", "value": tools_total}],
            "link": "index.html#the-workshop",
        },
        {
            "id": "vault-ledger", "kind": "vault",
            "title": "The Vault", "status": vault_status,
            "tier": tier_for(volumes["vault-ledger"], all_volumes),
            "stat_primary": {"label": "findings sealed", "value": findings_total},
            "stat_secondary": [{"label": "unsealed lines", "value": ledger.get("unsealed_lines")}],
            "link": "index.html#security-dashboard",
        },
    ]


def build_recent_events(intel_index, opportunities, attack_feed, limit=24):
    """Every VAPE process that already has its own live-updating building
    also throws off individually-timestamped real events -- surfaced here so
    cityscape.js can spawn one distinct "dispatch vehicle" per genuinely new
    real event (an investigation closing, an article publishing, a bounty
    lead appearing, an incident logged), the same honest-data discipline as
    the live x402 delivery trucks, just covering four more real signals
    instead of one. Purely a re-projection of fields these four files
    already carry -- no new signal, no LLM, no network call."""
    events = []
    for inv in intel_index.get("investigations") or []:
        ts = inv.get("date")
        if not ts:
            continue
        events.append({
            "id": f"investigation:{inv.get('target') or inv.get('title') or ts}",
            "type": "investigation",
            "timestamp": ts,
            "label": inv.get("name") or inv.get("target") or inv.get("title") or "Investigation",
            "verdict": inv.get("verdict"),
        })
    for a in intel_index.get("news") or []:
        ts = a.get("date")
        if not ts:
            continue
        events.append({
            "id": f"news:{a.get('title') or ts}",
            "type": "news",
            "timestamp": ts,
            "label": a.get("title") or "Dispatch",
        })
    for o in (opportunities if isinstance(opportunities, list) else []):
        ts = o.get("firstSeen")
        if not ts:
            continue
        events.append({
            "id": f"bounty:{o.get('id') or o.get('name') or ts}",
            "type": "bounty",
            "timestamp": ts,
            "label": o.get("name") or o.get("platform") or "Bounty lead",
        })
    for inc in attack_feed.get("incidents") or []:
        ts = inc.get("date")
        if not ts:
            continue
        events.append({
            "id": f"threat:{inc.get('name') or ts}",
            "type": "threat",
            "timestamp": ts,
            "label": inc.get("name") or "Incident",
            "amount_usd_m": inc.get("amount_usd_m"),
        })

    def _parse(ts):
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    events.sort(key=lambda e: _parse(e["timestamp"]), reverse=True)
    return events[:limit]


def build_roads(landmark_ids, lane_ids):
    """The Foundry as connective hub, per the explicit design brief: every
    other landmark and every lane checkpoint gets one spoke road running
    through it. Purely structural (which building sits near which road),
    not a data claim."""
    others = [lid for lid in landmark_ids if lid != "foundry"]
    return [["foundry", lid] for lid in others] + [["foundry", lid] for lid in lane_ids]


def build():
    secdash = _read_json(SECDASH_PATH)
    attack_feed = _read_json(ATTACK_FEED_PATH)
    intel_index = _read_json(INTEL_INDEX_PATH)
    opportunities = _read_json(OPPORTUNITIES_PATH, default=[])
    reputation = _read_json(REPUTATION_PATH)

    lanes = secdash.get("lanes") or []
    checkpoints = build_lane_checkpoints(lanes)
    landmarks = build_landmarks(secdash, attack_feed, intel_index, opportunities, reputation)

    for b in landmarks:
        pos = LAYOUT.get(b["id"], {"gridX": 0, "gridY": 0, "footprint": [1, 1]})
        b.update(pos)

    known = [lane for lane in lanes if lane.get("last_run_conclusion") is not None]
    lanes_passing = sum(1 for lane in known if lane.get("last_run_conclusion") == "success")

    city = {
        "generated_at": now_iso(),
        "district_stats": {
            "overall_threat_level": attack_feed.get("threat_level"),
            "lanes_passing": lanes_passing,
            "lanes_total": len(lanes),
            "buildings_total": len(landmarks) + len(checkpoints),
        },
        "buildings": landmarks + checkpoints,
        "roads": build_roads([b["id"] for b in landmarks], [c["id"] for c in checkpoints]),
        "recent_events": build_recent_events(intel_index, opportunities, attack_feed),
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(city, f, indent=2)

    print(json.dumps({
        "wrote": os.path.relpath(OUT_PATH, ROOT),
        "buildings": len(city["buildings"]),
        "roads": len(city["roads"]),
        "district_stats": city["district_stats"],
    }, indent=2))
    return city


if __name__ == "__main__":
    build()
