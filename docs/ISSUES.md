# Verified issue execution plan — updated 2026-10-26

There are **31 open issues** (#1–#20, #22–#32). #21 was closed as duplicate of #20. Every original issue now has its own hackathon execution supplement containing file surfaces, dependencies, work, acceptance tests and exclusions.

## First-class hackathon path
- Foundation: #1 -> #3 -> #4.
- Scientific core: #8 -> #9 -> #10 -> #11 -> #13.
- Meta AI: #30 (actual API) + #5 (typed planner) + #6 (guardrails) -> #12 (conversation UX).
- Runtime orchestration: #7; reproducibility: #14; smoke: #15; benchmarks: #22 and #32.
- Comparison: thin targeted implementation from #17.
- Delivery: #31 recorded/live demo, portal/eligibility verification and evidence.
- Cross-cutting: #16 lightweight CI, #28 runbook; narrow #19 visual polish.

## Defer explicitly
- #2 complete persistent tenancy model
- #18 full parameter sweep; #20 full auth/tenant policies; #23 advanced narrative analysis; #27 full observability
- #24 Morpheus; #25 SOFA; #26 OpenMM
- #29 broad scenario catalog and advanced #19 experience
These issues remain open as an honest post-competition backlog.

## Per-issue success proof
Linked focused PR with implementation code, type/contracts, unit/integration tests, error conditions, scientific provenance where relevant, limitation disclosure. Never close science issues with a UI-only animation. The contest is only ready when #15 + #30 + #32 + #31 can be demonstrated with real artifacts.

See docs/ROADMAP.md, docs/DEMO_SPEC.md and AGENTS.md. No portal submission is implied.
