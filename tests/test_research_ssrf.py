"""Tests for skillforge/research.py's SSRF fix (CodeRabbit, PR #282):
_is_public_hostname(), _validate_fetch_url(), and _fetch_keyless()'s
blocking behavior. Real gap this closes: _fetch_keyless() (the keyless
fallback web_reputation_check() uses to escalate a scam-mention hit to a
real page fetch) previously had zero URL validation -- a search result
pointing at a loopback/private/link-local address (e.g. cloud metadata,
169.254.169.254) would be fetched exactly like any public page. Hermetic:
socket.getaddrinfo and the MCP `fetch`/urllib layers are all mocked, no
real network calls.
"""
from unittest import mock

from skillforge import research


def _addrinfo(ip):
    # Real getaddrinfo() shape: list of (family, type, proto, canonname, sockaddr)
    return [(2, 1, 6, "", (ip, 0))]


def test_is_public_hostname_true_for_real_public_ip():
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        assert research._is_public_hostname("example.com") is True


def test_is_public_hostname_false_for_loopback():
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("127.0.0.1")):
        assert research._is_public_hostname("localhost") is False


def test_is_public_hostname_false_for_private_range():
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("10.0.0.5")):
        assert research._is_public_hostname("internal.example") is False


def test_is_public_hostname_false_for_link_local_cloud_metadata():
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        assert research._is_public_hostname("metadata.internal") is False


def test_is_public_hostname_false_when_any_resolved_address_is_private():
    # DNS-rebinding-style multi-answer: one public, one private -> reject
    # the whole hostname, not just the "first" address (fail closed).
    both = [(2, 1, 6, "", ("93.184.216.34", 0)), (2, 1, 6, "", ("10.0.0.5", 0))]
    with mock.patch.object(research.socket, "getaddrinfo", return_value=both):
        assert research._is_public_hostname("mixed.example") is False


def test_is_public_hostname_false_on_resolution_failure():
    with mock.patch.object(research.socket, "getaddrinfo", side_effect=OSError("no such host")):
        assert research._is_public_hostname("nope.invalid") is False


def test_validate_fetch_url_rejects_non_http_schemes():
    assert research._validate_fetch_url("file:///etc/passwd") is False
    assert research._validate_fetch_url("ftp://example.com/x") is False
    assert research._validate_fetch_url("gopher://example.com") is False


def test_validate_fetch_url_rejects_missing_hostname():
    assert research._validate_fetch_url("https://") is False
    assert research._validate_fetch_url("not a url at all") is False


def test_validate_fetch_url_accepts_public_https_url():
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        assert research._validate_fetch_url("https://example.com/page") is True


def test_validate_fetch_url_rejects_private_hostname():
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("172.16.0.1")):
        assert research._validate_fetch_url("http://internal.example/x") is False


def test_fetch_keyless_blocks_private_url_before_any_network_call(monkeypatch):
    monkeypatch.setattr(research, "_available", lambda name: False)
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("127.0.0.1")), \
         mock.patch.object(research.urllib.request, "build_opener") as m_opener:
        result = research._fetch_keyless("http://127.0.0.1/secret")
    assert result["provider"] == "urllib-keyless"
    assert "blocked" in result["error"]
    m_opener.assert_not_called()


def test_fetch_keyless_allows_public_url(monkeypatch):
    monkeypatch.setattr(research, "_available", lambda name: False)

    class _FakeResp:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return b"<html><body>hello world</body></html>"

    class _FakeOpener:
        def open(self, req, timeout=None):
            return _FakeResp()

    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")), \
         mock.patch.object(research.urllib.request, "build_opener", return_value=_FakeOpener()):
        result = research._fetch_keyless("https://example.com/page")
    assert result["provider"] == "urllib-keyless"
    assert "hello world" in result["content"]


def test_ssrf_safe_redirect_handler_blocks_redirect_to_private_target():
    handler = research._SSRFSafeRedirectHandler()
    req = mock.Mock()
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        with mock.patch("urllib.request.HTTPRedirectHandler.redirect_request") as m_super:
            try:
                handler.redirect_request(req, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/")
                raised = False
            except research.urllib.error.URLError:
                raised = True
    assert raised is True
    m_super.assert_not_called()


def test_ssrf_safe_redirect_handler_allows_redirect_to_public_target():
    handler = research._SSRFSafeRedirectHandler()
    req = mock.Mock()
    with mock.patch.object(research.socket, "getaddrinfo", return_value=_addrinfo("93.184.216.34")):
        with mock.patch("urllib.request.HTTPRedirectHandler.redirect_request", return_value="ok") as m_super:
            result = handler.redirect_request(req, None, 302, "Found", {}, "https://example.com/next")
    assert result == "ok"
    m_super.assert_called_once()
