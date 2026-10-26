# BioSim AI

**Natural language to reproducible biological simulation.**

BioSim AI is an open-source, AI-native 3D computational biology workbench. Users describe a biological experiment; an agent builds a typed experiment specification, validates scientific and compute constraints, schedules the appropriate simulation engine, and renders real computed trajectories and measurements.

> Current status: architectural foundation and development backlog. No production-grade simulation engine is integrated yet. Never label animations or synthetic fixtures as scientific findings.

## Product principles

1. **Physics before pixels:** scientific outputs always originate from numerical solvers.
2. **No fabricated findings:** AI can explain results but cannot create experimental result arrays.
3. **Evidence and reproducibility:** every run records model, seed, units, assumptions, solver version, code hash and dataset provenance.
4. **AI with guardrails:** typed tools and reviewed adapter manifests; never execute arbitrary LLM-authored shell/Python/C++.
5. **Progressive scientific fidelity:** start with cell-scale interactions; add subcellular and molecular engines as separate adapters.
6. **Honest uncertainty:** show model validity, limitations, calibration and confidence indicators.
7. **No medical diagnostic use.**

## First vertical slice

'Run two cells approaching each other, compare their resulting trajectories with different adhesion strengths' -> generate validated ExperimentSpec -> enqueue PhysiCell adapter run -> parse native results -> show time-indexed 3D playback, charts and physical assumptions -> export a reproducibility bundle.

Membrane deformation at mesh resolution is **not supported** by a simple agent-based cell model: SOFA integration belongs in a separate validated capability.

## Architecture

- `apps/web`: React + TypeScript + Vite + React Three Fiber, TanStack Query, lightweight charts.
- `services/api`: FastAPI REST, Pydantic schemas and OpenAPI.
- `services/worker`: isolated worker and simulation adapters; heavy solver images are separate.
- `packages/experiment-schema`: canonical JSON Schema, units and capability metadata.
- `packages/engine-physicell`: first scientific engine adapter (planned).
- `docs`: architecture, validation, threat model, ADRs and roadmap.
- PostgreSQL: users, experiments, runs, provenance; Redis for job queue; object store for trajectory artifacts.

## Getting started

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`. Source scaffolding is intentionally minimal until the first end-to-end scientific test is established. See tracked GitHub issues for implementation and acceptance criteria.

## Relevant software

[PhysiCell](https://github.com/MathCancer/PhysiCell) · [Morpheus](https://morpheus.gitlab.io/) · [SOFA](https://www.sofa-framework.org/) · [OpenMM](https://openmm.org/) · [Simularium](https://github.com/simularium/simularium-viewer)

## License

Apache-2.0 for original project code. Dependencies remain governed by their own licenses; check LGPL/GPL components and scientific asset/data terms before distribution.
