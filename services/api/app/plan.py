"""POST /v1/plan: constrained AI planning endpoint."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import jsonschema
from fastapi import APIRouter, HTTPException

from .meta_client import KeyNotConfigured, MetaApiError, MetaModelClient
from .planner import ModelResponse, plan_prompt
from .validation import _schema

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "services" / "worker"))

from worker.engines import list_engines  # noqa: E402

router = APIRouter(prefix="/v1", tags=["plan"])


class FixtureClient:
    """Deterministic stand-in for the model (tests/demos without a key).

    Fixture file: {"<prompt substring>": "<model JSON reply>", ...}.
    """

    def __init__(self, path: str):
        p = Path(path)
        if not p.is_absolute() and not p.exists():
            p = _REPO / p
        if not p.exists():
            raise FileNotFoundError(f"planner fixture not found: {path}")
        routes = json.loads(p.read_text())
        if not isinstance(routes, dict):
            raise ValueError(f"planner fixture must be a JSON object: {path}")
        self.routes = routes

    def complete(self, system: str, user: str) -> ModelResponse:
        lowered = user.lower()
        for needle, reply in self.routes.items():
            if needle.lower() in lowered:
                return ModelResponse(text=reply, model="planner-fixture")
        return ModelResponse(
            text=json.dumps({"kind": "unsupported",
                             "reason": "no fixture matched this prompt"}),
            model="planner-fixture",
        )


@router.post("/plan")
def create_plan(body: dict):
    prompt = body.get("prompt", "")
    if not isinstance(prompt, str) or len(prompt.strip()) < 8:
        raise HTTPException(400, "prompt must be a string of at least 8 characters")
    engines = [h.engine_id for h in list_engines() if h.available]
    if not engines:
        raise HTTPException(503, "no engines available")
    fixture = os.environ.get("BIOSIM_PLANNER_FIXTURE")
    if fixture:
        try:
            client = FixtureClient(fixture)
        except (OSError, ValueError) as e:
            raise HTTPException(503, f"planner fixture unavailable: {e}")
    else:
        try:
            client = MetaModelClient()
        except KeyNotConfigured:
            raise HTTPException(503, "planner unavailable: set META_MODEL_API_KEY "
                                    "or BIOSIM_PLANNER_FIXTURE")
    using_meta = isinstance(client, MetaModelClient)
    try:
        plan = plan_prompt(prompt.strip(), client, engines)
    except MetaApiError as e:
        raise HTTPException(504, f"planner model call failed: {e}")
    refusal = plan.get("refusal") or {}
    if using_meta and refusal.get("reason", "").startswith("model call failed:"):
        raise HTTPException(504, f"planner {refusal['reason']}")
    if plan["validated"]:
        validator = jsonschema.Draft202012Validator(_schema())
        for arm in plan["arms"]:
            errors = list(validator.iter_errors(arm["spec"]))
            if errors:
                return {"validated": False, "arms": [], "model_version": plan["model_version"],
                        "warnings": plan["warnings"],
                        "refusal": {"reason": f"arm {arm['name']} failed schema: "
                                              f"{errors[0].message}"},
                        "runs_created": []}
    return plan
