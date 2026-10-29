# Roadmap — Meta hackathon first, research platform later

## Immediate competition milestone: Nov 4 2026, 9 PM Bogotá
**Track recommendation:** Indie / Push the Frontier pending confirmed application.

### Day 1-2: can run science
#1 #3 #4 #8 #9. Choose pinned PhysiCell release, create tumor spheroid + drug assay; make real solver execute and emit versioned trajectory. Define golden benchmark before UI polish.

### Day 3-4: AI plans real experiment
#5 and hackathon Meta Model API adapter issue. Create deterministic validated tools with explicit units, guardrails (#6), error and unsupported behavior, no model-generated executable code.

### Day 5-6: visualize and compare
#7 #10 #11 #12 #13 and thin comparison from #17. Runtime is source of every position/time series. Support before/after parameter edit and rerun.

### Day 7: quality gate
#14 #15 #16 #22. Golden benchmark, reproducibility export, fast PR CI only, smoke run under explicit manual command, provider failure handling.

### Day 8: pitch and demo
Hackathon deliverable issue: README, screenshots of **actual running app**, <3 min draft video (duration is editorial choice, not confirmed rule), deployed stable demo, validation table and limitations.

### Day 9: submission readiness
Freeze features, test from new account/device, fallback recorded demo, check participant portal/rules, submit well before cutoff. Do not claim submission unless confirmed.

## Product backlog after competition
#2 full persistence, #18 sweeps, #19 broad UX, #20 tenant RBAC, #23 interpretations, #24 Morpheus, #25 SOFA FEM, #26 OpenMM and remaining P1 enhancements.

## Nonnegotiable definition of done
- AI actively uses a Meta model; requested capabilities measured with evaluation suite.
- The numerical solver really computes the frames; no synthetic output masquerading as solver result.
- Human can inspect exact parameters, units, scientific assumptions, provenance, and engine limitations.
- The experiment is repeatable within documented numerical tolerance.
- No clinical claim; no code execution from LLM prompt.
- Deploy reproducibly; no heavy noisy CI scheduled on every push.

See docs/HACKATHON_2026.md, docs/ARCHITECTURE.md, docs/ISSUES.md.
