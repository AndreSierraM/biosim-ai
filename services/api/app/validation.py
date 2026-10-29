"""ExperimentSpec validation against the canonical JSON Schema."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import jsonschema
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/specs", tags=["specs"])


class ValidationResult(BaseModel):
    valid: bool
    errors: list[str] = []


@lru_cache(maxsize=1)
def _schema() -> dict:
    path = (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "experiment-schema"
        / "experiment.schema.json"
    )
    return json.loads(path.read_text())


@router.post("/validate", response_model=ValidationResult)
def validate_spec(spec: dict) -> ValidationResult:
    validator = jsonschema.Draft202012Validator(_schema())
    errors = sorted(validator.iter_errors(spec), key=lambda e: list(e.path))
    return ValidationResult(
        valid=not errors,
        errors=[f"$/{'/'.join(map(str, e.path))}: {e.message}" for e in errors],
    )
