# Product specification

## Users
- Computational biology researchers: reproducible experiments with direct model control.
- Biomedical engineering students and educators: interactive 3D labs with explicit validity labels.
- AI/agent builders: extensible benchmarkable scientific tool orchestration.

## Critical user journey
1. Enter a biological hypothesis/prompt.
2. Review extracted species, geometry, units, boundary conditions, solver recommendation, assumptions and estimated compute cost.
3. Resolve missing parameters (required fields only), approve execution.
4. Observe queued/running/failed/completed status; cancel or rerun with seed.
5. Play 3D time-series and inspect measurable observables.
6. Compare a baseline against a parameter variant.
7. Export experiment specification, raw outputs, environment, provenance and limitations.

## Explicit non-goals
- Clinical diagnosis, personalized treatment, automated biological protocol execution.
- Atomistically detailed simulation of an entire cell.
- Implying a rendering, trajectory preview or LLM text is validation.
- GPU-heavy solver code running in the API/web container.

## Differentiator
An AI scientist interface constrained by a machine-readable registry of scientific simulation capabilities, with automatic reproducibility packages and model limitations attached to every result.

## Example prompts
- 'Compare how adhesion changes trajectories of two spherical cells after contact.'
- 'Run 100 cells competing for a limited diffusing nutrient under two initial concentrations.'
- 'Show an intracellular molecule diffusion experiment and the concentration over time.'

## AI interaction principles
Plan-before-run, editable parameters, provenance badges, user control, meaningful errors, visible progress, no demo data masquerading as simulation.
