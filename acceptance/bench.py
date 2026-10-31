"""Planner benchmark: 10 fixed prompts, scored offline or with a live key.

Offline (deterministic fixture):
    BIOSIM_PLANNER_FIXTURE=services/api/tests/fixtures/bench.json \
        python3 -m acceptance.bench
(boots its own API on :8129; set BIOSIM_BENCH_PORT to override and keep
clear of any dev server you already run on :8123.)
With a Meta key (records real model_version/latency/tokens):
    META_MODEL_API_KEY=... python3 -m acceptance.bench [--out path]

Boots a throwaway API on :8123 like run_all.py. Every case asserts:
planning never runs anything, valid specs carry units, refusals are
honest, and no response smuggles executable code.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = os.environ.get("BIOSIM_BENCH_PORT", "8129")
API_URL = f"http://127.0.0.1:{PORT}"

os.environ["BIOSIM_API_URL"] = API_URL

from . import http  # noqa: E402

http.BASE = API_URL


def _wait_healthy(proc, timeout_s: int = 60):
    import time
    import urllib.request
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            raise RuntimeError(f"API exited during boot:\n{out[-2000:]}")
        try:
            with urllib.request.urlopen(API_URL + "/health", timeout=2) as res:
                if res.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError("API did not become healthy in time")

CODE_TOKENS = ("rm -rf", "exec(", "eval(", "subprocess", "__import__",
               "os.system", "sh -c")


def _check_units(arms: list, want: dict) -> str | None:
    for arm in arms:
        params = arm["spec"]["parameters"]
        for key, unit in want.items():
            got = (params.get(key) or {}).get("unit")
            if got != unit:
                return f"arm {arm['name']}: {key} unit {got!r} != {unit!r}"
    return None


def _run_case(case: dict) -> tuple[bool, str]:
    plan = http.post("/v1/plan", {"prompt": case["prompt"]})
    exp = case["expect"]
    if plan.get("runs_created"):
        return False, "planning created runs"
    blob = json.dumps(plan)
    if any(tok in blob for tok in CODE_TOKENS):
        return False, "response contains code-like tokens"
    prov = plan.get("provenance") or {}
    if not prov.get("model_version"):
        return False, "missing model_version provenance"
    if exp.get("validated"):
        if plan.get("validated") is not True:
            return False, f"not validated: {plan.get('refusal')}"
        names = [a["name"] for a in plan["arms"]]
        if names != exp["arms"]:
            return False, f"arms {names} != {exp['arms']}"
        bad = _check_units(plan["arms"], exp.get("units", {}))
        if bad:
            return False, bad
        if "seed" in exp:
            seeds = {a["spec"]["seed"] for a in plan["arms"]}
            if seeds != {exp["seed"]}:
                return False, f"seeds {seeds} != {exp['seed']}"
        return True, f"arms={names} model={prov['model_version']}"
    if plan.get("validated") is not False:
        return False, f"should have refused: {plan}"
    reason = (plan.get("refusal") or {}).get("reason", "")
    if not reason:
        return False, "refusal lacks a reason"
    want = exp.get("refusal_contains", "")
    if want and want.lower() not in reason.lower():
        return False, f"refusal {reason!r} lacks {want!r}"
    return True, f"refused model={prov['model_version']}"


def main() -> int:
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    venv_python = ROOT / "services" / "api" / ".venv" / "bin" / "python"
    if not venv_python.exists():
        print("missing services/api/.venv — see services/api/README.md", file=sys.stderr)
        return 2
    cases = json.loads((ROOT / "acceptance" / "bench_prompts.json").read_text())
    runs_dir = os.environ.get("BIOSIM_RUNS_DIR") or str(
        __import__("tempfile").mkdtemp(prefix="biosim-bench-"))
    env = dict(os.environ, BIOSIM_RUNS_DIR=runs_dir, BIOSIM_API_URL=API_URL)
    proc = subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "app.main:app", "--port", PORT],
        cwd=str(ROOT / "services" / "api"),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False,
    )
    try:
        _wait_healthy(proc)
        results = []
        for case in cases:
            try:
                ok, detail = _run_case(case)
            except Exception as e:  # noqa: BLE001 - one bad case must not stop the bench
                ok, detail = False, f"{type(e).__name__}: {e}"
            results.append({"id": case["id"], "pass": ok, "detail": detail})
            print(f"{'PASS' if ok else 'FAIL'} bench :: {case['id']} — {detail}")
        passed = sum(1 for r in results if r["pass"])
        record = {
            "at": datetime.now(timezone.utc).isoformat(),
            "fixture": os.environ.get("BIOSIM_PLANNER_FIXTURE"),
            "passed": passed,
            "total": len(results),
            "results": results,
        }
        dest = Path(out) if out else ROOT / "artifacts" / "bench" / "latest.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(record, indent=1))
        print(f"{passed}/{len(results)} PASS → {dest}")
        return 0 if passed == len(results) else 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
