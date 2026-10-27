# Competition demo — user journey and API design

**Status:** target technical contract, not implemented.

## Target scenario (the product's one hero journey)

- User prompt: "Compare two identical cells approaching each other, first at adhesion A, then at 2 × A. What changes?"
- Meta-powered experiment planner proposes typed `ExperimentSpec` and flags assumptions about radii, speed, initial distance, time resolution, force model and solver capability.
- User can inspect/edit adhesion and control/variant parameters (with units) before confirmation.
- Run A and run B use the same initial geometry, solver version, model and chosen seed.
- PhysiCell performs actual cell-agent time evolution. Output is converted into versioned trajectory frames with `x,y,z,radius,t,cell_id` and provenance.
- Viewer shows synchronized positions over time (3D) and graphs of measured separation and contact duration, with run IDs and units.
- Follow-up question: "Did higher adhesion keep them together longer?" Meta's summary cites computed metric values and clearly states if the observed difference is inconclusive.

## Proposed UI (one screen)
- Header: BioSim AI, status of solver/provider, Experiment switcher.
- Left: conversational composer + AI plan summary with "unsupported" states and clear confirmation action.
- Center: 3D orbit view, units, selection, timeline controls.
- Right: param inspector and metrics tabs, provenance link, compare toggle.
- Bottom: solver run state, traceable log messages, no fictional or pre-rendered success on failures.
- Responsive: main viewport first, panels as tabs, keyboard accessible.

## Proposed API contract (subject to implementation and OpenAPI validation)
- `POST /api/v1/experiment-plans`: `{prompt:string}` -> `{status:"proposed"|"needs_information"|"unsupported",spec?,assumptions:[],questions:[],warnings:[]}`.
- `POST /api/v1/runs`: `{experiment_spec, idempotency_key}` -> `{run_id,state:"queued",spec_hash}`. Validate every field and capability before queueing.
- `GET /api/v1/runs/{run_id}`: state, progress, solver info, error_code and artifact manifest links.
- `POST /api/v1/runs/{run_id}/cancel`: idempotent cancellation; does not mark complete.
- `GET /api/v1/runs/{run_id}/frames`: versioned manifest and time-sliced frames from real solver.
- `GET /api/v1/runs/{run_id}/metrics`: separation-over-time, contact events/duration, dimensionality and method.
- `POST /api/v1/compare`: `{baseline_run_id,variant_run_id}` -> paired metric comparison and compatibility warnings.
- `POST /api/v1/analysis`: `{run_ids,question}` -> Meta grounded explanation referencing real values only.

Endpoints are proposed, and **none are currently available**.

## Scientific fidelity gate
Cell-agent contacts are represented by modelled force laws on spherical agents. The UI must never call this membrane mesh deformation or make clinical conclusions. Contact duration is a derived geometric observable and is sensitive to threshold, time resolution and physical model assumptions.

## Demo failure cases
- Unsupported subcellular physics -> explanation and alternate supported experiment, never fake animation.
- Missing units or contradictory parameters -> field errors/questions.
- Invalid Meta credential, provider outage -> explicit provider failure.
- Solver build fails, timeout, cancellation -> explicit failed/cancelled status, no generated results.
- Corrupt frames -> validation error and raw logs, not partial invalid graphs.

## Judge walkthrough
1. State the biological research problem and simulator limitations.
2. Type prompt; show Meta-powered plan, validation and approval.
3. Show actual Physicell run and its output metadata.
4. Play 3D and change adhesion, compare real metrics.
5. Ask the assistant why; show grounded explanation.
6. Export provenance manifest; disclose future possibilities separately.
