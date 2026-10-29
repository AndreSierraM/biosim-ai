"""Scenario handlers: each maps 1:1 to a spec.md scenario.

The product suite targets the PhysiCell spheroid assay. The reference
engine is dev scaffolding covered by its own unit tests, not by 001-004.
"""
from __future__ import annotations

import json
import math
import os
import time

from . import http

ENGINE = os.environ.get("BIOSIM_ACCEPT_ENGINE", "physicell")
OXYGEN_HIGH = float(os.environ.get("BIOSIM_OXYGEN_HIGH", 38.0))
OXYGEN_LOW = float(os.environ.get("BIOSIM_OXYGEN_LOW", 12.0))
POLL_TIMEOUT_S = 600


def _submit(engine: str, params: dict, seed: int) -> dict:
    return http.post("/v1/runs", {"engine": engine, "params": params, "seed": seed})


def _wait(job_id: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT_S
    while True:
        job = http.get(f"/v1/runs/{job_id}")
        if job["state"] in ("completed", "failed", "cancelled"):
            return job
        if time.time() > deadline:
            raise AssertionError(f"run {job_id} stuck in {job['state']}")
        time.sleep(2)


def _submit_and_wait(params: dict, seed: int = 7, engine: str = ENGINE) -> dict:
    job = _submit(engine, params, seed)
    final = _wait(job["id"])
    if final["state"] != "completed":
        raise AssertionError(f"run {job['id']} ended {final['state']}: {final.get('error')}")
    return final


def _trajectory(job_id: str) -> dict:
    return http.get(f"/v1/runs/{job_id}/trajectory")


def _live_dead(frame: dict) -> tuple[int, int]:
    live = sum(1 for c in frame["cells"] if not c.get("dead"))
    return live, len(frame["cells"]) - live


# --- 001: real tumor spheroid growth --------------------------------------


def s001_spheroid_grows_with_necrotic_core():
    job = _submit_and_wait({"oxygen": OXYGEN_HIGH})
    traj = _trajectory(job["id"])
    assert traj["frames"], "no frames computed"
    for f in traj["frames"]:
        assert f["cells"], "empty frame computed"
        for c in f["cells"]:
            assert all(math.isfinite(c[k]) for k in ("x_um", "y_um", "z_um")), \
                "non-finite position computed"
    summary = traj["summary"]
    assert summary["final_live"] > summary["initial_cells"], \
        f"no proliferation: {summary}"
    assert summary["final_dead"] > 0, f"no necrotic core: {summary}"


def s001_low_oxygen_hurts_growth():
    high = _submit_and_wait({"oxygen": OXYGEN_HIGH})
    low = _submit_and_wait({"oxygen": OXYGEN_LOW})
    sh = _trajectory(high["id"])["summary"]
    sl = _trajectory(low["id"])["summary"]
    assert sl["final_live"] < sh["final_live"], \
        f"low oxygen did not reduce growth: {sl} vs {sh}"
    assert sl["final_dead"] > sh["final_dead"], \
        f"low oxygen did not kill more: {sl} vs {sh}"


def s001_rerun_reproduces():
    a = _submit_and_wait({"oxygen": OXYGEN_HIGH}, seed=7)
    b = _submit_and_wait({"oxygen": OXYGEN_HIGH}, seed=7)
    fa = _trajectory(a["id"])["frames"]
    fb = _trajectory(b["id"])["frames"]
    assert json.dumps(fa, sort_keys=True) == json.dumps(fb, sort_keys=True), \
        "same seed produced different trajectories"


# --- 002: AI-planned experiment --------------------------------------------


def _quantities_have_units(spec: dict):
    for name, q in spec["parameters"].items():
        assert isinstance(q.get("unit"), str) and q["unit"], \
            f"quantity {name} lacks explicit units"


def s002_plan_from_prompt():
    plan = http.post("/v1/plan", {
        "prompt": "how does oxygen availability affect tumor spheroid growth",
    })
    assert plan.get("validated") is True, f"plan not validated: {plan}"
    assert plan.get("runs_created") == [], "planning must not run anything"
    arms = plan["arms"]
    assert [a["name"] for a in arms] == ["normal-oxygen", "low-oxygen"], plan
    oxygens = []
    for arm in arms:
        assert arm["spec"]["engine"] == "physicell", \
            f"plan names no scientific engine: {arm['spec']}"
        _quantities_have_units(arm["spec"])
        oxygens.append(arm["spec"]["parameters"]["oxygen"]["value"])
    assert oxygens[0] != oxygens[1], "arms do not vary oxygen"


def s002_refuse_impossible():
    plan = http.post("/v1/plan", {
        "prompt": "show me atom-level detail of a whole living cell",
    })
    assert plan.get("validated") is False, f"impossible plan validated: {plan}"
    assert not plan.get("runs_created"), "refused plan created runs"
    assert plan.get("refusal", {}).get("reason"), "refusal lacks a reason"


# --- 003: compare runs and rerun with edits --------------------------------


def s003_compare_side_by_side():
    a = _submit_and_wait({"oxygen": OXYGEN_HIGH})
    b = _submit_and_wait({"oxygen": OXYGEN_LOW})
    cmp = http.post("/v1/runs/compare", {"run_a": a["id"], "run_b": b["id"]})
    for key in ("run_a", "run_b"):
        frames = cmp[key]["frames"]
        assert frames and frames[0]["cells"], f"{key} lacks trajectories"
        assert math.isfinite(cmp[key]["summary"]["final_live"]), \
            f"{key} lacks living-cell count"


def s003_rerun_keeps_original():
    a = _submit_and_wait({"oxygen": OXYGEN_HIGH})
    before = http.get(f"/v1/runs/{a['id']}")
    b = _submit_and_wait({"oxygen": OXYGEN_LOW})
    assert b["id"] != a["id"], "rerun reused the original id"
    after = http.get(f"/v1/runs/{a['id']}")
    assert after["params"] == before["params"], "original run was mutated"
    edited = _trajectory(b["id"])["meta"]["params"]["oxygen"]
    assert edited == OXYGEN_LOW, f"rerun ignored the edit: {edited}"


# --- 005: drug dose-response ------------------------------------------------

DOSE_LADDER = (0.0, 1.0, 10.0)


def s005_doses_decrease_monotonically():
    lives = []
    for dose in DOSE_LADDER:
        job = _submit_and_wait({"oxygen": OXYGEN_HIGH, "drug_dose": dose})
        lives.append(_trajectory(job["id"])["summary"]["final_live"])
    assert lives[0] > lives[1] > lives[2], \
        f"live counts not strictly decreasing with dose: {list(zip(DOSE_LADDER, lives))}"


def s005_high_dose_kills_most():
    control = _submit_and_wait({"oxygen": OXYGEN_HIGH, "drug_dose": 0.0})
    treated = _submit_and_wait({"oxygen": OXYGEN_HIGH, "drug_dose": 10.0})
    lc = _trajectory(control["id"])["summary"]["final_live"]
    lt = _trajectory(treated["id"])["summary"]["final_live"]
    assert lt * 5 <= lc, f"high dose kept too many cells: {lt} vs control {lc}"


def s005_zero_dose_matches_drug_free():
    a = _submit_and_wait({"oxygen": OXYGEN_HIGH, "drug_dose": 0.0}, seed=7)
    b = _submit_and_wait({"oxygen": OXYGEN_HIGH}, seed=7)
    fa = _trajectory(a["id"])["frames"]
    fb = _trajectory(b["id"])["frames"]
    assert json.dumps(fa, sort_keys=True) == json.dumps(fb, sort_keys=True), \
        "dose 0 diverged from the drug-free assay"


def s005_plan_drug_comparison():
    plan = http.post("/v1/plan", {
        "prompt": "how does drug dose affect spheroid survival",
    })
    assert plan.get("validated") is True, f"plan not validated: {plan}"
    assert plan.get("runs_created") == [], "planning must not run anything"
    arms = plan["arms"]
    assert [a["name"] for a in arms] == ["control", "treated"], plan
    doses = []
    for arm in arms:
        assert arm["spec"]["engine"] == "physicell", \
            f"plan names no scientific engine: {arm['spec']}"
        _quantities_have_units(arm["spec"])
        doses.append(arm["spec"]["parameters"]["drug_dose"]["value"])
    assert doses[0] != doses[1], "arms do not vary drug dose"


# --- 004: reproducibility bundle -------------------------------------------


def s004_bundle_reproduces():
    a = _submit_and_wait({"oxygen": OXYGEN_HIGH}, seed=7)
    bundle = http.get(f"/v1/runs/{a['id']}/bundle")
    for key in ("engine", "params", "seed", "engine_version", "model_version"):
        assert key in bundle, f"bundle lacks {key}"
    b = _submit_and_wait(bundle["params"], seed=bundle["seed"], engine=bundle["engine"])
    fa = _trajectory(a["id"])["frames"]
    fb = _trajectory(b["id"])["frames"]
    assert json.dumps(fa, sort_keys=True) == json.dumps(fb, sort_keys=True), \
        "bundle rerun diverged"


SCENARIOS = [
    ("features/001-engine-run/spec.md", "Seeded cells grow into a spheroid", s001_spheroid_grows_with_necrotic_core),
    ("features/001-engine-run/spec.md", "Low oxygen slows growth and kills more cells", s001_low_oxygen_hurts_growth),
    ("features/001-engine-run/spec.md", "Repeating a run reproduces its growth curve", s001_rerun_reproduces),
    ("features/002-ai-plan/spec.md", "Plain-language request becomes a validated experiment", s002_plan_from_prompt),
    ("features/002-ai-plan/spec.md", "Impossible request is refused honestly", s002_refuse_impossible),
    ("features/003-compare-rerun/spec.md", "Two runs are compared side by side", s003_compare_side_by_side),
    ("features/003-compare-rerun/spec.md", "Edited parameter produces a new run", s003_rerun_keeps_original),
    ("features/004-reproducibility/spec.md", "A run exports everything needed to repeat it", s004_bundle_reproduces),
    ("features/005-dose-response/spec.md", "Higher doses reduce final live cells monotonically", s005_doses_decrease_monotonically),
    ("features/005-dose-response/spec.md", "A high dose kills most cells versus control", s005_high_dose_kills_most),
    ("features/005-dose-response/spec.md", "Zero dose reproduces the drug-free assay", s005_zero_dose_matches_drug_free),
    ("features/005-dose-response/spec.md", "Treatment request becomes a validated drug comparison", s005_plan_drug_comparison),
]
