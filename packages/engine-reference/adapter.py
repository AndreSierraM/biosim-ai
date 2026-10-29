"""Engine adapter boundary.

Every engine (reference scaffold today, PhysiCell in #8) implements
EngineAdapter: a manifest declaring fidelity/limits plus a run() entry
point returning a versioned artifact dict.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from solver import ENGINE_ID, ENGINE_VERSION, SolverParams, run


class EngineAdapter(Protocol):
    engine_id: str
    engine_version: str

    def manifest(self) -> dict: ...
    def run(self, params: dict, seed: int) -> dict: ...


class ReferenceAdapter:
    engine_id = ENGINE_ID
    engine_version = ENGINE_VERSION

    def manifest(self) -> dict:
        path = Path(__file__).parent / "manifest.json"
        return json.loads(path.read_text())

    def run(self, params: dict, seed: int) -> dict:
        return run(SolverParams(**params), seed)
