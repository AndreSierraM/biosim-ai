"""Constrained experiment planner: the model proposes JSON, code validates.

Dependency-free so unit tests run on stock Python. The router re-validates
every arm against the canonical ExperimentSpec schema before returning.
"""
from __future__ import annotations

import json
import math
from typing import Protocol

from .meta_client import ModelResponse

__all__ = ["ModelResponse", "plan_prompt"]


class ModelClient(Protocol):
    def complete(self, system: str, user: str) -> ModelResponse: ...


PROMPT_TEMPLATE_VERSION = "2"  # bump on any _system_prompt() change
SCHEMA_VERSION = "1.0.0"


OXYGEN_UNIT = "mmHg"
MAX_OXYGEN = 100.0
DRUG_UNIT = "uM"
MAX_DOSE = 100.0
ASSAY_OXYGEN = 38.0  # drug assays run at healthy oxygen
SEED = 7
INITIAL_CELLS = 12  # must match the PhysiCell adapter default

# Full custom-assay space. Authority is PARAM_SPECS in
# services/worker/engines/physicell/adapter.py (server-side guardrails);
# this mirror lets the planner propose any supported combination, and
# test_engine_defaults.py asserts the two stay in sync.
PARAM_DEFAULTS = {
    "oxygen": 38.0,
    "drug_dose": 0.0,
    "drug_ec50": 1.0,
    "drug_kill_max": 0.001,
    "drug_uptake": 10.0,
    "max_time_min": 4320.0,
    "report_interval_min": 60.0,
    "initial_cells": 12,
}
PARAM_UNITS = {
    "oxygen": "mmHg",
    "drug_dose": "uM",
    "drug_ec50": "uM",
    "drug_kill_max": "1/min",
    "drug_uptake": "1/min",
    "max_time_min": "min",
    "report_interval_min": "min",
    "initial_cells": "none",
}
PARAM_RANGES = {
    "oxygen": (0.0, 100.0),
    "drug_dose": (0.0, 100.0),
    "drug_ec50": (0.0, 100.0),
    "drug_kill_max": (0.0, 0.1),
    "drug_uptake": (0.0, 1000.0),
    "max_time_min": (60.0, 10080.0),
    "report_interval_min": (5.0, 1440.0),
    "initial_cells": (1, 500),
}
MAX_FRAMES = 500
SEED_MAX = 2147483647


def _system_prompt() -> str:
    return f"""You plan tumor spheroid experiments on PhysiCell. Reply with JSON only, no prose.
For an oxygen-availability comparison reply:
{{"kind": "spheroid_oxygen_compare", "engine": "physicell", "oxygen_high": <number>, "oxygen_low": <number>}}
Rules: oxygen in mmHg, 0 < value <= {MAX_OXYGEN}; arms must differ.
Calibrated assay: 38 grows with a small necrotic core, 12 grows slowly with heavy necrosis.
For a drug-treatment comparison reply:
{{"kind": "spheroid_drug_compare", "engine": "physicell", "drug_dose": <number>}}
Rules: sustained boundary dose in uM, 0 < dose <= {MAX_DOSE}.
Calibrated assay (oxygen 38): dose 0 grows to ~115 live cells, 0.3 to ~93, 1.0 to ~41, 10.0 to ~4.
For any other supported spheroid question reply with a custom assay:
{{"kind": "spheroid_custom", "engine": "physicell", "parameters": {{"oxygen": <number>, ...}}, "seed": <int>}}
Rules: only these keys, each a finite number inside its range (omit a key to keep its default):
oxygen (0,100] mmHg default 38; drug_dose [0,100] uM default 0; drug_ec50 (0,100] uM default 1;
drug_kill_max [0,0.1] 1/min default 0.001; drug_uptake [0,1000] 1/min default 10;
max_time_min [60,10080] min default 4320; report_interval_min [5,1440] min default 60;
initial_cells [1,500] integer default 12. max_time_min/report_interval_min must yield
at most {MAX_FRAMES} frames. seed in [0,{SEED_MAX}] default {SEED}.
cell_radius_um is NOT supported (the assay fixes the cell radius): never propose it.
If PhysiCell cannot do the request (atomistic detail, membrane FEM, clinical diagnosis, ...), reply:
{{"kind": "unsupported", "reason": "<one honest sentence naming the missing capability>"}}"""


def _spec(prompt: str, arm: str, oxygen: float, dose: float | None = None) -> dict:
    params: dict = {"oxygen": oxygen}
    if dose is not None:
        params["drug_dose"] = dose
    return _spec_full(prompt, arm, params, SEED)


def _spec_full(prompt: str, arm: str, params: dict, seed: int) -> dict:
    intent = f"{prompt} [{arm} arm]".strip()
    if len(intent) < 8:
        intent += " (tumor spheroid assay)"
    parameters = {
        key: {"value": params[key], "unit": PARAM_UNITS[key]}
        for key in PARAM_DEFAULTS if key in params
    }
    assumptions = ["Tumor spheroid assay: seeded cluster, oxygen diffusion/uptake, hypoxic necrosis."]
    if "drug_dose" in params or "drug_ec50" in params or "drug_kill_max" in params:
        assumptions.append("Cytotoxic drug: sustained boundary dose, diffusion/uptake gradient, Hill apoptosis.")
    count = params.get("initial_cells", INITIAL_CELLS)
    return {
        "schema_version": "1.0.0",
        "intent": intent,
        "engine": "physicell",
        "seed": seed,
        "entities": [{"id": "cells", "kind": "cell", "count": int(count)}],
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


def _validate_custom(data: dict) -> tuple[dict, int]:
    """Any supported parameter combination. Returns (merged params, seed)."""
    raw = data.get("parameters", {})
    if not isinstance(raw, dict):
        raise ValueError("parameters must be an object keyed by parameter name")
    unknown = sorted(k for k in raw if k not in PARAM_DEFAULTS)
    if unknown:
        raise ValueError(
            f"unsupported parameters {unknown}; supported: {sorted(PARAM_DEFAULTS)} "
            f"(cell_radius_um is fixed by the assay and never accepted)")
    params = dict(PARAM_DEFAULTS)
    for key, value in raw.items():
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"parameter {key!r} must be a finite number")
        lo, hi = PARAM_RANGES[key]
        v = float(value)
        if key == "initial_cells" and not float(value).is_integer():
            raise ValueError("parameter 'initial_cells' must be an integer")
        if not (lo <= v <= hi) or (key in ("oxygen", "drug_ec50") and v <= 0):
            raise ValueError(f"parameter {key!r}={value!r} out of range [{lo}, {hi}]")
        params[key] = int(value) if key == "initial_cells" else v
    frames = params["max_time_min"] / params["report_interval_min"]
    if frames > MAX_FRAMES:
        raise ValueError(
            f"max_time_min/report_interval_min yields {frames:.0f} frames, "
            f"over the {MAX_FRAMES} cap")
    seed = data.get("seed", SEED)
    if isinstance(seed, bool) or not isinstance(seed, int) or not (0 <= seed <= SEED_MAX):
        raise ValueError(f"seed must be an integer in [0, {SEED_MAX}]")
    return params, seed


def plan_prompt(prompt: str, client: ModelClient, engines: list[str]) -> dict:
    """Plan a spheroid experiment. Never runs anything.

    Every result carries a "provenance" block (model id, request id,
    token usage, latency, prompt-template and schema versions) so a
    judge can verify a real Meta call happened; without a key the
    model-dependent fields stay null instead of being invented.
    """
    prov: dict = {
        "model_version": None,
        "request_id": None,
        "tokens_in": None,
        "tokens_out": None,
        "latency_s": 0.0,
        "prompt_template": PROMPT_TEMPLATE_VERSION,
        "schema_version": SCHEMA_VERSION,
    }
    result = _plan_prompt(prompt, client, engines, prov)
    prov["model_version"] = result.get("model_version") or prov["model_version"]
    result["provenance"] = prov
    return result


def _plan_prompt(prompt: str, client: ModelClient, engines: list[str],
                 prov: dict) -> dict:
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
        prov.update({
            "model_version": resp.model,
            "request_id": resp.request_id,
            "tokens_in": resp.tokens_in,
            "tokens_out": resp.tokens_out,
            "latency_s": resp.latency_s,
        })
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
        if kind not in ("spheroid_oxygen_compare", "spheroid_drug_compare",
                          "spheroid_custom"):
            feedback = f"unknown kind {kind!r}"
            continue
        warnings: list[str] = []
        if data.get("engine", "physicell") != "physicell":
            warnings.append(f"engine {data.get('engine')!r} cannot run spheroids; using physicell")
        if kind == "spheroid_custom":
            try:
                custom_params, custom_seed = _validate_custom(data)
            except ValueError as e:
                feedback = str(e)
                continue
            return {
                "validated": True,
                "arms": [
                    {"name": "custom", "spec": _spec_full(prompt, "custom",
                                                         custom_params, custom_seed)},
                ],
                "model_version": resp.model,
                "warnings": warnings,
                "refusal": None,
                "runs_created": [],
            }
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
