# Feature 004 — Reproducibility bundle

Every run exports everything a stranger needs to repeat it.

```gherkin
Feature: Reproducibility bundle

Scenario: A run exports everything needed to repeat it
  Given a completed run
  When the researcher exports its reproducibility bundle
  Then the bundle contains the parameters, seed, engine version and model version
  And rerunning from the bundle reproduces the trajectories

Scenario: Idempotent retry never burns solver time twice
  Given a completed run submitted with an idempotency key
  When the researcher resubmits the same engine, parameters, seed and key
  Then the API returns the original run with deduplicated true
  And no new solver run starts

Scenario: Out-of-range parameters are rejected before running
  Given a run request with oxygen far outside the assay range
  When the researcher submits it
  Then the API refuses with a 400 naming the range
  And no job is created

Scenario: Fixed assay properties are rejected, never ignored
  Given a run request varying the cell radius
  When the researcher submits it
  Then the API refuses with a 400 explaining the radius is fixed
  And no job is created
```
