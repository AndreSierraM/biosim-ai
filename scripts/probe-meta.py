"""Probe the real Meta Model API without running any solver.

Usage:
  META_MODEL_API_KEY=... python3 scripts/probe-meta.py
  META_MODEL_API_KEY=... META_MODEL_NAME=muse-spark-1.3 python3 scripts/probe-meta.py

Prints model, request id, latency and the raw JSON reply for one tiny
planning-shaped prompt. Never writes runs or touches engines.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

from app.meta_client import KeyNotConfigured, MetaApiError, MetaModelClient


def main() -> int:
    try:
        client = MetaModelClient()
    except KeyNotConfigured as e:
        print(f"no key: {e}")
        print("get one at https://dev.meta.ai -> Start building -> API key, then:")
        print("  export META_MODEL_API_KEY='LLM|...'  # never commit it")
        return 2
    print(f"endpoint: {client.url} model: {client.model}")
    try:
        resp = client.complete(
            "You plan tumor spheroid experiments. Reply with JSON only, no prose.",
            'Request: how does oxygen availability affect tumor spheroid growth? '
            "Respond with JSON only.",
        )
    except MetaApiError as e:
        print(f"Meta call failed: {e}")
        if e.status_code is not None:
            print(f"http: {e.status_code}")
        if e.request_id:
            print(f"request: {e.request_id}")
        return 1
    print(f"model: {resp.model}")
    print(f"request_id: {resp.request_id}")
    print(f"latency_s: {resp.latency_s} tokens_in={resp.tokens_in} tokens_out={resp.tokens_out}")
    print(f"reply: {resp.text[:500]}")
    try:
        data = json.loads(resp.text)
        print(f"kind: {data.get('kind')}")
    except (json.JSONDecodeError, TypeError, AttributeError):
        print("reply was not JSON")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
