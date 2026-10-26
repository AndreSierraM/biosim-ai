# Meta Global AI Developer Hackathon — BioSim AI

Updated 2026-10-26. Source of truth for event: https://dev.meta.ai/events/global-hackathon

## Competition fit and eligibility
- Recommend **Indie Developer** track for an individual/student, **Push the Frontier** theme. Final track depends on participant's registration and official eligibility.
- Event requires approved application (applications closed Oct 25 ET), acceptance of Official Rules by selected participants. **Acceptance not verified.**
- Due **November 4, 2026 at 9:00 PM Eastern Time = 9:00 PM Bogotá** (EST after US daylight saving ends Nov 1), subject to organizer updates.
- Event page shows two tracks: Indie (creativity, technical ambition, works), Startup (technical execution, production readiness).
- Public event page did **not** expose official rules text or final submission form at audit time. **DO NOT assert exact mandatory video length, repository visibility, credits, API quotas, scoring weights or specific delivery fields** until verified in participant portal/rules. A secondary guide summarizes provisional rubric (impact 30%, Meta tooling 25%, execution 20%, demo 25%): confirm with official participant waiver/rules.
- Meta Model API, Muse Spark series, Muse Image and SAM 3.1 are listed; do not add SAM/Image without a concrete scientifically valid task. Only use models actually accessible to the participant.

## Winning thesis
BioSim AI: **From question to reproducible cell experiment**. Natural-language hypothesis -> Meta-powered model plan -> validated scientific parameters -> actual PhysiCell run -> interactive 3D trajectories + charts -> grounded explanation and reproducibility bundle. AI accelerates scientist workflows but never simulates physical outputs itself.

## Demo scenario: cell adhesion
User: 'Investigate how doubling adhesion affects the contact and separation of two cells.' 
1. AI identifies intended biological agents, physical assumptions, needed missing parameters and control/variant setup.
2. Typed ExperimentSpec with two arms, same initial conditions, explicit units and seed.
3. PhysiCell solver computes positions at each simulation time. No membrane deformation claims for agent spheres.
4. UI shows side-by-side 3D trajectories and distance-over-time/contact-duration chart, attributed to actual outputs.
5. User asks 'What changed and how confident are you?' Meta explains comparison *only using measured outputs*, says what model cannot infer and cites run ids.

## Scope freeze
**Must have:** Meta Model API adapter (real calls and logged model version), strict tools/schema, working solver adapter, reproducible experiment, real trajectory 3D, parameter edit/rerun, meaningful metrics, demo video, short pitch, deployable instructions.
**Nice-to-have:** multiple cell agents, parameter sweeps, sharing, curated scientific benchmark.
**Out of competition scope:** SOFA/FEM membrane deformation, OpenMM, Morpheus, complex RBAC, full research platform, generated bio images, clinical decisions.

## Delivery checklist
- [ ] Verify accepted participant and accepted Official Rules
- [ ] Verify participant portal submission form and required materials
- [ ] Confirm available Meta Model API model name, credentials/credits and limits
- [ ] End-to-end public/stable demo with no fallback simulated results
- [ ] Exportable runnable source, install/run commands and reproducibility record
- [ ] Screen recording/video and live demo backup
- [ ] Explicit README: what uses Meta AI; benchmarks, limitations, architecture, license/provenance
- [ ] Measure at least 10 prompts: valid specs, engine compatibility, unit correctness, refusal/unsupported handling, grounding of explanation
- [ ] Video shows actual engine log/output as evidence (not animation only)
- [ ] Test cold-start, bad prompt, solver failure, expired credentials, cancellation
- [ ] Submit before deadline; capture confirmation (manual participant action)

## Evidence / judging narrative
Impact: researchers and students reduce time from textual hypothesis to configured reproducible experiment. Benchmark task completion with/without assistant (do not claim improvement without measured data).
Meta usage: Muse Spark does semantic modeling, constrained planning, explanation; show real request/response metadata and validation statistics, no secret tokens.
Technical: numerical solver artifacts, schema guardrails, resource-isolated worker, provenance, repeatability.
Demo: compelling two-cell before/after comparison, inspectable observable plot, clear limitations, fallback recording.

## Sources
- https://dev.meta.ai/events/global-hackathon (official event page)
- https://cerebralvalley.ai/e/meta-ai-developer-hackathon (organizer)
- https://bootshell.com/meta-global-ai-developer-hackathon-2026-complete-guide-rules-prizes (secondary rubric only, not official confirmation)
