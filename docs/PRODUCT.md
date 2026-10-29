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
- 'How does oxygen availability affect tumor spheroid growth?' (control vs low-oxygen arms)
- 'How does drug dose affect spheroid survival?' (control vs treated arms, then a dose sweep)
- 'Sweep drug doses 0, 0.3, 1, 3, 10 uM and show the dose-response curve with IC50.'

## Flagship assay (hackathon slice)
Tumor spheroid + cytotoxic drug dose-response on PhysiCell 1.14.2: sustained
boundary dose, diffusion/uptake gradient, Hill apoptosis. Assay-scale readouts
(final live cells, dose-response curve, log-linear IC50) — explicitly not clinical.

## AI interaction principles
Plan-before-run, editable parameters, provenance badges, user control, meaningful errors, visible progress, no demo data masquerading as simulation.
