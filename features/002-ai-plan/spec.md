# Feature 002 — AI-planned experiment

A researcher writes a plain-language question; the Meta-powered
assistant plans a validated experiment or honestly refuses.

```gherkin
Feature: AI-planned experiment

Scenario: Plain-language request becomes a validated experiment
  Given a researcher asks "how does oxygen availability affect tumor spheroid growth"
  When the assistant plans the experiment
  Then the plan names the scientific engine and both oxygen values
  And every quantity carries explicit units
  And the plan is validated before anything runs

Scenario: Impossible request is refused honestly
  Given a researcher asks for atom-level detail of a whole cell
  When the assistant plans the experiment
  Then no experiment runs
  And the researcher learns why the engines cannot do it

Scenario: Custom assay uses any supported parameter combination
  Given a researcher asks for a spheroid with moderate oxygen and a custom seed
  When the assistant plans the experiment
  Then the plan validates with a single custom arm
  And every quantity carries explicit units
  And the arm seed matches the request
  And no runs are created by planning

Scenario: Unsupported parameter is refused honestly
  Given a researcher asks to vary the cell radius
  When the assistant plans the experiment
  Then no experiment runs
  And the researcher learns the assay fixes the cell radius

Scenario: AI discovers capabilities before planning
  Given the assistant needs to plan an unfamiliar assay
  When it lists the allowlisted tools
  Then it learns every engine with parameter ranges, units and limits
  And it learns planning never runs anything
```
