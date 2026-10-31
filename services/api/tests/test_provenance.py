"""Unit tests: Meta provenance plumbing with mocked HTTP. Run: python3 services/api/tests/test_provenance.py"""
import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.meta_client import MetaApiError, MetaModelClient, ModelResponse
from app.planner import plan_prompt

SECRET = "sk-PROBE-SECRET-xyz"


class _FakeHTTP:
    def __init__(self, body: dict, headers=None):
        self._body = json.dumps(body).encode()
        self.headers = headers or {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _install(fake=None, error=None):
    real = urllib.request.urlopen

    def _mock(req, timeout=None):
        if error is not None:
            raise error
        return fake

    urllib.request.urlopen = _mock
    return real


def _restore(real):
    urllib.request.urlopen = real


def _client():
    return MetaModelClient(api_key=SECRET, model="probe-model",
                           endpoint="https://probe.invalid/v1")


def test_happy_path_records_provenance():
    body = {"id": "req-123",
            "model": "probe-model-actual",
            "choices": [{"message": {"content": '{"kind": "unsupported", "reason": "x"}'}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 22}}
    real = _install(_FakeHTTP(body, {"x-request-id": "hdr-999"}))
    try:
        resp = _client().complete("sys", "user")
    finally:
        _restore(real)
    assert isinstance(resp, ModelResponse)
    assert resp.request_id == "req-123", resp.request_id  # body id wins
    assert resp.model == "probe-model-actual"
    assert (resp.tokens_in, resp.tokens_out) == (11, 22)
    assert resp.latency_s >= 0.0


def test_header_request_id_fallback_and_missing_usage():
    body = {"choices": [{"message": {"content": "hi"}}]}
    real = _install(_FakeHTTP(body, {"x-request-id": "hdr-999"}))
    try:
        resp = _client().complete("sys", "user")
    finally:
        _restore(real)
    assert resp.request_id == "hdr-999", resp.request_id
    assert resp.tokens_in is None and resp.tokens_out is None
    assert resp.model == "probe-model"  # configured default, not invented


def test_unexpected_shape_raises_without_key():
    real = _install(_FakeHTTP({"nope": True}))
    try:
        _client().complete("sys", "user")
    except MetaApiError as e:
        assert SECRET not in str(e), "key leaked into error"
    else:
        raise AssertionError("bad shape accepted")
    finally:
        _restore(real)


def test_http_error_carries_status_and_id_without_key():
    err = urllib.error.HTTPError(
        "https://probe.invalid/v1/chat/completions", 429, "Too Many",
        {"x-request-id": "hdr-429"}, io.BytesIO(b"rate limited"))
    real = _install(error=err)
    try:
        _client().complete("sys", "user")
    except MetaApiError as e:
        assert e.status_code == 429, e.status_code
        assert e.request_id == "hdr-429", e.request_id
        assert SECRET not in str(e), "key leaked into error"
        assert "rate limited" in str(e)
    else:
        raise AssertionError("HTTPError swallowed")
    finally:
        _restore(real)


class _FakePlannerClient:
    def __init__(self, text, **prov):
        self._resp = ModelResponse(text=text, model="live-probe", **prov)

    def complete(self, system, user):
        return self._resp


def test_planner_threads_live_provenance():
    text = json.dumps({"kind": "spheroid_oxygen_compare", "engine": "physicell",
                       "oxygen_high": 38.0, "oxygen_low": 12.0})
    plan = plan_prompt("compare oxygen",
                       _FakePlannerClient(text, request_id="req-1",
                                          tokens_in=50, tokens_out=20,
                                          latency_s=1.25),
                       ["physicell"])
    assert plan["validated"] is True, plan
    prov = plan["provenance"]
    assert prov["model_version"] == "live-probe"
    assert prov["request_id"] == "req-1"
    assert (prov["tokens_in"], prov["tokens_out"], prov["latency_s"]) == (50, 20, 1.25)
    assert prov["prompt_template"] and prov["schema_version"] == "1.0.0"


def test_planner_provenance_honest_without_key():
    text = json.dumps({"kind": "unsupported", "reason": "nope"})
    plan = plan_prompt("atom view", _FakePlannerClient(text), ["physicell"])
    assert plan["validated"] is False
    prov = plan["provenance"]
    assert prov["model_version"] == "live-probe"
    assert prov["request_id"] is None
    assert prov["tokens_in"] is None and prov["tokens_out"] is None


def main() -> int:
    test_happy_path_records_provenance()
    test_header_request_id_fallback_and_missing_usage()
    test_unexpected_shape_raises_without_key()
    test_http_error_carries_status_and_id_without_key()
    test_planner_threads_live_provenance()
    test_planner_provenance_honest_without_key()
    print("PASS test_provenance (6 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
