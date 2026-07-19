"""Validates skillforge/memory/security_standards.json's real structure —
VAPE's security-research knowledge base built from docs.hackenproof.com/
education/useful-sources and each linked resource's own verified content.
Schema-only checks (this is committed data, not a code path) so a future
edit that breaks the shape a consumer (e.g. a future audit-prompt builder)
would rely on fails loudly here rather than silently at read time.
"""
import json
import os

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "skillforge", "memory", "security_standards.json")


def _load():
    with open(PATH) as f:
        return json.load(f)


def test_file_is_valid_json_with_expected_schema():
    data = _load()
    assert data["schema"] == "vape.skillforge.knowledge.v1"
    assert "updated" in data
    assert isinstance(data["resources"], list)
    assert len(data["resources"]) > 0


def test_every_resource_has_required_fields():
    required = {"id", "name", "category", "status", "last_verified", "summary"}
    for r in _load()["resources"]:
        missing = required - set(r.keys())
        assert not missing, f"resource {r.get('id')} missing fields: {missing}"


def test_resource_ids_are_unique():
    ids = [r["id"] for r in _load()["resources"]]
    assert len(ids) == len(set(ids))


def test_deprecated_swc_registry_lists_real_successors():
    resources = {r["id"]: r for r in _load()["resources"]}
    swc = resources["swc-registry"]
    assert swc["status"] == "deprecated"
    successor_names = {s["name"] for s in swc["successors"]}
    assert "Smart Contract Security Verification Standard (SCSVS)" in successor_names


def test_scsvs_has_all_14_categories():
    resources = {r["id"]: r for r in _load()["resources"]}
    scsvs_content = resources["scsvs"]["verified_content"]
    assert len(scsvs_content) == 14
    assert scsvs_content[0].startswith("V1:")
    assert scsvs_content[-1].startswith("V14:")


def test_unverified_resource_is_honestly_flagged():
    resources = {r["id"]: r for r in _load()["resources"]}
    vigilseek = resources["vigilseek"]
    assert vigilseek["status"] == "not-independently-verified"
    assert vigilseek["url"] is None
