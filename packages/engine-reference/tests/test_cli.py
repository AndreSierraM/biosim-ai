"""CLI gate: --seed overrides the params-file seed without crashing.

Stdlib only. Run: python3 tests/test_cli.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent


def run_cli(params: dict, *extra: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        pf = Path(tmp) / "p.json"
        out = Path(tmp) / "traj.json"
        pf.write_text(json.dumps(params))
        r = subprocess.run(
            [sys.executable, str(ROOT / "cli.py"),
             "--params", str(pf), "--out", str(out), *extra],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, f"cli failed: {r.stderr.strip()}"
        return json.loads(out.read_text())


def main() -> int:
    base = json.loads((ROOT / "params" / "baseline.json").read_text())
    assert "seed" in base, "fixture must carry a seed to test the override"

    art = run_cli(base, "--seed", "123")
    assert art["meta"]["seed"] == 123, "flag seed was not used"

    art = run_cli(base)
    assert art["meta"]["seed"] == base["seed"], "file seed was not used"

    no_seed = dict(base)
    no_seed.pop("seed")
    art = run_cli(no_seed)
    assert art["meta"]["seed"] == 7, "default seed must be 7"

    print("PASS test_cli (--seed override, file seed, default seed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
