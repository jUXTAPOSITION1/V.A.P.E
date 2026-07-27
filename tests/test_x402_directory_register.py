"""Tests for agents/x402_directory_register.py's duplicate-listing-avoidance
logic (2026-07-25): register_402index() must skip any offering already
recorded in STATE_PATH, since 402index.io's /register endpoint has
undocumented dedup behavior and re-sending an already-listed offering risks
creating a duplicate. Hermetic: _post (the real network call) and
STATE_PATH are always mocked/redirected to a tmp file, no real network call.
"""
import json
from unittest import mock

from agents import x402_directory_register as reg


def _fake_post_ok(url, payload, **kwargs):
    return 201, {"id": "fake", "status": "pending review"}


def test_all_offerings_count_matches_worker_routes():
    names = [n for n, _meta, _prefix in reg._all_offerings()]
    assert len(names) == len(set(names)), "no duplicate offering names across tiers"
    assert "exploit_check" in names
    assert "dossier_check" in names
    assert "bounty_deep_dive" in names
    assert "token_intel" in names


def test_load_state_defaults_to_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "nope.json"))
    state = reg._load_state()
    assert state == {"registered_402index": []}


def test_save_then_load_state_roundtrip(tmp_path, monkeypatch):
    path = str(tmp_path / "state.json")
    monkeypatch.setattr(reg, "STATE_PATH", path)
    reg._save_state({"registered_402index": ["exploit_check"]})
    assert reg._load_state()["registered_402index"] == ["exploit_check"]


def test_register_402index_skips_already_registered(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    reg._save_state({"registered_402index": ["exploit_check", "token_safety_check"]})
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok) as m_post, \
         mock.patch.object(reg, "time") as m_time:
        results = reg.register_402index(only={"exploit_check", "dossier_check"})
    # Only dossier_check should actually be POSTed — exploit_check is
    # already-registered and skipped even though it's in `only`.
    posted_names = [c.args[1]["name"] for c in m_post.call_args_list]
    assert posted_names == ["VAPE dossier_check"]
    assert len(results) == 1
    assert results[0]["offering"] == "dossier_check"
    assert results[0]["ok"] is True


def test_register_402index_force_all_resends_everything_in_only(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    reg._save_state({"registered_402index": ["exploit_check"]})
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok) as m_post, \
         mock.patch.object(reg, "time"):
        results = reg.register_402index(only={"exploit_check"}, force_all=True)
    assert len(results) == 1
    assert m_post.call_count == 1


def test_register_402index_records_new_successes_in_state(tmp_path, monkeypatch):
    state_path = tmp_path / "state.json"
    monkeypatch.setattr(reg, "STATE_PATH", str(state_path))
    reg._save_state({"registered_402index": ["exploit_check"]})
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok), \
         mock.patch.object(reg, "time"):
        reg.register_402index(only={"dossier_check", "tx_decode"})
    saved = json.loads(state_path.read_text())
    assert set(saved["registered_402index"]) == {"exploit_check", "dossier_check", "tx_decode"}


def test_register_402index_does_not_record_failed_attempts(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    with mock.patch.object(reg, "_post", return_value=(500, {"error": "boom"})), \
         mock.patch.object(reg, "time"):
        results = reg.register_402index(only={"dossier_check"})
    assert results[0]["ok"] is False
    assert reg._load_state()["registered_402index"] == []


def test_ratelimit_headers_picks_only_rate_limit_fields():
    """_ratelimit_headers() exists so a 429 log tells us *when* the quota
    resets. It must match the common header spellings case-insensitively
    (402index.io's convention isn't documented) without dragging along
    unrelated headers."""
    headers = {
        "Content-Type": "application/json",
        "Retry-After": "1800",
        "X-RateLimit-Limit": "50",
        "x-ratelimit-remaining": "0",
        "RateLimit-Reset": "1785020000",
        "X-Rate-Limit-Window": "3600",
        "Server": "nginx",
        "Date": "Sat, 25 Jul 2026 22:00:00 GMT",
    }
    got = reg._ratelimit_headers(headers)
    assert got == {
        "Retry-After": "1800",
        "X-RateLimit-Limit": "50",
        "x-ratelimit-remaining": "0",
        "RateLimit-Reset": "1785020000",
        "X-Rate-Limit-Window": "3600",
    }


def test_ratelimit_headers_handles_missing_headers():
    assert reg._ratelimit_headers(None) == {}
    assert reg._ratelimit_headers({}) == {}
    assert reg._ratelimit_headers({"Server": "nginx"}) == {}


def test_register_402index_captures_service_id_from_response(tmp_path, monkeypatch):
    """A first-ever registration only ever learns its 402index.io service id
    from the POST /register response body — nothing else ever surfaces it
    (402index.io has no documented list/search-by-URL endpoint). Without
    persisting it, edit_listing()'s domain-verified PATCH path (the fix for
    listings losing their price after a successful registration — see
    register_402index()'s docstring) could never engage for that offering."""
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    with mock.patch.object(reg, "_post", side_effect=_fake_post_ok), \
         mock.patch.object(reg, "time"):
        reg.register_402index(only={"dossier_check"})
    assert reg._load_state()["service_ids"] == {"dossier_check": "fake"}


def test_register_402index_prefers_patch_when_token_and_id_known(tmp_path, monkeypatch):
    """Once X402INDEX_VERIFICATION_TOKEN is set and an offering already has a
    known service id, re-sending it (force_all) must go through
    edit_listing()'s domain-verified PATCH, not the anonymous POST
    /api/v1/register — that anonymous path is what 402index.io's own docs
    say re-enters the "pending review" queue."""
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    reg._save_state({"registered_402index": ["dossier_check"], "service_ids": {"dossier_check": "svc-1"}})
    monkeypatch.setattr(reg, "X402INDEX_VERIFICATION_TOKEN", "tok-123")
    with mock.patch.object(reg, "edit_listing", return_value=(200, {"id": "svc-1"})) as m_edit, \
         mock.patch.object(reg, "_post") as m_post, \
         mock.patch.object(reg, "time"):
        results = reg.register_402index(only={"dossier_check"}, force_all=True)
    m_edit.assert_called_once()
    assert m_edit.call_args.args[0] == "svc-1"
    assert m_edit.call_args.args[1] == reg.X402INDEX_DOMAIN
    assert m_edit.call_args.args[2] == "tok-123"
    m_post.assert_not_called()
    assert results[0]["ok"] is True


def test_register_402index_falls_back_to_post_without_token(tmp_path, monkeypatch):
    """Same known-service-id offering, but no verification token set (the
    default, current state) — must still use the anonymous POST path
    unchanged, never guessing at edit_listing() without real credentials."""
    monkeypatch.setattr(reg, "STATE_PATH", str(tmp_path / "state.json"))
    reg._save_state({"registered_402index": ["dossier_check"], "service_ids": {"dossier_check": "svc-1"}})
    monkeypatch.setattr(reg, "X402INDEX_VERIFICATION_TOKEN", None)
    with mock.patch.object(reg, "edit_listing") as m_edit, \
         mock.patch.object(reg, "_post", side_effect=_fake_post_ok) as m_post, \
         mock.patch.object(reg, "time"):
        reg.register_402index(only={"dossier_check"}, force_all=True)
    m_edit.assert_not_called()
    m_post.assert_called_once()


def test_edit_listing_sends_patch_with_domain_and_token(monkeypatch):
    """edit_listing() must PATCH /api/v1/services/:id with the domain +
    verification_token proving ownership, per 402index.io's documented
    domain-verified edit flow (confirmed via diag-402index-docs.yml, since
    the docs page 403s automated fetchers from the normal dev sandbox)."""
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def getcode(self):
            return 200

        def read(self):
            return json.dumps({"id": "svc-1", "price_usd": 0.1}).encode()

    def _fake_urlopen(req, timeout=15):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["body"] = json.loads(req.data.decode())
        return _FakeResponse()

    monkeypatch.setattr(reg.urllib.request, "urlopen", _fake_urlopen)
    code, body = reg.edit_listing("svc-1", "vape-x402.vapex402.workers.dev", "tok-123", price_usd=0.1)
    assert code == 200
    assert body["price_usd"] == 0.1
    assert captured["method"] == "PATCH"
    assert captured["url"] == "https://402index.io/api/v1/services/svc-1"
    assert captured["body"] == {
        "domain": "vape-x402.vapex402.workers.dev",
        "verification_token": "tok-123",
        "price_usd": 0.1,
    }
