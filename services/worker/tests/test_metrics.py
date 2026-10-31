"""Unit tests: pure frame metrics + golden dose_1 spot check.

Run: python3 services/worker/tests/test_metrics.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.metrics import (
    final_dead_fraction,
    final_live_fraction,
    live_counts,
    peak_live,
    summarize_frames,
    t50_min,
)

HERE = Path(__file__).parent
GOLDEN = HERE / "fixtures" / "golden" / "physicell_dose_1.json"


def _frame(t: float, n_live: int, n_dead: int) -> dict:
    cells = [{"dead": False} for _ in range(n_live)]
    cells += [{"dead": True} for _ in range(n_dead)]
    return {"t_min": t, "cells": cells}


def test_decline_run():
    frames = [_frame(0.0, 10, 0), _frame(60.0, 20, 0),
              _frame(120.0, 10, 10), _frame(180.0, 4, 16)]
    assert live_counts(frames) == [10, 20, 10, 4]
    assert final_live_fraction(frames) == 0.2
    assert final_dead_fraction(frames) == 0.8
    assert peak_live(frames) == (20, 60.0)
    assert t50_min(frames) == 120.0  # first post-peak frame at/below 10
    s = summarize_frames(frames)
    assert s == {"final_live_fraction": 0.2, "final_dead_fraction": 0.8,
                 "t50_min": 120.0, "peak_live": 20, "peak_live_t_min": 60.0}


def test_growth_only_has_no_t50():
    frames = [_frame(0.0, 5, 0), _frame(60.0, 10, 0), _frame(120.0, 15, 5)]
    assert t50_min(frames) is None
    assert peak_live(frames) == (15, 120.0)
    assert final_live_fraction(frames) == 0.75


def test_empty_and_all_dead():
    assert summarize_frames([]) == {
        "final_live_fraction": 0.0, "final_dead_fraction": 0.0,
        "t50_min": None, "peak_live": 0, "peak_live_t_min": None}
    frames = [_frame(0.0, 0, 3), _frame(60.0, 0, 5)]
    assert t50_min(frames) is None
    assert peak_live(frames) == (0, 0.0)
    assert final_dead_fraction(frames) == 1.0


def test_golden_dose_1():
    assert GOLDEN.exists(), f"golden fixture inexistente: {GOLDEN}"
    golden = json.loads(GOLDEN.read_text())
    frames, summary = golden["frames"], golden["summary"]
    s = summarize_frames(frames)
    assert summary["final_live"] == 41 and summary["final_dead"] == 3
    assert s["final_live_fraction"] == round(41 / 44, 6)
    assert s["final_dead_fraction"] == round(3 / 44, 6)
    assert s["peak_live"] == 41 and s["peak_live_t_min"] == 4320.0
    assert s["t50_min"] is None  # growth-only: live never halves from peak


def main() -> int:
    test_decline_run()
    test_growth_only_has_no_t50()
    test_empty_and_all_dead()
    test_golden_dose_1()
    print("PASS test_metrics (4 casos: sinteticos + golden dose_1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
