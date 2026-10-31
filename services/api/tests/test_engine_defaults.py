"""Unit tests: engine defaults consistency. Run: python3 services/api/tests/test_engine_defaults.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "services" / "worker" / "engines" / "physicell"))

from app import planner  # noqa: E402

try:
    import adapter as physicell_adapter
except ImportError as exc:  # scipy ausente u otro problema de import
    physicell_adapter = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def test_planner_initial_cells_matches_physicell_default():
    """planner.INITIAL_CELLS debe coincidir con DEFAULTS['initial_cells'] del adapter PhysiCell."""
    if physicell_adapter is None:
        try:
            import pytest
        except ImportError:
            import unittest
            raise unittest.SkipTest(
                f"adapter PhysiCell no importable (scipy ausente?): {_IMPORT_ERROR}")
        pytest.skip(f"adapter PhysiCell no importable (scipy ausente?): {_IMPORT_ERROR}")
    assert planner.INITIAL_CELLS == physicell_adapter.DEFAULTS["initial_cells"], (
        f"planner.INITIAL_CELLS={planner.INITIAL_CELLS} != "
        f"adapter DEFAULTS['initial_cells']={physicell_adapter.DEFAULTS['initial_cells']}")


def test_planner_param_space_matches_adapter():
    """PARAM_DEFAULTS/RANGES/UNITS del planner deben coincidir con PARAM_SPECS del adapter."""
    if physicell_adapter is None:
        try:
            import pytest
        except ImportError:
            import unittest
            raise unittest.SkipTest(
                f"adapter PhysiCell no importable (scipy ausente?): {_IMPORT_ERROR}")
        pytest.skip(f"adapter PhysiCell no importable (scipy ausente?): {_IMPORT_ERROR}")
    assert planner.PARAM_DEFAULTS == physicell_adapter.DEFAULTS, (
        f"planner defaults divergen del adapter: {planner.PARAM_DEFAULTS} vs "
        f"{physicell_adapter.DEFAULTS}")
    specs = physicell_adapter.PARAM_SPECS
    assert sorted(planner.PARAM_RANGES) == sorted(specs), (
        f"planner ranges divergen del adapter: {sorted(planner.PARAM_RANGES)} vs "
        f"{sorted(specs)}")
    for key, (lo, hi) in planner.PARAM_RANGES.items():
        assert (lo, hi) == specs[key][:2], f"rango de {key} diverge del adapter"
        assert planner.PARAM_UNITS[key] == specs[key][2], f"unidad de {key} diverge"
    assert planner.MAX_FRAMES == physicell_adapter.MAX_FRAMES


def main() -> int:
    if physicell_adapter is None:
        print(f"SKIP test_engine_defaults: adapter PhysiCell no importable: {_IMPORT_ERROR}")
        return 0
    test_planner_initial_cells_matches_physicell_default()
    test_planner_param_space_matches_adapter()
    print("PASS test_engine_defaults (2 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
