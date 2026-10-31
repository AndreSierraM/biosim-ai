"""Unit tests: per-IP rate limiter. Run: python3 services/api/tests/test_ratelimit.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ratelimit import RateLimiter, bucket_for


def test_allows_up_to_budget_then_429():
    lim = RateLimiter(max_hits=3, window_s=60.0)
    assert all(lim.allow("ip", now=100.0 + i)[0] for i in range(3))
    ok, retry = lim.allow("ip", now=103.0)
    assert ok is False and retry > 0, (ok, retry)


def test_window_slides_and_recovers():
    lim = RateLimiter(max_hits=1, window_s=10.0)
    assert lim.allow("ip", now=100.0)[0] is True
    assert lim.allow("ip", now=105.0)[0] is False
    assert lim.allow("ip", now=111.0)[0] is True


def test_keys_are_isolated():
    lim = RateLimiter(max_hits=1, window_s=60.0)
    assert lim.allow("a", now=100.0)[0] is True
    assert lim.allow("b", now=100.0)[0] is True
    assert lim.allow("a", now=101.0)[0] is False


def test_bucket_routing():
    assert bucket_for("/v1/runs") is not None
    assert bucket_for("/v1/plan") is not None
    assert bucket_for("/v1/runs/abc") is None
    assert bucket_for("/v1/engines") is None
    assert bucket_for("/health") is None


def main() -> int:
    test_allows_up_to_budget_then_429()
    test_window_slides_and_recovers()
    test_keys_are_isolated()
    test_bucket_routing()
    print("PASS test_ratelimit (4 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
