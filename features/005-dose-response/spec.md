# Feature 005 — Drug dose-response

Researchers sweep a cytotoxic drug dose over the spheroid assay and get
a graded dose-response: higher sustained doses reduce the final live-cell
count monotonically. Dose zero reproduces the drug-free assay exactly.

```gherkin
Feature: Drug dose-response

Scenario: Higher doses reduce final live cells monotonically
  Given completed spheroid runs at drug doses 0, 1 and 10 uM
  When the researcher reads the final live-cell counts
  Then the counts decrease strictly with dose

Scenario: A high dose kills most cells versus control
  Given a control run at 0 uM and a treated run at 10 uM
  When the researcher compares final live-cell counts
  Then the treated spheroid keeps at most 20% of the control count

Scenario: Zero dose reproduces the drug-free assay
  Given a run with drug dose 0 uM and a run without any drug parameter
  When the researcher compares their trajectories
  Then both trajectories are identical

Scenario: Treatment request becomes a validated drug comparison
  Given the prompt "how does drug dose affect spheroid survival"
  When the researcher plans the experiment
  Then the plan validates with a control arm and a treated arm
  And the arms differ in drug dose with explicit units
  And no runs are created by planning
```
