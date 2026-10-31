"""Tiny per-IP rate limiter (demo protection, no Redis).

Sliding-window counters in memory: POST /v1/runs and POST /v1/plan are
expensive (solver time, model spend), so anonymous traffic gets a budget
and controlled 429 + Retry-After instead of an unbounded queue.
"""
from __future__ import annotations

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, max_hits: int, window_s: float):
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, float]:
        """True + 0 when under budget; False + retry_after_s when over."""
        now = time.time() if now is None else now
        with self._lock:
            queue = self._hits.setdefault(key, deque())
            while queue and queue[0] <= now - self.window_s:
                queue.popleft()
            if len(queue) >= self.max_hits:
                return False, max(0.0, queue[0] + self.window_s - now)
            queue.append(now)
            return True, 0.0


RUN_LIMIT = RateLimiter(max_hits=30, window_s=60.0)
PLAN_LIMIT = RateLimiter(max_hits=60, window_s=60.0)


def bucket_for(path: str) -> RateLimiter | None:
    if path == "/v1/runs":
        return RUN_LIMIT
    if path == "/v1/plan":
        return PLAN_LIMIT
    return None
