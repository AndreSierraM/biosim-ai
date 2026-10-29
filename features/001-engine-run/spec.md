# Feature 001 — Real tumor spheroid growth

The scientific engine (not the AI, not an animation) grows a cell
cluster from a seed: proliferation, oxygen consumption and necrosis
all emerge from the numerical model.

```gherkin
Feature: Real tumor spheroid growth

Scenario: Seeded cells grow into a spheroid
  Given a tumor spheroid experiment with normal oxygen
  When the experiment runs on the scientific engine
  Then living cells multiply over time
  And dead cells appear in the oxygen-starved core

Scenario: Low oxygen slows growth and kills more cells
  Given a tumor spheroid experiment with low oxygen
  When the experiment runs on the scientific engine
  Then it ends with fewer living cells than the normal-oxygen run
  And it ends with more dead cells than the normal-oxygen run

Scenario: Repeating a run reproduces its growth curve
  Given a completed spheroid run
  When the same experiment runs again with the same seed
  Then every recorded growth measurement matches the first run
```
