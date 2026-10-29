# Feature 003 — Compare runs and rerun with edits

Researchers compare two runs side by side and launch edited reruns
without touching the originals.

```gherkin
Feature: Compare runs and rerun with edits

Scenario: Two runs are compared side by side
  Given a completed normal-oxygen run and a completed low-oxygen run
  When the researcher compares them
  Then both 3D spheroids are visible together
  And the living-cell counts are shown side by side

Scenario: Edited parameter produces a new run
  Given a completed run
  When the researcher lowers its oxygen and reruns
  Then a new run starts from the edited parameters
  And the original run is unchanged
```
