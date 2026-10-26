# Delivery roadmap

## P0 — Foundation + first real cell simulation
ExperimentSpec, capability registry, secure planning API, run store, worker orchestration, PhysiCell adapter, frame parser, minimal 3D playback, scientific validity tests, reproducibility export.

**Gate:** an AI-planned two-cell interaction run yields genuine PhysiCell-produced trajectories; viewable in browser; full rerun reproducible with a fixed seed, within expected numerical tolerances; failures report explicitly.

## P1 — Useful laboratory
Comparative experiments, metric panels, parameter sweeps, reproducible workspace, saved prompts, share/export, polished UX, observability and system hardening.

**Gate:** nontechnical users can compare two scientifically valid scenarios and inspect model assumptions without coding.

## P2 — Multiscale pathways
Morpheus for declarative cellular spatial models, SOFA for deformable-cell mechanics, custom scientific reference datasets.

**Gate:** every adapter has independently validated fixtures and limitations.

## P3 — Molecular simulations
OpenMM atomistic tasks, molecular structure viewer and PDB provenance, compute quotas and GPU scheduling.

**Gate:** no suggestion that molecular and whole-cell physical models are interchangeable.

## Delivery policy
One focused CI workflow for lint, unit, schema contract and minimal integration checks; nightly/heavy scientific benchmarks only on demand. No CI matrix spam. Never deploy stub or synthetic data as real experiment output.
