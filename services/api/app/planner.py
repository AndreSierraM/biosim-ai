"""Constrained experiment planner: the model proposes JSON, code validates.

Dependency-free so unit tests run on stock Python. The router re-validates
every arm against the canonical ExperimentSpec schema before returning.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ModelResponse:
    text: str
    model: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_s: float = 0.0


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> ModelResponse: ...


OXYGEN_UNIT = "mmHg"
MAX_OXYGEN = 100.0
DRUG_UNIT = "uM"
MAX_DOSE = 100.0
ASSAY_OXYGEN = 38.0  # drug assays run at healthy oxygen
SEED = 7
INITIAL_CELLS = 12  # must match the PhysiCell adapter default


def _system_prompt() -> str:
    return f"""You plan tumor spheroid experiments on PhysiCell. Reply with JSON only, no prose.
For an oxygen-availability comparison reply:
{{"kind": "spheroid_oxygen_compare", "engine": "physicell", "oxygen_high": <number>, "oxygen_low": <number>}}
Rules: oxygen in mmHg, 0 < value <= {MAX_OXYGEN}; arms must differ.
Calibrated assay: 38 grows with a small necrotic core, 12 grows slowly with heavy necrosis.
For a drug-treatment comparison reply:
{{"kind": "spheroid_drug_compare", "engine": "physicell", "drug_dose": <number>}}
Rules: sustained boundary dose in uM, 0 < dose <= {MAX_DOSE}.
Calibrated assay (oxygen 38): dose 0 grows to ~137 live cells, 0.3 to ~87, 1.0 to ~22, 10.0 to ~2.
If PhysiCell cannot do the request (atomistic detail, membrane FEM, clinical diagnosis, ...), reply:
{{"kind": "unsupported", "reason": "<one honest sentence naming the missing capability>"}}"""


def _spec(prompt: str, arm: str, oxygen: float, dose: float | None = None) -> dict:
    intent = f"{prompt} [{arm} arm]".strip()
    if len(intent) < 8:
        intent += " (tumor spheroid assay)"
    parameters = {
        "oxygen": {"value": oxygen, "unit": OXYGEN_UNIT},
    }
    assumptions = ["Tumor spheroid assay: seeded cluster, oxygen diffusion/uptake, hypoxic necrosis."]
    if dose is not None:
        parameters["drug_dose"] = {"value": dose, "unit": DRUG_UNIT}
        assumptions.append("Cytotoxic drug: sustained boundary dose, diffusion/uptake gradient, Hill apoptosis.")
    return {
        "schema_version": "1.0.0",
        "intent": intent,
        "engine": "physicell",
        "seed": SEED,
        "entities": [{"id": "cells", "kind": "cell", "count": INITIAL_CELLS}],
        "parameters": parameters,
        "outputs": ["positions", "cell_counts", "time_series"],
        "assumptions": assumptions,
    }


def _validate_numbers(data: dict) -> tuple[float, float]:
    try:
        high = float(data["oxygen_high"])
        low = float(data["oxygen_low"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("oxygen_high and oxygen_low must be numbers")
    for v in (high, low):
        if not math.isfinite(v) or not (0 < v <= MAX_OXYGEN):
            raise ValueError(f"oxygen {v} out of range (0, {MAX_OXYGEN}]")
    if high == low:
        raise ValueError("arms must differ in oxygen")
    return high, low


def _validate_dose(data: dict) -> float:
    try:
        dose = float(data["drug_dose"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("drug_dose must be a number")
    if not math.isfinite(dose) or not (0 < dose <= MAX_DOSE):
        raise ValueError(f"drug_dose {dose} out of range (0, {MAX_DOSE}]")
    return dose


def plan_prompt(prompt: str, client: ModelClient, engines: list[str]) -> dict:
    """Plan a two-arm spheroid experiment. Never runs anything."""
    if "physicell" not in engines:
        return {"validated": False, "arms": [], "model_version": None, "warnings": [],
                "refusal": {"reason": "spheroid assay needs the PhysiCell engine "
                                      "(run services/worker/engines/physicell/setup.sh)"},
                "runs_created": []}
    feedback = ""
    last_model = "unknown"
    for _ in range(2):  # first attempt + one repair
        user_msg = f"Request: {prompt}\nRespond with JSON only."
        if feedback:
            user_msg += f"\nPrevious attempt failed validation: {feedback}. Fix it."
        try:
            resp = client.complete(_system_prompt(), user_msg)
        except Exception as e:  # noqa: BLE001 - provider errors become honest refusals
            return {"validated": False, "arms": [], "model_version": last_model,
                    "warnings": [], "refusal": {"reason": f"model call failed: {e}"},
                    "runs_created": []}
        last_model = resp.model
        try:
            data = json.loads(resp.text)
        except (json.JSONDecodeError, TypeError):
            feedback = "reply was not valid JSON"
            continue
        if not isinstance(data, dict):
            feedback = "reply must be a JSON object"
            continue
        kind = data.get("kind")
        if kind == "unsupported":
            return {"validated": False, "arms": [], "model_version": resp.model,
                    "warnings": [],
                    "refusal": {"reason": data.get("reason") or "request is not supported"},
                    "runs_created": []}
        if kind not in ("spheroid_oxygen_compare", "spheroid_drug_compare"):
            feedback = f"unknown kind {kind!r}"
            continue
        warnings: list[str] = []
        if data.get("engine", "physicell") != "physicell":
            warnings.append(f"engine {data.get('engine')!r} cannot run spheroids; using physicell")
        if kind == "spheroid_drug_compare":
            try:
                dose = _validate_dose(data)
            except ValueError as e:
                feedback = str(e)
                continue
            return {
                "validated": True,
                "arms": [
                    {"name": "control", "spec": _spec(prompt, "control", ASSAY_OXYGEN, 0.0)},
                    {"name": "treated", "spec": _spec(prompt, "treated", ASSAY_OXYGEN, dose)},
                ],
                "model_version": resp.model,
                "warnings": warnings,
                "refusal": None,
                "runs_created": [],
            }
        try:
            high, low = _validate_numbers(data)
        except ValueError as e:
            feedback = str(e)
            continue
        if high < low:
            high, low = low, high
            warnings.append("oxygen arms swapped into high/low order")
        return {
            "validated": True,
            "arms": [
                {"name": "normal-oxygen", "spec": _spec(prompt, "normal-oxygen", high)},
                {"name": "low-oxygen", "spec": _spec(prompt, "low-oxygen", low)},
            ],
            "model_version": resp.model,
            "warnings": warnings,
            "refusal": None,
            "runs_created": [],
        }
    return {"validated": False, "arms": [], "model_version": last_model, "warnings": [],
            "refusal": {"reason": f"planner could not produce valid parameters: {feedback}"},
            "runs_created": []}
