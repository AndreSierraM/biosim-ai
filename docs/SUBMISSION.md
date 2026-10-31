# BioSim AI — Submission kit / working draft

## One sentence
BioSim AI turns a biological research question into a validated, repeatable cellular simulation using Meta AI and scientific numerical software, then lets users explore the computed results in interactive 3D.

## Theme
Push the Frontier (official), recommended Indie track unless application says otherwise.

## Problem
Researchers and learners face multiple disconnected interfaces and expertise requirements to turn qualitative hypotheses into a parameterized numerical model, run it, and inspect reproducible observables.

## Differentiator
Meta AI acts as a constrained scientific experiment planner and interpreter, not a video generator. Deterministic scientific engine execution plus provenance makes outputs inspectable and repeatable.

## Proof points needed before finalizing submission
- Real Meta Model API calls with model ID and schema-valid planning examples.
- PhysiCell spheroid dose-response: control vs treated runs plus a graded dose
  ladder, measured seed 7 engine 1.14.2 (0 → 115 live, 0.3 → 93, 1.0 → 41,
  10 → 4 uM; strictly decreasing, high dose ≈3% of control), with controlled
  assumptions. No measured IC50 yet: any IC50 shown is an assay-scale
  interpolation, not a fitted experimental value.
- Recording of live prompt-to-plan-to-sweep-to-3D experience.
- Reproducibility package and scientific benchmark.
- Source code and deployed working URL.
- Clear limitation: simplified cell agents, not membrane-level biomechanics; no clinical claims.

## Pending official verification
Review accepted Official Rules and live participant portal for mandatory fields, video specs, team and ownership requirements, access rules, credits and whether source/public deployment is required. This draft is not evidence of successful registration or submission.
