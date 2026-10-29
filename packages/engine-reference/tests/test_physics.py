"""Physics invariants (stdlib only). Run: python3 tests/test_physics.py"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adapter import ReferenceAdapter

ROOT = Path(__file__).parent.parent


def load(name: str):
    raw = json.loads((ROOT / "params" / name).read_text())
    return raw, int(raw.pop("seed"))


def center_of_mass(frame):
    n = len(frame["cells"])
    return [
        sum(c[k] for c in frame["cells"]) / n
        for k in ("x_um", "y_um", "z_um")
    ]


def main() -> int:
    adapter = ReferenceAdapter()
    base_params, seed = load("baseline.json")

    # 1. Mirror symmetry: zero noise + symmetric start -> COM stays at origin
    #    and cells mirror each other every frame.
    sym = dict(base_params, diffusion_um2_per_min=0.0,
               initial_positions=[[-28.0, 0.0, 0.0], [28.0, 0.0, 0.0]])
    art = adapter.run(sym, seed)
    worst = 0.0
    for f in art["frames"]:
        a, b = f["cells"]
        worst = max(worst, *(abs(v) for v in center_of_mass(f)))
        for k in ("x_um", "y_um", "z_um"):
            worst = max(worst, abs(a[k] + b[k]))
    assert worst < 1e-6, f"symmetry broken: {worst}"

    # 2. Overlap stays bounded on both variants (no deep interpenetration).
    summaries = {}
    for name in ("baseline.json", "high-adhesion.json"):
        params, s = load(name)
        summaries[name] = adapter.run(params, s)["summary"]
    for name, sm in summaries.items():
        assert sm["max_overlap_um"] < 5.0, f"{name} overlaps {sm['max_overlap_um']}um"

    # 3. Doubled adhesion sticks while baseline separates.
    base, high = summaries["baseline.json"], summaries["high-adhesion.json"]
    assert high["final_distance_um"] < base["final_distance_um"], (
        f"high final_d={high['final_distance_um']} not below base={base['final_distance_um']}"
    )
    assert high["contact_duration_min"] > 5 * base["contact_duration_min"], (
        f"weak adhesion contrast: {high['contact_duration_min']} vs {base['contact_duration_min']}"
    )

    print(
        f"PASS physics symmetry<{worst:.2e} "
        f"overlap base={base['max_overlap_um']}um high={high['max_overlap_um']}um "
        f"contact base={base['contact_duration_min']}min high={high['contact_duration_min']}min"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
