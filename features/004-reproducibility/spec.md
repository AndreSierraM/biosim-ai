# Feature 004 — Reproducibility bundle

Every run exports everything a stranger needs to repeat it.

```gherkin
Feature: Reproducibility bundle

Scenario: A run exports everything needed to repeat it
  Given a completed run
  When the researcher exports its reproducibility bundle
  Then the bundle contains the parameters, seed, engine version and model version
  And rerunning from the bundle reproduces the trajectories
```
