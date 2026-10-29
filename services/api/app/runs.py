"""Run submission, polling, trajectory, compare and bundle endpoints."""
from __future__ import annotations

import os
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, StrictInt, StrictStr, ValidationError

SEED_MIN = 0
SEED_MAX = 2**31 - 1


class RunSubmit(BaseModel):
    """Validated POST /v1/runs payload (all failures surface as 400)."""

    engine: StrictStr = Field(min_length=1)
    params: dict = Field(default_factory=dict)
    seed: StrictInt = Field(default=7, ge=SEED_MIN, le=SEED_MAX)


def _request_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "body"
        parts.append(f"{loc}: {err['msg']}")
    return "invalid run request: " + "; ".join(parts)


_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "services" / "worker"))

from worker.engines import EngineNotAvailable, UnknownEngine, get_engine, list_engines  # noqa: E402
from worker.jobs import JobStore, kill_proc  # noqa: E402
from worker.runner import execute  # noqa: E402

router = APIRouter(prefix="/v1/runs", tags=["runs"])
engines_router = APIRouter(tags=["engines"])

_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="biosim-run")
_FUTURES: dict[str, Future] = {}
_FUTURES_LOCK = threading.Lock()


def _store() -> JobStore:
    return JobStore(os.environ.get("BIOSIM_RUNS_DIR", str(_REPO / "artifacts" / "runs")))


@router.post("")
def submit_run(body: dict):
    try:
        req = RunSubmit.model_validate(body)
    except ValidationError as e:
        raise HTTPException(400, _request_error(e))
    try:
        handle = get_engine(req.engine)
    except UnknownEngine as e:
        raise HTTPException(400, str(e))
    if not handle.available:
        raise HTTPException(503, handle.reason or f"engine {req.engine} unavailable")
    unknown = sorted(k for k in req.params if k not in handle.defaults)
    if unknown:
        raise HTTPException(
            400,
            f"unknown params for engine {req.engine}: {unknown}; "
            f"known: {sorted(handle.defaults)}",
        )
    store = _store()
    job = store.create(req.engine, req.params, req.seed)
    fut = _POOL.submit(execute, store, job["id"])
    with _FUTURES_LOCK:
        _FUTURES[job["id"]] = fut
    return job


@router.get("")
def list_runs():
    return {"runs": _store().list()}


@router.get("/{job_id}")
def get_run(job_id: str):
    try:
        return _store().get(job_id)
    except KeyError:
        raise HTTPException(404, "unknown run")


@router.delete("/{job_id}")
def cancel_run(job_id: str):
    store = _store()
    try:
        job = store.get(job_id)
    except KeyError:
        raise HTTPException(404, "unknown run")
    if job["state"] in ("completed", "failed", "cancelled"):
        return job
    job = store.update(job_id, state="cancelled")
    with _FUTURES_LOCK:
        fut = _FUTURES.pop(job_id, None)
    if fut is not None:
        fut.cancel()
    kill_proc(job_id)
    return job


def _ready_trajectory(job_id: str) -> dict:
    try:
        job = _store().get(job_id)
    except KeyError:
        raise HTTPException(404, "unknown run")
    if job["state"] != "completed":
        raise HTTPException(409, f"run is {job['state']}")
    try:
        return _store().read_trajectory(job_id)
    except FileNotFoundError:
        raise HTTPException(409, "run has no artifact yet")


@router.get("/{job_id}/trajectory")
def get_trajectory(job_id: str):
    return _ready_trajectory(job_id)


@router.get("/{job_id}/bundle")
def get_bundle(job_id: str):
    try:
        job = _store().get(job_id)
    except KeyError:
        raise HTTPException(404, "unknown run")
    if job["state"] != "completed":
        raise HTTPException(409, f"run is {job['state']}")
    return {
        "engine": job["engine"],
        "engine_version": job["engine_version"],
        "params": job["params"],
        "seed": job["seed"],
        "model_version": job["model_version"],
        "artifact_digest": job["artifact_digest"],
    }


@router.post("/compare")
def compare_runs(body: dict, include_frames: bool = True):
    a = _ready_trajectory(body.get("run_a", ""))
    b = _ready_trajectory(body.get("run_b", ""))
    if not include_frames:
        return {
            "run_a": {"summary": a["summary"]},
            "run_b": {"summary": b["summary"]},
        }
    return {
        "run_a": {"frames": a["frames"], "summary": a["summary"]},
        "run_b": {"frames": b["frames"], "summary": b["summary"]},
    }


@engines_router.get("/v1/engines")
def get_engines():
    return {
        "engines": [
            {
                "engine_id": h.engine_id,
                "engine_version": h.manifest.get("engine_version"),
                "available": h.available,
                "reason": h.reason,
            }
            for h in list_engines()
        ]
    }
