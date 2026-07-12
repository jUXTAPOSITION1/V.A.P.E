"""Tests for skillforge/memory/graph.py — the deployer/token relationship
graph built from agents/investigate.py's real ledger schema.

Every test builds the graph from a hand-built synthetic ledger dict (never
the live intel/investigations/ledger.json) so these stay deterministic
regardless of what VAPE has actually investigated by the time CI runs.
"""
from skillforge.memory import graph as g


def _ledger(*entries):
    """Build a ledger dict keyed the same way agents/investigate.py's real
    ledger is (bare address, or "chain:address" for multi-chain entries)."""
    out = {}
    for e in entries:
        key = f"{e.get('_chain', '8453')}:{e['address']}" if e.get("_chain_prefixed") else e["address"]
        out[key] = {k: v for k, v in e.items() if not k.startswith("_")}
    return out


def test_empty_ledger_yields_empty_graph():
    graph = g.build_graph({})
    assert graph.node_count == 0 and graph.edge_count == 0
    assert g.graph_stats(graph)["nodes"] == 0


def test_missing_ledger_file_degrades_to_empty_graph(monkeypatch, tmp_path):
    monkeypatch.setattr(g, "LEDGER_PATH", str(tmp_path / "does-not-exist.json"))
    graph = g.build_graph()  # None -> loads from (missing) LEDGER_PATH
    assert graph.node_count == 0


def test_single_deployer_single_token():
    ledger = _ledger({"address": "0xaaa0000000000000000000000000000000000a",
                      "creator_address": "0xdeployer000000000000000000000000000001",
                      "symbol": "ONE", "last_verdict": "PROCEED", "last_score": 90})
    graph = g.build_graph(ledger)
    deployer = "0xdeployer000000000000000000000000000001"
    token = "0xaaa0000000000000000000000000000000000a"
    assert g.deployer_of(token, graph) == deployer
    assert g.tokens_by_deployer(deployer, graph) == [
        {"address": token, "symbol": "ONE", "verdict": "PROCEED", "score": 90, "chain": "8453"}
    ]
    # No other token from this deployer -> no siblings for the one token itself.
    assert g.sibling_tokens(token, graph) == []


def test_real_shaped_cluster_worst_verdict_first():
    """Mirrors the actual pattern this module was built to generalize: one
    deployer, several tokens, mixed verdicts — must rank REJECT before
    CAUTION before PROCEED."""
    deployer = "0xdeployer000000000000000000000000000002"
    ledger = _ledger(
        {"address": "0xbbb0000000000000000000000000000000000b", "creator_address": deployer,
         "symbol": "GOOD", "last_verdict": "PROCEED", "last_score": 85},
        {"address": "0xccc0000000000000000000000000000000000c", "creator_address": deployer,
         "symbol": "BAD", "last_verdict": "REJECT", "last_score": 10},
        {"address": "0xddd0000000000000000000000000000000000d", "creator_address": deployer,
         "symbol": "MEH", "last_verdict": "CAUTION", "last_score": 55},
    )
    graph = g.build_graph(ledger)
    tokens = g.tokens_by_deployer(deployer, graph)
    assert [t["verdict"] for t in tokens] == ["REJECT", "CAUTION", "PROCEED"]

    # Siblings of the PROCEED token exclude itself and include the other two.
    sibs = g.sibling_tokens("0xbbb0000000000000000000000000000000000b", graph)
    assert {t["address"] for t in sibs} == {
        "0xccc0000000000000000000000000000000000c",
        "0xddd0000000000000000000000000000000000d",
    }

    stats = g.graph_stats(graph)
    assert stats["multi_token_deployers"] == 1
    assert stats["biggest_cluster"] == {"deployer": deployer, "token_count": 3}


def test_unrelated_deployers_dont_cross_contaminate():
    ledger = _ledger(
        {"address": "0xeee0000000000000000000000000000000000e", "creator_address": "0xdeployerA00000000000000000000000000001",
         "symbol": "A1", "last_verdict": "PROCEED", "last_score": 80},
        {"address": "0xfff0000000000000000000000000000000000f", "creator_address": "0xdeployerB00000000000000000000000000002",
         "symbol": "B1", "last_verdict": "PROCEED", "last_score": 80},
    )
    graph = g.build_graph(ledger)
    assert g.sibling_tokens("0xeee0000000000000000000000000000000000e", graph) == []
    assert g.sibling_tokens("0xfff0000000000000000000000000000000000f", graph) == []
    assert g.graph_stats(graph)["multi_token_deployers"] == 0


def test_token_with_no_creator_address_is_isolated():
    ledger = _ledger({"address": "0x1110000000000000000000000000000000001",
                      "symbol": "ORPHAN", "last_verdict": "PROCEED", "last_score": 80})
    graph = g.build_graph(ledger)
    assert g.deployer_of("0x1110000000000000000000000000000000001", graph) is None
    assert g.sibling_tokens("0x1110000000000000000000000000000000001", graph) == []


def test_chain_prefixed_keys_parse_chain_correctly():
    ledger = {
        "10:0x2220000000000000000000000000000000002": {
            "address": "0x2220000000000000000000000000000000002",
            "creator_address": "0xdeployerC00000000000000000000000000003",
            "symbol": "OPTOK", "last_verdict": "PROCEED", "last_score": 80,
        }
    }
    graph = g.build_graph(ledger)
    node = graph.nodes["0x2220000000000000000000000000000000002"]
    assert node["chain"] == "10"


def test_unknown_address_returns_empty_not_error():
    graph = g.build_graph({})
    assert g.deployer_of("0xnotintheledger00000000000000000000000", graph) is None
    assert g.tokens_by_deployer("0xnotintheledger00000000000000000000000", graph) == []
    assert g.sibling_tokens("0xnotintheledger00000000000000000000000", graph) == []


def test_export_graph_json_writes_real_file(tmp_path):
    ledger = _ledger({"address": "0x3330000000000000000000000000000000003",
                      "creator_address": "0xdeployerD00000000000000000000000000004",
                      "symbol": "EXP", "last_verdict": "PROCEED", "last_score": 80})
    graph = g.build_graph(ledger)
    out = tmp_path / "graph.json"
    path = g.export_graph_json(str(out), graph)
    assert path == str(out) and out.exists()
    import json
    data = json.loads(out.read_text())
    assert data["stats"]["nodes"] == 2  # token + deployer
    assert len(data["edges"]) == 1
    assert data["edges"][0]["type"] == "DEPLOYED"
