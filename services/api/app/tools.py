"""GET /v1/tools: allowlisted tool manifest for the AI planner.

The model is a planner, never a solver: it may only use the six tools
below, and every invocation is authorized server-side by the dedicated
endpoint (no shell, no eval, no arbitrary paths or code).
"""
from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "services" / "worker"))

from worker.engines import list_engines  # noqa: E402

router = APIRouter(prefix="/v1", tags=["tools"])

TOOLS = [
    {
        "name": "list_capabilities",
        "endpoint": "GET /v1/tools",
        "description": "Discover engines, their parameter ranges with units, "
                       "observables and honest limits. Call this before "
                       "planning anything unfamiliar.",
    },
    {
        "name": "propose_experiment",
        "endpoint": "POST /v1/plan",
        "description": "Turn a plain-language question into validated "
                       "ExperimentSpec arms (or an honest refusal). Planning "
                       "never runs anything.",
        "input": {"prompt": "string, at least 8 characters"},
    },
    {
        "name": "validate_experiment",
        "endpoint": "POST /v1/specs/validate",
        "description": "Check an ExperimentSpec against the canonical schema "
                       "before running it.",
    },
    {
        "name": "submit_simulation",
        "endpoint": "POST /v1/runs",
        "description": "Run validated parameters on a scientific engine. "
                       "Pass idempotency_key to make retries free: the same "
                       "key+engine+params+seed returns the existing job "
                       "(deduplicated: true) instead of burning solver time. "
                       "Without a key every submit runs fresh.",
        "input": {"engine": "string", "params": "object", "seed": "int",
                  "idempotency_key": "optional string"},
    },
    {
        "name": "get_run_summary",
        "endpoint": "GET /v1/runs/{job_id} + /trajectory + /bundle",
        "description": "Poll run state, read measured trajectory frames and "
                       "the reproducibility bundle. Explain only measured "
                       "outputs, never invented ones.",
    },
    {
        "name": "compare_runs",
        "endpoint": "POST /v1/runs/compare",
        "description": "Side-by-side measured frames and summaries of two "
                       "completed runs.",
        "input": {"run_a": "job id", "run_b": "job id"},
    },
]


@router.get("/tools")
def get_tools():
    engines = []
    for h in list_engines():
        engines.append({
            "engine_id": h.engine_id,
            "engine_version": h.manifest.get("engine_version"),
            "available": h.available,
            "reason": h.reason,
            "display_name": h.manifest.get("display_name"),
            "fidelity": h.manifest.get("fidelity"),
            "observables": h.manifest.get("observables", []),
            "limits": h.manifest.get("limits", []),
            "defaults": h.defaults if h.available else {},
            "param_specs": h.param_specs() if h.available else {},
        })
    return {"tools": TOOLS, "engines": engines}
