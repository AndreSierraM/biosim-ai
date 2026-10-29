"""Golden test: PhysiCell trajectories are deterministic vs fixtures.

Re-runs the real adapter (seed 7, oxygen 38, max_time 4320, interval 60)
for doses 0/1/10 uM and compares against committed fixtures byte-identically
(json with sort_keys) plus summary final_live/final_dead.
Run: python3 services/worker/tests/test_golden_physicell.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.physicell.adapter import PhysiCellAdapter

HERE = Path(__file__).parent
GOLDEN = HERE / "fixtures" / "golden"
DOSES = (0, 1, 10)
SEED = 7


def run_dose(adapter: PhysiCellAdapter, dose: int) -> dict:
    params = adapter.default_params()
    params.update({"oxygen": 38.0, "drug_dose": float(dose),
                   "max_time_min": 4320.0, "report_interval_min": 60.0})
    result = adapter.run(params, SEED)
    return {"params": params, "seed": SEED,
            "frames": result["frames"], "summary": result["summary"]}


def test_golden_dose(dose: int) -> float:
    adapter = PhysiCellAdapter()
    path = GOLDEN / f"physicell_dose_{dose}.json"
    assert path.exists(), f"golden fixture inexistente: {path}"
    expected = json.loads(path.read_text())
    t0 = time.time()
    actual = run_dose(adapter, dose)
    dt = time.time() - t0
    tag = f"dosis {dose} uM (seed {SEED})"
    exp_s, act_s = expected["summary"], actual["summary"]
    assert act_s["final_live"] == exp_s["final_live"], (
        f"DIVERGE {tag}: final_live {act_s['final_live']} != golden {exp_s['final_live']}")
    assert act_s["final_dead"] == exp_s["final_dead"], (
        f"DIVERGE {tag}: final_dead {act_s['final_dead']} != golden {exp_s['final_dead']}")
    exp_frames = json.dumps(expected["frames"], sort_keys=True)
    act_frames = json.dumps(actual["frames"], sort_keys=True)
    assert act_frames == exp_frames, (
        f"DIVERGE {tag}: frames difieren del golden "
        f"(golden {len(exp_frames)} bytes, actual {len(act_frames)} bytes)")
    print(f"PASS {tag}: {len(actual['frames'])} frames byte-identicos, "
          f"live={act_s['final_live']} dead={act_s['final_dead']} en {dt:.1f}s")
    return dt


def main() -> int:
    times = {dose: test_golden_dose(dose) for dose in DOSES}
    print("PASS test_golden_physicell (3 dosis): "
          + ", ".join(f"{d}uM={t:.1f}s" for d, t in times.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
