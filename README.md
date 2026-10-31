# BioSim AI

**From biological hypothesis to reproducible 3D cell simulation, powered by Meta AI.**

BioSim AI is an open-source AI-native scientific workbench: describe a cellular experiment in natural language, review its validated parameters, run a real numerical solver, inspect 3D trajectories and compare measured outcomes.

> **Implementation status (2026-10-28): prompt → validated plan → pinned PhysiCell 1.14.2 run → 3D + charts works end-to-end (acceptance 12/12, planner bench 10/10 offline). Measured dose ladder seed 7: 0→115, 0.3→93, 1.0→41, 10→4 live cells. Live Meta Model API calls NOT yet verified (planner runs on a deterministic fixture until a key is provisioned); no submission made.** Do not claim a working prototype, benchmark or submission before actual evidence exists.

## Meta hackathon focus

Proposed theme **Push the Frontier**, proposed category **Indie Developer** (subject to registration eligibility). The current competition goal is a single credible prompt-to-PhysiCell-to-3D-to-explanation loop.

**Hero experiment:** "What changes when the adhesion between two approaching cells doubles?" Meta AI proposes a typed experiment, a human reviews assumptions, PhysiCell generates the actual cellular trajectories, and a 3D interface shows before/after and distance/contact-time graphs. The assistant explains only measured results and their limitations.

- [Hackathon audit and eligibility](docs/HACKATHON_2026.md)
- [Competition-first development roadmap](docs/ROADMAP.md)
- [Task dependencies and GitHub issues](docs/ISSUES.md)
- [Agent implementation rules](AGENTS.md)
- [Demo UX, API and observables](docs/DEMO_SPEC.md)
- [Meta API integration contract](docs/META_AI_ADAPTER.md)
- [Submission package checklist](docs/SUBMISSION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Scientific engine research](docs/RESEARCH.md)
- [Security boundaries](docs/SECURITY.md)
- [GitHub issue tracker](https://github.com/AndreSierraM/biosim-ai/issues)

## Architecture (shipped, except Meta live calls)

- React + TypeScript + React Three Fiber for chat, input validation and trajectory visualization.
- FastAPI + Pydantic with a versioned ExperimentSpec and engine capability manifest (`GET /v1/tools`).
- Meta Model API adapter implemented with model/request/token/latency provenance; live calls pending verified account/model access (fixture until then).
- Pinned PhysiCell 1.14.2 worker producing authentic cell-center trajectories and numerical outputs.
- Hashes, seed, units, solver version, model assumptions and original output in each reproducibility bundle.

Morpheus, SOFA and OpenMM are independent longer-term adapters, **not required for the hackathon**. An agent-based spherical cell model must not be presented as a deformable-membrane finite element simulation.

## Development approach

Work issues in dependency order, only close an issue with reproducible evidence and tests. No invented simulation results, permanent mocks in user-facing screens or unreviewed LLM-generated executable code. Keep CI lightweight to minimize notification noise. See [AGENTS.md](AGENTS.md).

```bash
# 1. compute reference trajectories (stdlib Python, no install)
python3 packages/engine-reference/cli.py \
  --params packages/engine-reference/params/baseline.json \
  --out artifacts/baseline/trajectory.json
python3 packages/engine-reference/tests/test_determinism.py

# 2. API (health, spec validation, runs, planning)
cd services/api
.venv/bin/python -m uvicorn app.main:app --port 8123

# 3. web viewer (needs samples copied once, see apps/web/README.md)
cd apps/web && npm install && npm run dev   # -> http://localhost:5173
```

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`. Scaffolding grows with
each vertical slice; see tracked GitHub issues for acceptance criteria.

## Relevant software

[PhysiCell](https://github.com/MathCancer/PhysiCell) · [Morpheus](https://morpheus.gitlab.io/) · [SOFA](https://www.sofa-framework.org/) · [OpenMM](https://openmm.org/) · [Simularium](https://github.com/simularium/simularium-viewer)

## License

The original repository uses Apache-2.0. Imported solvers, datasets, pretrained models and models' outputs retain their respective license and use restrictions.
