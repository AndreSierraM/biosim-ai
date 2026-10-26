# ADR 0001: Capability-first scientific engine adapters

Status: Accepted (architecture)

## Context
An LLM cannot reliably decide solver semantics from names alone. Engines operate across different spatiotemporal scales and numerical assumptions.

## Decision
Each adapter exposes a versioned manifest specifying supported scales, geometry, units, mechanisms, outputs, resource requirements and limitations. A typed planner first proposes an experiment; deterministic validation checks compatibility before dispatch. Artifacts carry provenance.

## Consequences
Adding a new engine requires golden-case validation. Higher upfront engineering cost, lower risk of scientifically misleading results. An unsupported experiment returns an honest capability error.
