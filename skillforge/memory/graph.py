"""
VAPE's lightweight on-chain relationship graph.

Built from the real investigation ledger (intel/investigations/ledger.json),
which already records every investigated address's GoPlus-reported
creator_address — no new data collection, no new infrastructure, no new
dependency. Hand-rolled adjacency dicts rather than a graph library: the
query surface this needs (a deployer's other tokens, a token's deployer)
doesn't warrant one, and stdlib-only matches every other module in agents/
and skillforge/memory/ (see data_fetchers.py, defillama.py, retriever.py).

This generalizes agents/investigate.py's existing _deployer_repeat_offender()
(which only checks whether ONE prior verdict from the same deployer was
CAUTION/REJECT) into a full queryable cluster: every token from a given
deployer, worst-verdict-first, regardless of whether any individually
tripped a flag — a mass-token-factory deployer can fly under the old check
until one of its tokens gets unlucky with a verdict. As of this writing the
live ledger already contains a real 7-token cluster from one deployer
address, so this isn't graph-shaped speculation over a hypothetical.

Single edge type for now: DEPLOYED (creator_address -> token address).
"""
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEDGER_PATH = os.path.join(ROOT, "intel", "investigations", "ledger.json")
GRAPH_EXPORT_PATH = os.path.join(ROOT, "data", "relationship-graph.json")

# Worst-first ordering for cluster listings — a REJECT sibling is the most
# actionable thing to surface first, a PROCEED sibling the least.
_VERDICT_RANK = {"REJECT": 0, "CAUTION": 1, "PROCEED": 2}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_ledger(path=None):
    try:
        with open(path or LEDGER_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


class Graph:
    """Minimal directed graph: nodes with attrs, one edge type (DEPLOYED)."""

    def __init__(self):
        self.nodes = {}   # address -> attrs dict
        self._out = {}    # address -> set(successor addresses)
        self._in = {}     # address -> set(predecessor addresses)

    def add_node(self, addr, **attrs):
        self.nodes.setdefault(addr, {}).update({k: v for k, v in attrs.items() if v is not None})
        self._out.setdefault(addr, set())
        self._in.setdefault(addr, set())

    def add_edge(self, u, v):
        self.add_node(u)
        self.add_node(v)
        self._out[u].add(v)
        self._in[v].add(u)

    def successors(self, addr):
        return sorted(self._out.get(addr, ()))

    def predecessors(self, addr):
        return sorted(self._in.get(addr, ()))

    def edges(self):
        return [(u, v) for u, vs in self._out.items() for v in vs]

    def __contains__(self, addr):
        return addr in self.nodes

    @property
    def node_count(self):
        return len(self.nodes)

    @property
    def edge_count(self):
        return sum(len(v) for v in self._out.values())


def build_graph(ledger=None):
    """Build the DEPLOYED graph from the real investigation ledger. Never
    raises — a missing/empty ledger yields an empty (but valid) graph."""
    g = Graph()
    ledger = ledger if ledger is not None else _load_ledger()
    for key, entry in (ledger or {}).items():
        if not isinstance(entry, dict):
            continue
        if ":" in key:
            chain, addr_from_key = key.split(":", 1)
        else:
            chain, addr_from_key = "8453", key
        addr = (entry.get("address") or addr_from_key or "").lower()
        if not addr:
            continue
        g.add_node(addr, role="token", symbol=entry.get("symbol"),
                   verdict=entry.get("last_verdict"), score=entry.get("last_score"),
                   chain=chain, times_investigated=entry.get("times_investigated", 1))
        creator = (entry.get("creator_address") or "").lower()
        if creator and creator != addr:
            if creator not in g.nodes:
                g.add_node(creator, role="deployer")
            g.add_edge(creator, addr)
    return g


def deployer_of(token_address, g=None):
    """The on-record deployer for a token address, or None if unknown."""
    g = g if g is not None else build_graph()
    preds = g.predecessors(token_address.lower())
    return preds[0] if preds else None


def tokens_by_deployer(deployer_address, g=None):
    """Every token on record deployed by this address, worst-verdict-first.
    [] if this address has never deployed anything on record."""
    g = g if g is not None else build_graph()
    tokens = []
    for tok in g.successors(deployer_address.lower()):
        n = g.nodes.get(tok, {})
        tokens.append({"address": tok, "symbol": n.get("symbol"), "verdict": n.get("verdict"),
                       "score": n.get("score"), "chain": n.get("chain")})
    tokens.sort(key=lambda t: _VERDICT_RANK.get(t["verdict"], 1))
    return tokens


def sibling_tokens(token_address, g=None):
    """Every OTHER token on record from the same deployer as `token_address`
    — the direct generalization of _deployer_repeat_offender(). [] if this
    token's deployer is unknown or has deployed nothing else on record."""
    g = g if g is not None else build_graph()
    addr = token_address.lower()
    creator = deployer_of(addr, g)
    if not creator:
        return []
    return [t for t in tokens_by_deployer(creator, g) if t["address"] != addr]


def graph_stats(g=None):
    g = g if g is not None else build_graph()
    # Derived from graph STRUCTURE (has outgoing DEPLOYED edges), not the
    # mutable "role" attribute — a node can be both a token (its own ledger
    # entry) and a deployer (of others). role="token" would silently
    # overwrite an earlier role="deployer" via add_node()'s update(), which
    # previously undercounted such a node here even though
    # tokens_by_deployer()/sibling_tokens() (edge-based already) stayed correct.
    deployers = [n for n in g.nodes if g.successors(n)]
    clusters = {d: len(g.successors(d)) for d in deployers}
    clusters = {k: v for k, v in clusters.items() if v > 1}
    biggest = max(clusters.items(), key=lambda kv: kv[1]) if clusters else None
    return {
        "nodes": g.node_count, "edges": g.edge_count,
        "deployers": len(deployers), "multi_token_deployers": len(clusters),
        "biggest_cluster": {"deployer": biggest[0], "token_count": biggest[1]} if biggest else None,
    }


def export_graph_json(path=None, g=None):
    """Persist a small, inspectable JSON export — same "committed derived
    artifact" pattern as data/reputation.json / data/attack-feed.json, so a
    future dashboard view or ad-hoc query doesn't need to rebuild the graph
    from the ledger itself."""
    g = g if g is not None else build_graph()
    out_path = path or GRAPH_EXPORT_PATH
    nodes = [{"id": n, **d} for n, d in g.nodes.items()]
    edges = [{"from": u, "to": v, "type": "DEPLOYED"} for u, v in g.edges()]
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"generated": _now_iso(), "stats": graph_stats(g),
                    "nodes": nodes, "edges": edges}, f, indent=2)
    return out_path
