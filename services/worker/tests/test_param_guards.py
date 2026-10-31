"""Unit tests: PhysiCell parameter guardrails. Run: python3 services/worker/tests/test_param_guards.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.physicell.adapter import PhysiCellAdapter, validate_params


def test_defaults_have_no_cell_radius():
    defaults = PhysiCellAdapter().default_params()
    assert "cell_radius_um" not in defaults, (
        "cell_radius_um is fixed by the assay binary and must not be offered")


def test_validate_accepts_defaults():
    validate_params({})
    validate_params(PhysiCellAdapter().default_params())


def test_validate_rejects_cell_radius():
    try:
        validate_params({"cell_radius_um": 10.0})
    except ValueError as e:
        assert "not supported" in str(e), str(e)
    else:
        raise AssertionError("cell_radius_um silently accepted")


def test_validate_rejects_out_of_range():
    bad = [
        {"oxygen": 0.0},
        {"oxygen": 101.0},
        {"drug_dose": -1.0},
        {"drug_dose": 101.0},
        {"drug_ec50": 0.0},
        {"drug_kill_max": 0.5},
        {"drug_uptake": -0.5},
        {"max_time_min": 30.0},
        {"report_interval_min": 1.0},
        {"initial_cells": 0},
        {"initial_cells": 501},
        {"initial_cells": 12.5},
        # 10080/5 = 2016 frames, over the 500 cap
        {"max_time_min": 10080.0, "report_interval_min": 5.0},
    ]
    for params in bad:
        try:
            validate_params(params)
        except ValueError:
            pass
        else:
            raise AssertionError(f"out-of-range accepted: {params}")


def test_validate_rejects_nonfinite():
    for params in [{"oxygen": float("nan")}, {"oxygen": float("inf")},
                   {"drug_dose": float("-inf")}]:
        try:
            validate_params(params)
        except ValueError:
            pass
        else:
            raise AssertionError(f"non-finite accepted: {params}")


def test_run_rejects_before_solver_burn():
    adapter = PhysiCellAdapter()
    try:
        adapter.run({**adapter.default_params(), "cell_radius_um": 10.0}, 7)
    except ValueError as e:
        assert "not supported" in str(e), str(e)
    else:
        raise AssertionError("run() accepted cell_radius_um")
    try:
        adapter.run({**adapter.default_params(), "oxygen": 500.0}, 7)
    except ValueError as e:
        assert "out of range" in str(e), str(e)
    else:
        raise AssertionError("run() accepted oxygen=500")


def main() -> int:
    test_defaults_have_no_cell_radius()
    test_validate_accepts_defaults()
    test_validate_rejects_cell_radius()
    test_validate_rejects_out_of_range()
    test_validate_rejects_nonfinite()
    test_run_rejects_before_solver_burn()
    print("PASS test_param_guards (6 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
