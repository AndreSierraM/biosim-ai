"""Unit tests: engine defaults consistency. Run: python3 services/api/tests/test_engine_defaults.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "services" / "worker" / "engines" / "physicell"))

from app import planner

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


def main() -> int:
    if physicell_adapter is None:
        print(f"SKIP test_engine_defaults: adapter PhysiCell no importable: {_IMPORT_ERROR}")
        return 0
    test_planner_initial_cells_matches_physicell_default()
    print("PASS test_engine_defaults (1 test)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
