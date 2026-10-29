"""Stdlib JSON HTTP client for acceptance handlers."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("BIOSIM_API_URL", "http://localhost:8123")


class HttpError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}: {body[:300]}")
        self.status = status
        self.body = body


def _req(method: str, path: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        raise HttpError(e.code, e.read().decode(errors="replace"))


def get(path: str):
    return _req("GET", path)


def post(path: str, payload: dict):
    return _req("POST", path, payload)
