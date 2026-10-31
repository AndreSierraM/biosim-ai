"""API tests: run guardrails, dedupe and tools manifest.

Run: services/api/.venv/bin/python services/api/tests/test_runs_api.py
(needs the API venv: fastapi + scipy).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import HTTPException

from app import runs
from app.plan import create_plan
from app.tools import get_tools
from worker.jobs import JobStore


def _check_http(body: dict, want_code: int, want_text: str):
    try:
        runs.submit_run(body)
    except HTTPException as e:
        assert e.status_code == want_code, (e.status_code, e.detail)
        assert want_text in str(e.detail), e.detail
    else:
        raise AssertionError(f"expected HTTP {want_code} for {body}")


def test_rejects_unknown_param():
    _check_http({"engine": "reference-2cell", "params": {"nope": 1}, "seed": 7},
                400, "unknown params")


def test_rejects_out_of_range():
    _check_http({"engine": "physicell", "params": {"oxygen": 500.0}, "seed": 7},
                400, "out of range")


def test_rejects_cell_radius():
    _check_http({"engine": "physicell", "params": {"cell_radius_um": 10.0}, "seed": 7},
                400, "not supported")


def test_idempotent_submit_returns_same_job():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BIOSIM_RUNS_DIR"] = tmp
        try:
            store = JobStore(tmp)
            job = store.create("reference-2cell", {"adhesion": 6.0}, 7,
                               idempotency_key="abc")
            store.update(job["id"], state="completed")
            again = runs.submit_run(
                {"engine": "reference-2cell", "params": {"adhesion": 6.0},
                 "seed": 7, "idempotency_key": "abc"})
            assert again["id"] == job["id"], again
            assert again.get("deduplicated") is True, again
            assert len(list(Path(tmp).glob("*/job.json"))) == 1
        finally:
            os.environ.pop("BIOSIM_RUNS_DIR", None)


def test_submit_without_key_always_runs_fresh():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BIOSIM_RUNS_DIR"] = tmp
        try:
            store = JobStore(tmp)
            job = store.create("reference-2cell", {"adhesion": 6.0}, 7)
            store.update(job["id"], state="completed")
            fresh = runs.submit_run(
                {"engine": "reference-2cell", "params": {"adhesion": 6.0}, "seed": 7})
            assert fresh["id"] != job["id"], fresh
            assert fresh.get("deduplicated") is not True
            done = runs._FUTURES[fresh["id"]].result(timeout=120)
            assert done["state"] == "completed", done
        finally:
            os.environ.pop("BIOSIM_RUNS_DIR", None)


def test_idempotency_key_conflict_is_422():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["BIOSIM_RUNS_DIR"] = tmp
        try:
            JobStore(tmp).create("reference-2cell", {"adhesion": 6.0}, 7,
                                 idempotency_key="abc")
            _check_http({"engine": "reference-2cell", "params": {"adhesion": 9.0},
                         "seed": 7, "idempotency_key": "abc"},
                        422, "already used")
        finally:
            os.environ.pop("BIOSIM_RUNS_DIR", None)


def test_tools_manifest_lists_allowlist_and_ranges():
    manifest = get_tools()
    names = [t["name"] for t in manifest["tools"]]
    for need in ("list_capabilities", "propose_experiment", "validate_experiment",
                 "submit_simulation", "get_run_summary", "compare_runs"):
        assert need in names, names
    phys = next(e for e in manifest["engines"] if e["engine_id"] == "physicell")
    assert phys["available"] is True, phys
    assert phys["param_specs"]["oxygen"]["unit"] == "mmHg"
    assert "cell_radius_um" not in phys["param_specs"], phys["param_specs"]
    assert any("radius" in lim for lim in phys["limits"]), phys["limits"]


def test_plan_response_carries_provenance():
    repo = Path(__file__).parent.parent.parent.parent
    os.environ["BIOSIM_PLANNER_FIXTURE"] = str(
        repo / "services" / "api" / "tests" / "fixtures" / "acceptance.json")
    try:
        plan = create_plan({"prompt": "how does oxygen availability affect growth"})
    finally:
        os.environ.pop("BIOSIM_PLANNER_FIXTURE", None)
    assert plan["validated"] is True, plan
    assert plan["planner_backend"] == "fixture", plan
    prov = plan["provenance"]
    assert prov["model_version"] == "planner-fixture", prov
    assert prov["prompt_template"] and prov["schema_version"] == "1.0.0", prov
    assert prov["request_id"] is None and prov["tokens_in"] is None, prov


def test_planner_status_honest_backend():
    from app.plan import planner_status
    repo = Path(__file__).parent.parent.parent.parent
    old_fixture = os.environ.pop("BIOSIM_PLANNER_FIXTURE", None)
    old_key = os.environ.pop("META_MODEL_API_KEY", None)
    try:
        os.environ["BIOSIM_PLANNER_FIXTURE"] = str(
            repo / "services" / "api" / "tests" / "fixtures" / "acceptance.json")
        st = planner_status()
        assert st["backend"] == "fixture" and st["configured"] is True, st
        assert "KEY" not in json.dumps(st), st
        del os.environ["BIOSIM_PLANNER_FIXTURE"]
        os.environ["META_MODEL_API_KEY"] = "LLM|test-secret"
        st = planner_status()
        assert st["backend"] == "live" and st["model"] == "muse-spark-1.3", st
        assert "test-secret" not in json.dumps(st), st
        del os.environ["META_MODEL_API_KEY"]
        st = planner_status()
        assert st["backend"] == "none" and st["configured"] is False, st
    finally:
        if old_fixture is not None:
            os.environ["BIOSIM_PLANNER_FIXTURE"] = old_fixture
        else:
            os.environ.pop("BIOSIM_PLANNER_FIXTURE", None)
        if old_key is not None:
            os.environ["META_MODEL_API_KEY"] = old_key
        else:
            os.environ.pop("META_MODEL_API_KEY", None)


def main() -> int:
    test_rejects_unknown_param()
    test_rejects_out_of_range()
    test_rejects_cell_radius()
    test_idempotent_submit_returns_same_job()
    test_submit_without_key_always_runs_fresh()
    test_idempotency_key_conflict_is_422()
    test_tools_manifest_lists_allowlist_and_ranges()
    test_plan_response_carries_provenance()
    test_planner_status_honest_backend()
    print("PASS test_runs_api (9 tests)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
