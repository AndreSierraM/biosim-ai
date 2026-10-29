"""PhysiCell spheroid adapter: render config, run binary, parse MultiCellDS."""
from __future__ import annotations

import glob
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from scipy.io import loadmat

HERE = Path(__file__).parent
VENDOR = HERE / "vendor"
BINARY = VENDOR / "project"
CONFIG_TEMPLATE = HERE / "model" / "spheroid_settings.xml"

ENGINE_ID = "physicell"
ENGINE_VERSION = "1.14.2"
RUN_TIMEOUT_S = 540

DEFAULTS = {
    "oxygen": 38.0,
    "drug_dose": 0.0,
    "drug_ec50": 1.0,
    "drug_kill_max": 0.001,
    "drug_uptake": 10.0,
    "max_time_min": 4320.0,
    "report_interval_min": 60.0,
    "initial_cells": 12,
    "cell_radius_um": 10.0,
}


def _set_text(root: ET.Element, path: str, value) -> None:
    el = root.find(path)
    if el is None:
        raise RuntimeError(f"config template lacks {path}")
    el.text = str(value)


def _validate_finite(params: dict, seed: int) -> None:
    for key, value in params.items():
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            raise ValueError(f"param {key!r} must be finite, got {value!r}")
    if isinstance(seed, (int, float)) and not math.isfinite(float(seed)):
        raise ValueError(f"seed must be finite, got {seed!r}")


def _render_config(params: dict, seed: int, outdir: Path, dest: Path) -> None:
    _validate_finite(params, seed)
    tree = ET.parse(CONFIG_TEMPLATE)
    root = tree.getroot()
    _set_text(root, "./save/folder", str(outdir))
    _set_text(root, "./options/random_seed", seed)
    _set_text(root, "./overall/max_time", params["max_time_min"])
    _set_text(root, "./save/full_data/interval", params["report_interval_min"])
    for name, key in (("oxygen", "oxygen"), ("drug", "drug_dose")):
        base = f"./microenvironment_setup/variable[@name='{name}']"
        if root.find(base) is None:
            raise RuntimeError(f"config template lacks substrate {name}")
        _set_text(root, f"{base}/initial_condition", params[key])
        _set_text(root, f"{base}/Dirichlet_boundary_condition", params[key])
        for face in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"):
            el = root.find(
                f"{base}/Dirichlet_options/boundary_value[@ID='{face}']"
            )
            if el is None:
                raise RuntimeError(
                    f"config template lacks Dirichlet face {face} for {name}")
            el.text = str(params[key])
    _set_text(root, "./user_parameters/initial_cells", params["initial_cells"])
    _set_text(root, "./user_parameters/drug_ec50", params["drug_ec50"])
    _set_text(root, "./user_parameters/drug_kill_max", params["drug_kill_max"])
    _set_text(root, "./user_parameters/drug_uptake", params["drug_uptake"])
    tree.write(dest)


def _label_indices(root: ET.Element) -> tuple[int, int, int]:
    """Column indices for cell ID, position and dead flag."""
    labels = root.find(
        "./cellular_information/cell_populations/cell_population/custom/simplified_data/labels"
    )
    if labels is None:
        raise RuntimeError("report lacks simplified_data labels")
    idx = {lab.text.strip(): int(lab.get("index")) for lab in labels if lab.text}
    for need in ("ID", "position", "dead"):
        if need not in idx:
            raise RuntimeError(f"labels lack {need}: {sorted(idx)}")
    return idx["ID"], idx["position"], idx["dead"]


def _cells_filename(root: ET.Element) -> str:
    el = root.find(
        "./cellular_information/cell_populations/cell_population/custom/simplified_data/filename"
    )
    if el is None or not el.text:
        raise RuntimeError("report lacks simplified_data filename")
    return el.text.strip()


def _parse_reports(outdir: Path) -> list[dict]:
    files = sorted(glob.glob(str(outdir / "output*.xml")))
    if not files:
        raise RuntimeError(f"no PhysiCell reports in {outdir}")
    frames = []
    for path in files:
        root = ET.parse(path).getroot()
        t_el = root.find("./metadata/current_time")
        if t_el is None or t_el.text is None:
            raise RuntimeError(f"{path} lacks metadata/current_time")
        id_col, pos_col, dead_col = _label_indices(root)
        cells_path = Path(path).parent / _cells_filename(root)
        try:
            mat = loadmat(str(cells_path))["cells"]
        except KeyError as exc:
            raise RuntimeError(f"{path}: {cells_path} lacks 'cells' key") from exc
        except (FileNotFoundError, OSError, ValueError) as exc:
            raise RuntimeError(f"{path}: cannot load {cells_path}: {exc}") from exc
        rows = mat.T  # BioFVM writes (n_fields, n_cells)
        if rows.shape[1] <= max(id_col, pos_col + 2, dead_col):
            raise RuntimeError(f"{path}: cells matrix shape {mat.shape} too narrow")
        ids = [int(r[id_col]) for r in rows]
        if any(i < 0 for i in ids) or len(set(ids)) != len(ids):
            raise RuntimeError(f"{path}: insane cell IDs (misread matrix?)")
        cells = sorted(
            ({"id": f"cell-{int(r[id_col])}",
              "x_um": round(float(r[pos_col]), 6),
              "y_um": round(float(r[pos_col + 1]), 6),
              "z_um": round(float(r[pos_col + 2]), 6),
              "dead": bool(int(r[dead_col]))} for r in rows),
            key=lambda c: c["id"],
        )
        frames.append({"t_min": round(float(t_el.text), 6), "cells": cells})
    return frames


def _jobs():
    try:
        import worker.jobs as jobs
    except ImportError:
        return None
    return jobs


def _summarize(frames: list[dict]) -> dict:
    """Additive metric fields; tolerates any loader (path or package)."""
    try:
        from worker.metrics import summarize_frames
    except ImportError:
        import importlib.util

        path = HERE.parents[1] / "worker" / "metrics.py"
        spec = importlib.util.spec_from_file_location("worker_metrics", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        summarize_frames = module.summarize_frames
    return summarize_frames(frames)


def _current_cancelled() -> bool:
    jobs = _jobs()
    if jobs is None:
        return False
    try:
        job_id, store = jobs.current_job()
        if not job_id or store is None:
            return False
        return store.get(job_id)["state"] == "cancelled"
    except Exception:  # noqa: BLE001 - store hiccup means "not cancelled"
        return False


def _wait_cancellable(proc: subprocess.Popen, rundir: Path) -> tuple[str, str]:
    """Wait like subprocess.run(timeout=RUN_TIMEOUT_S) but abort on cancel."""
    jobs = _jobs()
    start = time.monotonic()
    while True:
        try:
            return proc.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            pass
        if _current_cancelled():
            proc.kill()
            proc.communicate()
            assert jobs is not None
            raise jobs.JobCancelled(f"PhysiCell run cancelled (see {rundir})")
        if time.monotonic() - start >= RUN_TIMEOUT_S:
            proc.kill()
            proc.communicate()
            raise RuntimeError(f"PhysiCell exceeded {RUN_TIMEOUT_S}s (see {rundir})")


def _radius_um(cells: list[dict]) -> float:
    n = len(cells)
    if n == 0:
        return 0.0
    cx = sum(c["x_um"] for c in cells) / n
    cy = sum(c["y_um"] for c in cells) / n
    cz = sum(c["z_um"] for c in cells) / n
    return max(math.dist((c["x_um"], c["y_um"], c["z_um"]), (cx, cy, cz)) for c in cells)


class PhysiCellAdapter:
    engine_id = ENGINE_ID
    engine_version = ENGINE_VERSION

    def manifest(self) -> dict:
        return json.loads((HERE / "manifest.json").read_text())

    def default_params(self) -> dict:
        return dict(DEFAULTS)

    def run(self, params: dict, seed: int) -> dict:
        if not BINARY.exists():
            raise RuntimeError("PhysiCell binary missing; run engines/physicell/setup.sh")
        missing = [k for k in DEFAULTS if k not in params]
        if missing:
            raise RuntimeError(f"missing params: {missing}")
        rundir = Path(tempfile.mkdtemp(prefix="physicell-run-"))
        try:
            outdir = rundir / "output"
            outdir.mkdir(parents=True, exist_ok=True)
            config = rundir / "config.xml"
            _render_config(params, seed, outdir, config)

            env = dict(os.environ, OMP_NUM_THREADS="1")
            proc = subprocess.Popen(
                [str(BINARY), str(config)], cwd=str(VENDOR), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            jobs = _jobs()
            job_id = jobs.current_job()[0] if jobs is not None else None
            if jobs is not None and job_id:
                jobs.register_proc(job_id, proc)
            try:
                out, err = _wait_cancellable(proc, rundir)
            finally:
                if jobs is not None and job_id:
                    jobs.unregister_proc(job_id)
            if proc.returncode != 0:
                tail = (out + err)[-2000:]
                raise RuntimeError(f"PhysiCell exit {proc.returncode} (see {rundir}):\n{tail}")

            frames = _parse_reports(outdir)
            live0 = sum(1 for c in frames[0]["cells"] if not c["dead"])
            live_n = sum(1 for c in frames[-1]["cells"] if not c["dead"])
            dead_n = sum(1 for c in frames[-1]["cells"] if c["dead"])
            return {
                "meta": {
                    "engine_id": ENGINE_ID,
                    "engine_version": ENGINE_VERSION,
                    "integrator": "physicell-1.14.2 (mechanics dt 0.1 min, single thread)",
                    "seed": seed,
                    "units": {"length": "um", "time": "min"},
                    "dt_min": 0.1,
                    "duration_min": params["max_time_min"],
                    "frame_every": params["report_interval_min"],
                    "params": dict(params),
                    "run_dir": str(rundir),
                    "assumptions": [
                        "Agent cells; no membrane deformation.",
                        "Oxygen-driven necrosis below 8 mmHg.",
                        "Drug: sustained boundary dose, diffusion/uptake gradient, "
                        "Hill apoptosis kill_max*dose/(dose+EC50) on all live cells.",
                        "Proliferation unscaled by oxygen (follow-up).",
                        "Single-threaded deterministic run.",
                    ],
                },
                "frames": frames,
                "summary": {
                    "n_frames": len(frames),
                    "initial_cells": live0,
                    "final_live": live_n,
                    "final_dead": dead_n,
                    "final_radius_um": round(_radius_um(frames[-1]["cells"]), 6),
                    **_summarize(frames),
                },
            }
        finally:
            if os.environ.get("BIOSIM_KEEP_RUNS") != "1":
                shutil.rmtree(rundir, ignore_errors=True)
