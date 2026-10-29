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
    pass


@dataclass
class ModelResponse:
    text: str
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_s: float = 0.0


class MetaModelClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 endpoint: str | None = None, timeout_s: int = 15):
        key = api_key or os.environ.get("META_MODEL_API_KEY", "")
        if not key:
            raise KeyNotConfigured("set META_MODEL_API_KEY (see .env.example)")
        self.api_key = key
        self.model = model or os.environ.get("META_MODEL_NAME", "muse-spark-1.3")
        base = endpoint or os.environ.get("META_MODEL_ENDPOINT", "https://api.meta.ai/v1")
        self.url = base.rstrip("/") + "/chat/completions"
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
                body = json.loads(res.read().decode())
        except urllib.error.HTTPError as e:
            raise MetaApiError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}")
        except OSError as e:
            raise MetaApiError(f"request failed: {e}")
        try:
            text = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise MetaApiError(f"unexpected response shape: {json.dumps(body)[:300]}")
        usage = body.get("usage", {})
        return ModelResponse(
            text=text,
            model=body.get("model", self.model),
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            latency_s=round(time.time() - start, 3),
        )
