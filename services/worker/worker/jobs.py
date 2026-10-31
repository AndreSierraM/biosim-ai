"""Filesystem job store (hackathon simplification; PG/Redis post-competition)."""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATES = ("draft", "validated", "queued", "running", "completed", "failed", "cancelled")


class JobCancelled(Exception):
    """Raised inside a running engine when its job was cancelled."""


_CTX = threading.local()

_PROCS: dict[str, Any] = {}
_PROCS_LOCK = threading.Lock()


def set_current_job(job_id: str, store: Any = None) -> None:
    _CTX.job_id = job_id
    _CTX.store = store


def clear_current_job() -> None:
    _CTX.job_id = None
    _CTX.store = None


def current_job() -> tuple[str | None, Any]:
    return getattr(_CTX, "job_id", None), getattr(_CTX, "store", None)


def register_proc(job_id: str, proc: Any) -> None:
    with _PROCS_LOCK:
        _PROCS[job_id] = proc


def unregister_proc(job_id: str) -> None:
    with _PROCS_LOCK:
        _PROCS.pop(job_id, None)


def get_proc(job_id: str) -> Any | None:
    with _PROCS_LOCK:
        return _PROCS.get(job_id)


def kill_proc(job_id: str) -> bool:
    proc = get_proc(job_id)
    if proc is None:
        return False
    try:
        proc.kill()
    except Exception:  # noqa: BLE001 - already exited or zombie
        return False
    return True

_JOB_ID_RE = re.compile(r"^[0-9a-f]{12}$")


def _validate_job_id(job_id: str) -> str:
    if not isinstance(job_id, str) or not _JOB_ID_RE.match(job_id):
        raise KeyError(job_id)
    return job_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id: str) -> Path:
        _validate_job_id(job_id)
        return self.root / job_id / "job.json"

    def create(self, engine: str, params: dict, seed: int, model_version=None,
               idempotency_key: str | None = None, provenance: dict | None = None) -> dict:
        if not isinstance(params, dict):
            raise TypeError("params must be a dict")
        job = {
            "id": uuid.uuid4().hex[:12],
            "engine": engine,
            "params": params,
            "seed": seed,
            "model_version": model_version,
            "idempotency_key": idempotency_key,
            "provenance": provenance,
            "state": "queued",
            "created_at": _now(),
            "updated_at": _now(),
            "error": None,
            "summary": None,
            "artifact_digest": None,
            "engine_version": None,
        }
        p = self._path(job["id"])
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(job, indent=1))
        return job

    def get(self, job_id: str) -> dict:
        _validate_job_id(job_id)
        p = self._path(job_id)
        if not p.exists():
            raise KeyError(job_id)
        return json.loads(p.read_text())

    def update(self, job_id: str, **fields) -> dict:
        _validate_job_id(job_id)
        if "state" in fields and fields["state"] not in STATES:
            raise ValueError(f"bad state {fields['state']}")
        with self._lock:
            job = self.get(job_id)
            job.update(fields)
            job["updated_at"] = _now()
            self._path(job_id).write_text(json.dumps(job, indent=1))
            return job

    def list(self) -> list[dict]:
        jobs = [json.loads(p.read_text()) for p in sorted(self.root.glob("*/job.json"))]
        jobs.sort(key=lambda j: j["created_at"])
        return jobs

    def find_for_key(self, engine: str, params: dict, seed: int,
                     idempotency_key: str) -> dict | None:
        """Newest non-failed job with identical key+engine+params+seed, if any.

        Powers idempotent submit: retrying with the same key returns the
        existing job instead of burning solver time. Without a key every
        submit creates a fresh run (reproducibility proofs stay honest).
        """
        best: dict | None = None
        for job in self.list():
            if (job.get("state") not in ("failed",)
                    and job.get("idempotency_key") == idempotency_key
                    and job.get("engine") == engine
                    and job.get("seed") == seed
                    and job.get("params") == params):
                if best is None or job["created_at"] > best["created_at"]:
                    best = job
        return best

    def key_conflict(self, params: dict, seed: int, engine: str,
                     idempotency_key: str) -> dict | None:
        """A job reusing the key for different engine/params/seed, if any."""
        for job in self.list():
            if (job.get("idempotency_key") == idempotency_key
                    and (job.get("engine") != engine
                         or job.get("seed") != seed
                         or job.get("params") != params)):
                return job
        return None

    def trajectory_path(self, job_id: str) -> Path:
        _validate_job_id(job_id)
        return self.root / job_id / "trajectory.json"

    def write_trajectory(self, job_id: str, artifact: dict):
        _validate_job_id(job_id)
        self.trajectory_path(job_id).write_text(json.dumps(artifact, indent=1))

    def read_trajectory(self, job_id: str) -> dict:
        _validate_job_id(job_id)
        p = self.trajectory_path(job_id)
        if not p.exists():
            raise FileNotFoundError(job_id)
        return json.loads(p.read_text())
