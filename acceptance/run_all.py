"""Acceptance runner: boots a throwaway API, executes scenarios, reports.

Usage: python3 -m acceptance.run_all [001] [003]  (optional spec filters)
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API_URL = "http://127.0.0.1:8123"


def _wait_healthy(proc: subprocess.Popen, timeout_s: int = 60):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            raise RuntimeError(f"API exited during boot:\n{out[-2000:]}")
        try:
            with urllib.request.urlopen(API_URL + "/health", timeout=2) as res:
                if res.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("API did not become healthy in time")


def main() -> int:
    filters = sys.argv[1:]
    venv_python = ROOT / "services" / "api" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        print("missing services/api/.venv — see services/api/README.md", file=sys.stderr)
        return 2

    runs_dir = tempfile.mkdtemp(prefix="biosim-accept-")
    env = dict(os.environ, BIOSIM_RUNS_DIR=runs_dir, BIOSIM_API_URL=API_URL)
    proc = subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "app.main:app", "--port", "8123"],
        cwd=str(ROOT / "services" / "api"),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False,
    )
    try:
        _wait_healthy(proc)
        os.environ["BIOSIM_API_URL"] = API_URL
        from .scenarios import ENGINE, SCENARIOS

        print(f"engine under test: {ENGINE}  runs_dir: {runs_dir}")
        failures = 0
        for spec, name, func in SCENARIOS:
            if filters and not any(f in spec for f in filters):
                continue
            try:
                func()
                print(f"PASS {spec} :: {name}")
            except Exception as e:  # noqa: BLE001 - report any scenario failure
                failures += 1
                print(f"FAIL {spec} :: {name}\n     {type(e).__name__}: {e}")
        print(f"{'ALL PASS' if not failures else f'{failures} FAILURES'}")
        return 1 if failures else 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
