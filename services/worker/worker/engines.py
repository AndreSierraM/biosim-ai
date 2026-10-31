"""Engine registry: manifests, defaults and run entry points."""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "packages" / "engine-reference"))

from adapter import ReferenceAdapter  # noqa: E402


class UnknownEngine(Exception):
    pass


class EngineNotAvailable(Exception):
    pass


@dataclass
class EngineHandle:
    engine_id: str
    manifest: dict
    available: bool
    reason: str = ""
    defaults: dict = field(default_factory=dict)
    _run: Callable | None = None
    _validate: Callable | None = None
    _param_specs: Callable | None = None

    def run(self, params: dict, seed: int) -> dict:
        if not self.available or self._run is None:
            raise EngineNotAvailable(self.reason or self.engine_id)
        return self._run({**self.defaults, **params}, seed)

    def validate(self, params: dict) -> None:
        """Server-side range guardrails; no-op when the engine has none."""
        if self._validate is not None:
            self._validate({**self.defaults, **params})

    def param_specs(self) -> dict:
        if self._param_specs is not None:
            return self._param_specs()
        return {}


def _reference_handle() -> EngineHandle:
    adapter = ReferenceAdapter()
    raw = json.loads(
        (_REPO / "packages" / "engine-reference" / "params" / "baseline.json").read_text()
    )
    raw.pop("seed", None)
    return EngineHandle("reference-2cell", adapter.manifest(), True, defaults=raw,
                        _run=adapter.run)


def _physicell_handle() -> EngineHandle:
    base = _REPO / "services" / "worker" / "engines" / "physicell"
    manifest_path = base / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {"engine_id": "physicell", "engine_version": "1.14.2"}
    )
    adapter_path = base / "adapter.py"
    binary = base / "vendor" / "project"
    if not adapter_path.exists():
        return EngineHandle("physicell", manifest, False,
                            reason="adapter not implemented yet")
    if not binary.exists():
        return EngineHandle("physicell", manifest, False,
                            reason="engine binary missing; run engines/physicell/setup.sh")
    spec = importlib.util.spec_from_file_location("physicell_adapter", adapter_path)
    if spec is None or spec.loader is None:
        return EngineHandle("physicell", manifest, False, reason="adapter unloadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter = module.PhysiCellAdapter()
    return EngineHandle("physicell", adapter.manifest(), True,
                        defaults=adapter.default_params(), _run=adapter.run,
                        _validate=adapter.validate,
                        _param_specs=adapter.param_specs)


def get_engine(engine_id: str) -> EngineHandle:
    if engine_id == "reference-2cell":
        return _reference_handle()
    if engine_id == "physicell":
        return _physicell_handle()
    raise UnknownEngine(f"unknown engine: {engine_id}")


def list_engines() -> list[EngineHandle]:
    return [get_engine(e) for e in ("reference-2cell", "physicell")]
