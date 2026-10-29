"""Unit tests: job runner with the reference engine. Run: python3 services/worker/tests/test_runner.py"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from worker.jobs import JobStore
from worker.runner import execute


def test_reference_run_completes():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job = store.create("reference-2cell", {"adhesion": 6.0}, 7)
        final = execute(store, job["id"])
        assert final["state"] == "completed", f"ended {final['state']}: {final.get('error')}"
        traj = store.read_trajectory(job["id"])
        assert len(traj["frames"]) == 201
        assert traj["meta"]["params"]["adhesion"] == 6.0
        assert final["summary"]["contact_duration_min"] > 0
        assert final["artifact_digest"]


def test_unknown_engine_fails_cleanly():
    with tempfile.TemporaryDirectory() as tmp:
        store = JobStore(tmp)
        job = store.create("nope-engine", {}, 7)
        final = execute(store, job["id"])
        assert final["state"] == "failed"
        assert "nope-engine" in (final["error"] or "")


def main() -> int:
    test_reference_run_completes()
    test_unknown_engine_fails_cleanly()
    print("PASS test_runner (2 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
