"""Pure trajectory metrics computed from simulation frames.

Frames: [{"t_min": float, "cells": [{"dead": bool, ...}, ...]}, ...].
No I/O, no third-party dependencies.
"""
from __future__ import annotations


def live_counts(frames: list[dict]) -> list[int]:
    """Live (non-dead) cell count per frame."""
    return [sum(1 for c in f.get("cells", []) if not c.get("dead")) for f in frames]


def total_counts(frames: list[dict]) -> list[int]:
    """Total cell count per frame."""
    return [len(f.get("cells", [])) for f in frames]


def final_live_fraction(frames: list[dict]) -> float:
    """Fraction of final-frame cells alive (0.0 when empty)."""
    if not frames or not frames[-1].get("cells"):
        return 0.0
    cells = frames[-1]["cells"]
    return sum(1 for c in cells if not c.get("dead")) / len(cells)


def final_dead_fraction(frames: list[dict]) -> float:
    """Fraction of final-frame cells dead (0.0 when empty)."""
    if not frames or not frames[-1].get("cells"):
        return 0.0
    cells = frames[-1]["cells"]
    return sum(1 for c in cells if c.get("dead")) / len(cells)


def peak_live(frames: list[dict]) -> tuple[int, float | None]:
    """Highest live count and its first time (0, None when no frames)."""
    if not frames:
        return 0, None
    counts = live_counts(frames)
    top = max(counts)
    t = next(f["t_min"] for f, n in zip(frames, counts) if n == top)
    return top, t


def t50_min(frames: list[dict]) -> float | None:
    """First t_min at/after the live peak where live falls to half the max.

    None when the population never drops that far (growth-only runs),
    when no frame exists, or when no cell was ever alive.
    """
    if not frames:
        return None
    counts = live_counts(frames)
    top = max(counts)
    if top <= 0:
        return None
    peak_idx = counts.index(top)
    for f, n in zip(frames[peak_idx:], counts[peak_idx:]):
        if n <= top / 2:
            return f["t_min"]
    return None


def summarize_frames(frames: list[dict]) -> dict:
    """Metric fields merged into the adapter summary (additive only)."""
    top, top_t = peak_live(frames)
    return {
        "final_live_fraction": round(final_live_fraction(frames), 6),
        "final_dead_fraction": round(final_dead_fraction(frames), 6),
        "t50_min": t50_min(frames),
        "peak_live": top,
        "peak_live_t_min": top_t,
    }
