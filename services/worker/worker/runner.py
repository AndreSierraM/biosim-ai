"""Synchronous job execution (the API runs this in a thread pool)."""
from __future__ import annotations

import hashlib
import json

from .engines import get_engine
from .jobs import JobCancelled, JobStore, clear_current_job, set_current_job, unregister_proc


def _cancelled(store: JobStore, job_id: str) -> bool:
    try:
        return store.get(job_id)["state"] == "cancelled"
    except KeyError:
        return True


def execute(store: JobStore, job_id: str) -> dict:
    job = store.get(job_id)
    if job["state"] == "cancelled":
        return job
    store.update(job_id, state="running")
    set_current_job(job_id, store)
    try:
        if _cancelled(store, job_id):
            return store.get(job_id)
        handle = get_engine(job["engine"])
        artifact = handle.run(job["params"], job["seed"])
        if _cancelled(store, job_id):
            return store.get(job_id)
        store.write_trajectory(job_id, artifact)
        digest = hashlib.sha256(
            json.dumps(artifact, sort_keys=True).encode()
        ).hexdigest()
        return store.update(
            job_id,
            state="completed",
            summary=artifact["summary"],
            artifact_digest=f"sha256:{digest}",
            engine_version=handle.manifest["engine_version"],
        )
    except JobCancelled:
        return store.get(job_id)
    except Exception as e:  # noqa: BLE001 - worker must record failure, never crash
        if _cancelled(store, job_id):
            return store.get(job_id)
        return store.update(job_id, state="failed", error=f"{type(e).__name__}: {e}"[:500])
    finally:
        clear_current_job()
        unregister_proc(job_id)
