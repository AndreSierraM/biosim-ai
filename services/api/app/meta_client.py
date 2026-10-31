"""Meta Model API client (OpenAI-compatible wire, stdlib only).

Config via env: META_MODEL_API_KEY (required), META_MODEL_NAME
(default muse-spark-1.3), META_MODEL_ENDPOINT (default https://api.meta.ai/v1).
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


class KeyNotConfigured(Exception):
    pass


class MetaApiError(Exception):
    """Provider failure. Carries HTTP status + request id; never secrets."""

    def __init__(self, message: str, *, status_code: int | None = None,
                 request_id: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


@dataclass
class ModelResponse:
    text: str
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_s: float = 0.0
    request_id: str | None = None


class MetaModelClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 endpoint: str | None = None, timeout_s: int = 15):
        key = (api_key or os.environ.get("META_MODEL_API_KEY", "")).strip()
        if not key:
            raise KeyNotConfigured("set META_MODEL_API_KEY (see .env.example)")
        self.api_key = key
        self.model = (model or os.environ.get("META_MODEL_NAME",
                                              "muse-spark-1.3")).strip() or "muse-spark-1.3"
        base = (endpoint or os.environ.get("META_MODEL_ENDPOINT",
                                           "https://api.meta.ai/v1")).strip()
        base = base.rstrip("/")
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        self.url = base + "/chat/completions"
        self.timeout_s = timeout_s

    def complete(self, system: str, user: str, max_tokens: int = 800,
                 temperature: float = 0.2) -> ModelResponse:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode(),
            headers={"content-type": "application/json",
                     "authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as res:
                raw = res.read().decode()
                try:
                    headers = res.headers
                except AttributeError:
                    headers = {}
                get_header = (headers.get if hasattr(headers, "get")
                              else lambda k, d=None: d)
                header_request_id = get_header("x-request-id")
                body = json.loads(raw)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            hint = ""
            if e.code == 401:
                hint = " (bad/expired key: recreate one at dev.meta.ai)"
            elif e.code == 429:
                hint = " (rate limited or out of credits: retry later)"
            raise MetaApiError(
                f"HTTP {e.code}: {body}{hint}",
                status_code=e.code,
                request_id=_header_of(e),
            )
        except OSError as e:
            raise MetaApiError(f"request failed: {e}")
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise MetaApiError(f"unexpected response shape: {json.dumps(body)[:300]}")
        usage = body.get("usage", {}) or {}
        request_id = body.get("id") or body.get("request_id") or body.get("requestId")
        return ModelResponse(
            text=text,
            model=body.get("model", self.model),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            latency_s=round(time.time() - start, 3),
            request_id=request_id or header_request_id,
        )


def _header_of(http_error) -> str | None:
    """Best-effort request id from an HTTP error (headers may be absent)."""
    try:
        headers = http_error.headers
    except AttributeError:
        return None
    if headers is None or not hasattr(headers, "get"):
        return None
    return headers.get("x-request-id")
