"""POST /v1/plan: constrained AI planning endpoint."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import jsonschema
from fastapi import APIRouter, HTTPException

from .meta_client import KeyNotConfigured, MetaApiError, MetaModelClient, ModelResponse
from .planner import plan_prompt
from .validation import _schema

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "services" / "worker"))

from worker.engines import list_engines  # noqa: E402

router = APIRouter(prefix="/v1", tags=["plan"])


def planner_status() -> dict:
    """Honest planner backend without leaking secrets.

    fixture: BIOSIM_PLANNER_FIXTURE set (deterministic demo, no Meta call).
    live: META_MODEL_API_KEY set (real Meta Model API call).
    none: neither configured (planning unavailable).
    """
    import urllib.parse
    fixture = os.environ.get("BIOSIM_PLANNER_FIXTURE")
    if fixture:
        return {"backend": "fixture", "model": "planner-fixture",
                "endpoint_host": None, "fixture": fixture,
                "configured": True}
    key = os.environ.get("META_MODEL_API_KEY", "").strip()
    if key:
        endpoint = os.environ.get("META_MODEL_ENDPOINT",
                                   "https://api.meta.ai/v1").strip()
        try:
            host = urllib.parse.urlparse(endpoint).hostname
        except Exception:  # noqa: BLE001 - never fail status on bad endpoint
            host = None
        model = os.environ.get("META_MODEL_NAME", "muse-spark-1.3").strip()
        return {"backend": "live", "model": model or "muse-spark-1.3",
                "endpoint_host": host, "configured": True}
    return {"backend": "none", "model": None,
            "endpoint_host": None, "configured": False}


@router.get("/planner/status")
def get_planner_status():
    return planner_status()


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
        detail = f"planner model call failed: {e}"
        if e.status_code is not None:
            detail += f" (http {e.status_code})"
        if e.request_id:
            detail += f" (request {e.request_id})"
        raise HTTPException(504, detail)
    refusal = plan.get("refusal") or {}
    if using_meta and refusal.get("reason", "").startswith("model call failed:"):
        raise HTTPException(504, f"planner {refusal['reason']}")
    plan["planner_backend"] = "live" if using_meta else "fixture"
    if plan["validated"]:
        validator = jsonschema.Draft202012Validator(_schema())
        for arm in plan["arms"]:
            errors = list(validator.iter_errors(arm["spec"]))
            if errors:
                return {"validated": False, "arms": [], "model_version": plan["model_version"],
                        "warnings": plan["warnings"],
                        "planner_backend": plan["planner_backend"],
                        "refusal": {"reason": f"arm {arm['name']} failed schema: "
                                              f"{errors[0].message}"},
                        "runs_created": []}
    return plan
