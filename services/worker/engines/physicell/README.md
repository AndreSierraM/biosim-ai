# PhysiCell two-cell engine

Real scientific engine for the hackathon slice: pinned PhysiCell 1.14.2
(BSD-3) running a two-cell adhesion assay, normalized to the same
trajectory artifact as the reference engine.

- `model/custom.cpp` — assay code (adapted template; BSD notice retained)
- `model/two_cell_settings.xml` — config template (adapter substitutes
  adhesion, seed, output folder per run)
- `adapter.py` — config render + binary run + MultiCellDS parse
- `vendor/` — pinned source + built `project` binary (gitignored)
- `setup.sh` — clone (if missing), install model, build with brew GCC

```bash
services/worker/engines/physicell/setup.sh
```

Runs execute single-threaded (`OMP_NUM_THREADS=1`) for determinism.
Per-run workdirs live under the system temp dir; the artifact records
`meta.run_dir` for inspection.
