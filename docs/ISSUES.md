# Issue execution order

28 open implementation issues. #21 was closed as a duplicate of #20.

## P0 — Scientific end-to-end first
- #1 monorepo -> #3 schema -> #4 capability registry -> #5 AI planner
- #1 -> #2 persistence -> #7 job lifecycle -> #8 real PhysiCell adapter
- #8 -> #9 scientific validation -> #10 parser -> #11 3D viewer
- #5 + #11 -> #12 interactive experiment UX
- #9 + #10 -> #13 scientific results -> #14 reproducibility export
- #5 + #8 + #10 + #11 + #14 -> #15 real end-to-end integration
- #6 security is cross-cutting and required before enabling execution.
- #16 light CI and #28 documentation are cross-cutting.

## P1 — Production-quality scientific workbench
- #17 baseline/variant comparisons after #15
- #18 parameter sweeps after #7, #9, #17
- #19 UX polish after #11, #12
- #20 authentication/tenancy after #2
- #22 benchmark suite after #9; required for future adapters
- #23 grounded AI analysis after #13, #22
- #27 artifact observability after #7, #14
- #29 curated scenarios after #15, #22

## P2/P3 — Scientific expansion
- #24 Morpheus after #4, #7, #10, #22
- #25 SOFA after #4, #7, #10, #22
- #26 OpenMM after #4, #7, #10, #22

## Release quality gates
- No LLM-generated outputs are presented as solver results.
- Re-run same configuration and seed reproduces a run within benchmark tolerance.
- Unsupported biology/physics returns a capability validation error.
- Scientific outputs always include units, solver identity, assumptions and provenance.
- CI runs on PRs with lightweight checks; expensive simulations are manually triggered.
