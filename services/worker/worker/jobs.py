"""Filesystem job store (hackathon simplification; PG/Redis post-competition)."""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl  # noqa: F401 - POSIX advisory locks (no-op fallback below)
    _HAS_FCNTL = True
except ImportError:  # Windows: threads-only locking
    _HAS_FCNTL = False

STATES = ("draft", "validated", "queued", "running", "completed", "failed", "cancelled")
TERMINAL_STATES = ("completed", "failed", "cancelled")

# One lock shared by every JobStore instance in this process: create/update
# and the idempotency reserve below are atomic across API threads.
_STORE_LOCK = threading.RLock()


class JobCancelled(Exception):
    """Raised inside a running engine when its job was cancelled."""


class KeyConflict(Exception):
    """Idempotency key already reserved for a different engine/params/seed."""

    def __init__(self, message: str, job: dict | None = None):
        super().__init__(message)
        self.job = job


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


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Crash-safe write: temp file + fsync + atomic rename, never a truncation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    with open(tmp, "w") as fh:
        fh.write(json.dumps(payload, separators=(",", ":")))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class JobStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

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
        with _STORE_LOCK:
            _atomic_write_json(self._path(job["id"]), job)
        return job

    def create_idempotent(self, engine: str, params: dict, seed: int, model_version=None,
                          idempotency_key: str | None = None,
                          provenance: dict | None = None) -> tuple[dict, bool]:
        """Atomic reserve: same check-and-create under one lock (no TOCTOU).

        Returns (job, deduplicated). Raises KeyConflict when the key is already
        reserved for a different engine/params/seed.
        """
        with _STORE_LOCK:
            if idempotency_key is not None:
                conflict = self.key_conflict(params, seed, engine, idempotency_key)
                if conflict is not None:
                    raise KeyConflict(
                        f"idempotency key already used for a different run "
                        f"({conflict['id']}: engine={conflict['engine']} "
                        f"seed={conflict['seed']})", conflict)
                existing = self.find_for_key(engine, params, seed, idempotency_key)
                if existing is not None:
                    return existing, True
            return self.create(engine, params, seed, model_version,
                               idempotency_key, provenance), False

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
        with _STORE_LOCK:
            job = self.get(job_id)
            if ("state" in fields and job.get("state") in TERMINAL_STATES
                    and fields["state"] != job["state"]):
                raise ValueError(
                    f"terminal job {job_id} is {job['state']}: "
                    f"refusing transition to {fields['state']}")
            job.update(fields)
            job["updated_at"] = _now()
            _atomic_write_json(self._path(job_id), job)
            return job

    def purge_expired(self, max_age_days: float) -> int:
        """Delete job dirs whose job.json mtime is older than the retention.

        Export first: only metadata+trajectory dirs go away; the digest in
        the export bundle stays verifiable elsewhere. Returns deleted count.
        """
        cutoff = time.time() - max_age_days * 86400
        deleted = 0
        with _STORE_LOCK:
            for meta in sorted(self.root.glob("*/job.json")):
                try:
                    if meta.stat().st_mtime < cutoff:
                        shutil.rmtree(meta.parent, ignore_errors=True)
                        deleted += 1
                except OSError:
                    continue
        return deleted

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
        # Compact on disk (~30% smaller); gunzip/gzip on the wire shrinks more.
        self.trajectory_path(job_id).write_text(
            json.dumps(artifact, separators=(",", ":")))

    def read_trajectory(self, job_id: str) -> dict:
        _validate_job_id(job_id)
        p = self.trajectory_path(job_id)
        if not p.exists():
            raise FileNotFoundError(job_id)
        return json.loads(p.read_text())
