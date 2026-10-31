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
    attempts: int = 1


def _public_error(status: int, body: str, request_id: str | None) -> str:
    """Short, safe provider error: status + hint, body only when tiny/generic."""
    short = " ".join(body.split())[:120]
    if status == 401:
        return "HTTP 401: bad or expired key (recreate one at dev.meta.ai)"
    if status == 429:
        extra = f": {short}" if len(short) < 40 else ""
        return f"HTTP 429: rate limited or out of credits, retry later{extra}"
    if status in (500, 502, 503, 504):
        return f"HTTP {status}: model provider temporarily unavailable, retry later"
    if short:
        return f"HTTP {status}: {short}"
    return f"HTTP {status}: model request failed"


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
                 temperature: float = 0.2, _sleep=time.sleep) -> ModelResponse:
        """One selective retry on transient failures (429/5xx/timeout).

        Auth and validation errors never retry. Provider bodies stay short
        and generic in public errors; request id + status travel instead.
        """
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
        attempts = 0
        delay = 0.5
        while True:
            attempts += 1
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
                if e.code in (429, 500, 502, 503, 504) and attempts < 2:
                    _sleep(delay)
                    delay *= 2
                    continue
                raise MetaApiError(
                    _public_error(e.code, e.read().decode(errors="replace"),
                                  _header_of(e)),
                    status_code=e.code,
                    request_id=_header_of(e),
                )
            except (OSError, TimeoutError) as e:
                if attempts < 2:
                    _sleep(delay)
                    delay *= 2
                    continue
                raise MetaApiError(f"request failed after {attempts} attempts: "
                                   f"{type(e).__name__}")
            try:
                text = body["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise MetaApiError("unexpected response shape from model provider")
            usage = body.get("usage", {}) or {}
            request_id = body.get("id") or body.get("request_id") or body.get("requestId")
            return ModelResponse(
                text=text,
                model=body.get("model", self.model),
                tokens_in=usage.get("prompt_tokens"),
                tokens_out=usage.get("completion_tokens"),
                latency_s=round(time.time() - start, 3),
                request_id=request_id or header_request_id,
                attempts=attempts,
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
