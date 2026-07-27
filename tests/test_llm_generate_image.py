"""Tests for agents/llm.py::generate_image() -- the real xAI Grok Image
text-to-image call (a separate product/endpoint from every /chat/completions
provider elsewhere in this module) and its own daily-count usage cap.
Hermetic: urllib.request.urlopen and the usage-file path are both
mocked/redirected, no real network call, no real file writes outside tmp_path.
"""
import io
import json
import urllib.error
from unittest import mock

from agents import llm


def _fake_response(body_dict):
    body = json.dumps(body_dict).encode()

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def read(self):
            return body
    return Resp()


def test_generate_image_returns_none_without_api_key(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY_1", raising=False)
    assert llm.generate_image("a prompt") is None


def test_generate_image_parses_real_response_shape(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
    with mock.patch("urllib.request.urlopen",
                     return_value=_fake_response({"data": [{"url": "https://xai.example/img.png"}]})) as mocked:
        url = llm.generate_image("editorial illustration of a rally")
    assert url == "https://xai.example/img.png"
    # confirm it hit xAI's real images endpoint, not /chat/completions
    req = mocked.call_args[0][0]
    assert req.full_url == "https://api.x.ai/v1/images/generations"
    payload = json.loads(req.data.decode())
    assert payload["model"] == llm.XAI_IMAGE_MODEL
    assert "messages" not in payload  # images API shape, not chat completions


def test_generate_image_returns_none_on_missing_url_field(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
    with mock.patch("urllib.request.urlopen", return_value=_fake_response({"data": [{}]})):
        assert llm.generate_image("prompt") is None


def test_generate_image_never_raises_on_network_error(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
    with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("boom")):
        assert llm.generate_image("prompt") is None


def test_generate_image_records_usage_and_respects_daily_cap(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setenv("XAI_IMAGE_DAILY_CAP", "2")
    usage_path = tmp_path / "xai_image_usage.json"
    monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(usage_path))

    with mock.patch("urllib.request.urlopen",
                     return_value=_fake_response({"data": [{"url": "https://xai.example/1.png"}]})):
        assert llm.generate_image("p1") == "https://xai.example/1.png"
        assert llm.generate_image("p2") == "https://xai.example/1.png"
        # third call this "day" should be blocked by the cap without even
        # attempting the network call
        with mock.patch("urllib.request.urlopen") as third_call:
            assert llm.generate_image("p3") is None
            third_call.assert_not_called()

    usage = json.loads(usage_path.read_text())
    assert usage["count"] == 2


def test_generate_image_prompt_is_truncated_to_1000_chars(monkeypatch, tmp_path):
    monkeypatch.setenv("XAI_API_KEY_1", "key1")
    monkeypatch.setattr(llm, "IMAGE_USAGE_PATH", str(tmp_path / "xai_image_usage.json"))
    long_prompt = "x" * 5000
    with mock.patch("urllib.request.urlopen",
                     return_value=_fake_response({"data": [{"url": "https://xai.example/img.png"}]})) as mocked:
        llm.generate_image(long_prompt)
    payload = json.loads(mocked.call_args[0][0].data.decode())
    assert len(payload["prompt"]) == 1000
