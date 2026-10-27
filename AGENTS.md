# AI agent instructions — BioSim AI

Read README.md, docs/HACKATHON_2026.md, docs/ROADMAP.md, docs/ISSUES.md and relevant issue before any code changes. This is a **scientific software system** preparing for Meta Global AI Developer Hackathon 2026, not a generic chat or animation demo.

## Source of truth / priority
- Target deliverable: usable Meta AI prompt -> typed plan -> real PhysiCell run -> 3D view + measured chart -> grounded explanation.
- Check scientific correctness before aesthetics. Demo visual quality matters only after real solver data flows end-to-end.
- Contest constraints should be verified from organizers / participant portal; don't assert unverified submission requirements.
- Don't work on Morpheus, SOFA, OpenMM, organization RBAC or broad parameter sweeps before the core run works.
- Keep changes focused to issue scope and dependency order. Do not refactor unrelated parts or add demo/sample data in production UI.

## Required implementation discipline
1. Inspect existing structure/code before changing it; avoid duplicate abstractions.
2. Pick a single canonical ExperimentSpec schema and derive Python/TypeScript types; units explicit and validated.
3. LLM is a planner, *not* a numerical solver. Never accept tool invocations, paths or executable code not allowlisted by server.
4. Real numerical outputs must come from pinned native solver binaries and be marked with exact engine/version/hash, seed, assumptions and artifact digest.
5. Fixtures/mocks may appear ONLY inside tests with explicit labels. The final app cannot display fake plots/cells as measured experimental output.
6. If a request asks for unsupportable physics (e.g. cell membrane deformation via PhysiCell spherical agents), return precise unsupported capability feedback.
7. Record real model provider ID from Meta API; do not hardcode unverified wire protocols or claim API calls that were not made.
8. Validate science with quantitative golden cases and tolerances; include negative/invalid/timeout/cancellation paths.
9. Keep a single lightweight PR CI workflow; heavy solver and live provider tests manual/on-demand.
10. Don't declare production/hackathon ready until end-to-end proof and submission checklist are independently verified.

## PR completion template
- Linked issue and touched paths
- User-visible result and screenshots from running code when relevant
- Commands run with exit status, unit + integration tests
- Scientific source of run outputs and benchmark/tolerances
- Model/solver versions and environment
- Known limitations, security risks and next dependency
- No unverifiable claims of deployed URLs or successful submission

## Agent working order
Start #1, #3, #4, #8, #9; enable #30 Meta model adapter and #5 planner; connect #7, #10, #11, #12, #13, thin #17, #14, #15; evaluate #32 and prepare #31. Enforce #6, #16, #22 and #28 cross-cutting.
