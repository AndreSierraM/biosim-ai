"""Reference two-cell adhesion solver.

Development scaffold only: rigid-sphere overdamped dynamics used to build
the viewer, API and provenance plumbing before the PhysiCell adapter (#8)
lands. NEVER present its outputs as PhysiCell results.

Model (v0.2.0): two spheres (radius R) in 3D, overdamped (v = F / gamma,
the correct regime for cells at low Reynolds number).
  * Hertz-like repulsive core: F ~ overlap^1.5 while surfaces overlap
  * adhesion over a thin capture shell with a cosine taper (smooth,
    no on/off jump at contact)
  * approach phase with smooth ramp in/out
  * background separation pull with smooth distance taper
  * Brownian motion from a diffusion coefficient: sigma = sqrt(2 D dt)
  * Heun (predictor-corrector) integration of the drift term plus
    Euler-Maruyama noise (standard for additive-noise SDEs)
Units: micrometers (um) and minutes. Force units are arbitrary; gamma
sets the velocity scale.
"""
from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass

ENGINE_ID = "reference-2cell"
ENGINE_VERSION = "0.2.0"
INTEGRATOR = "heun-drift+euler-maruyama-noise"


@dataclass(frozen=True)
class SolverParams:
    cell_radius_um: float = 10.0
    dt_min: float = 0.01
    duration_min: float = 20.0
    frame_every: int = 10
    approach_force: float = 60.0
    approach_until_min: float = 1.0
    separate_force: float = 8.0
    separation_range_um: float = 150.0
    separation_width_um: float = 10.0
    hertz_k: float = 12.0
    adhesion: float = 6.0
    adhesion_shell_um: float = 1.0
    diffusion_um2_per_min: float = 0.02
    gamma: float = 1.0
    initial_gap_um: float = 36.0
    initial_positions: list | None = None


def _smoothstep(x: float) -> float:
    x = 0.0 if x <= 0.0 else 1.0 if x >= 1.0 else x
    return x * x * (3.0 - 2.0 * x)


def _pair_forces(p0, p1, t: float, p: SolverParams):
    """Force vectors (f0, f1) plus center distance. Positive scalar = separating."""
    dx, dy, dz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    d = math.sqrt(dx * dx + dy * dy + dz * dz)
    if d < 1e-9:
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1e-9
    ax, ay, az = dx / d, dy / d, dz / d
    diameter = 2.0 * p.cell_radius_um
    overlap = diameter - d

    s = 0.0
    s += (
        p.separate_force
        * 0.5
        * (1.0 - math.tanh((d - p.separation_range_um) / p.separation_width_um))
    )
    if t < p.approach_until_min:
        s -= p.approach_force * _smoothstep(
            min(t, p.approach_until_min - t) / 0.1
        )
    if overlap > 0.0:
        s += p.hertz_k * overlap**1.5
    shell_edge = diameter + p.adhesion_shell_um
    if d < shell_edge:
        if d <= diameter:
            profile = 1.0
        else:
            profile = 0.5 * (
                1.0 + math.cos(math.pi * (d - diameter) / p.adhesion_shell_um)
            )
        s -= p.adhesion * profile
    return (-s * ax, -s * ay, -s * az), (s * ax, s * ay, s * az), d


def run(params: SolverParams, seed: int) -> dict:
    rng = random.Random(seed)
    if params.initial_positions is not None:
        pos = [list(map(float, row)) for row in params.initial_positions]
        assert len(pos) == 2 and all(len(r) == 3 for r in pos)
    else:
        half = params.cell_radius_um + params.initial_gap_um / 2.0
        pos = [[-half, 2.0, 0.0], [half, -2.0, 1.0]]

    steps = int(round(params.duration_min / params.dt_min))
    jitter = math.sqrt(2.0 * params.diffusion_um2_per_min * params.dt_min)
    k = params.dt_min / params.gamma
    diameter = 2.0 * params.cell_radius_um

    frames: list[dict] = []
    contact_steps = 0
    min_distance = float("inf")
    max_overlap = 0.0
    for step in range(steps + 1):
        t = step * params.dt_min
        _, _, dist = _pair_forces(pos[0], pos[1], t, params)
        in_contact = dist < diameter
        contact_steps += 1 if in_contact else 0
        min_distance = min(min_distance, dist)
        max_overlap = max(max_overlap, diameter - dist)
        if step % params.frame_every == 0:
            frames.append(
                {
                    "t_min": round(t, 6),
                    "contact": in_contact,
                    "cells": [
                        {
                            "id": f"cell-{i}",
                            "x_um": round(q[0], 6),
                            "y_um": round(q[1], 6),
                            "z_um": round(q[2], 6),
                            "dead": False,
                        }
                        for i, q in enumerate(pos)
                    ],
                }
            )
        if step == steps:
            break
        # Heun on the drift: Euler predictor, trapezoid corrector, noise once.
        f0a, f1a, _ = _pair_forces(pos[0], pos[1], t, params)
        q0 = [pos[0][j] + k * f0a[j] for j in range(3)]
        q1 = [pos[1][j] + k * f1a[j] for j in range(3)]
        f0b, f1b, _ = _pair_forces(q0, q1, t + params.dt_min, params)
        for i, (fa, fb) in enumerate(((f0a, f0b), (f1a, f1b))):
            for j in range(3):
                pos[i][j] += 0.5 * k * (fa[j] + fb[j]) + rng.gauss(0.0, jitter)

    final_dist = _pair_forces(pos[0], pos[1], params.duration_min, params)[2]
    cx = sum(p[0] for p in pos) / 2.0
    cy = sum(p[1] for p in pos) / 2.0
    cz = sum(p[2] for p in pos) / 2.0
    final_radius = max(
        math.dist(p, (cx, cy, cz)) for p in pos
    )
    return {
        "meta": {
            "engine_id": ENGINE_ID,
            "engine_version": ENGINE_VERSION,
            "integrator": INTEGRATOR,
            "seed": seed,
            "units": {"length": "um", "time": "min"},
            "dt_min": params.dt_min,
            "duration_min": params.duration_min,
            "frame_every": params.frame_every,
            "params": asdict(params),
            "assumptions": [
                "Rigid spherical cells; no membrane deformation.",
                "Overdamped dynamics (v = F / gamma); inertia neglected.",
                "Hertz-like repulsive core; adhesion over a thin capture shell.",
                "Background separation pull tapers smoothly beyond 150 um.",
                "Development scaffold: not PhysiCell, not calibrated biology.",
            ],
        },
        "frames": frames,
        "summary": {
            "n_frames": len(frames),
            "initial_cells": 2,
            "final_live": 2,
            "final_dead": 0,
            "final_radius_um": round(final_radius, 6),
            "contact_duration_min": round(contact_steps * params.dt_min, 6),
            "min_distance_um": round(min_distance, 6),
            "max_overlap_um": round(max(max_overlap, 0.0), 6),
            "final_distance_um": round(final_dist, 6),
        },
    }
