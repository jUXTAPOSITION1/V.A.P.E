"""Tests for agents/x402_index_claim.py::status() — a read-only GET of a
real 402index.io service-detail URL (never a guessed/undocumented list-all
endpoint, since 402index.io's api-docs don't document one). Hermetic:
urllib.request.urlopen is always mocked, no real network call.
"""
from unittest import mock
import urllib.error

import pytest

from agents import x402_index_claim as claim


class _FakeResponse:
    def __init__(self, code, body):
        self._code = code
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def getcode(self):
        return self._code

    def read(self):
        return self._body.encode()

    @property
    def headers(self):
        return {"Content-Type": "text/html"}


def test_status_prints_body_on_200(capsys):
    with mock.patch.object(claim.urllib.request, "urlopen",
                            return_value=_FakeResponse(200, "<html>listed: yes</html>")):
        claim.status("https://402index.io/service/fake-uuid")
    out = capsys.readouterr().out
    assert "HTTP 200" in out
    assert "listed: yes" in out


def test_status_exits_nonzero_on_404(capsys):
    err = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
    err.read = lambda: b"not found"
    with mock.patch.object(claim.urllib.request, "urlopen", side_effect=err):
        with pytest.raises(SystemExit) as exc:
            claim.status("https://402index.io/service/does-not-exist")
    assert exc.value.code == 1


def test_status_exits_nonzero_on_connection_failure():
    with mock.patch.object(claim.urllib.request, "urlopen", side_effect=OSError("boom")):
        with pytest.raises(SystemExit) as exc:
            claim.status("https://402index.io/service/fake-uuid")
    assert exc.value.code == 1
