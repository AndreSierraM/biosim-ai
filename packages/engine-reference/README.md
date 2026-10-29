# engine-reference

Reference two-cell adhesion solver: a **development scaffold** with real
numerics (overdamped rigid-sphere dynamics, seeded RNG), used to build the
viewer, API and provenance plumbing before the PhysiCell adapter (#8).

> Its outputs are computed, but they are NOT PhysiCell results and NOT
> validated biology. Every artifact carries `engine_id: reference-2cell`
> so provenance stays honest.

## Run

```bash
# from the repo root
python3 packages/engine-reference/cli.py \
  --params packages/engine-reference/params/baseline.json \
  --out artifacts/baseline/trajectory.json

python3 packages/engine-reference/cli.py \
  --params packages/engine-reference/params/high-adhesion.json \
  --out artifacts/high-adhesion/trajectory.json

# reproducibility + physics gates (stdlib only, no install)
python3 packages/engine-reference/tests/test_determinism.py
python3 packages/engine-reference/tests/test_physics.py
```

## Files

- `solver.py` — physics + integration, zero dependencies
- `adapter.py` — `EngineAdapter` boundary the PhysiCell adapter will implement
- `manifest.json` — fidelity declaration and limits
- `params/` — pinned parameter sets (baseline vs doubled adhesion)
- `cli.py` — writes versioned trajectory artifacts
