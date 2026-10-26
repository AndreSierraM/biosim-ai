# Engine research and integration shortlist (2026-10-26)

| Engine | Strength | Constraint | Integration priority |
| --- | --- | --- | --- |
| PhysiCell | 3D multicellular agent-based physics, growth, motility, diffusion | Cells modeled as agents, not detailed deforming membranes | P0 |
| Morpheus | Declarative multicellular CPM/ODE/PDE and SBML | Complex adapter conversion and model-specific semantics | P2 |
| SOFA | Finite-element deformation, collision/contact | More expensive geometry/material validation | P2 |
| OpenMM | Atomistic molecular dynamics, accelerated GPUs | Nanosecond-scale / molecular, not cell collision | P3 |
| Simularium | Browser trajectory visualization | Viewer rather than a scientific solver | P1 option |

Sources:
- https://physicell.org/Downloads.html (PhysiCell BSD-3)
- https://physicell.org/ (PhysiCell overview)
- https://morpheus.gitlab.io/ (Morpheus BSD, MorpheusML, 2D/3D)
- https://github.com/sofa-framework/sofa (LGPL core, GPL applications)
- https://github.com/openmm/openmm (mixed MIT/LGPL components; review bundled licenses)
- https://github.com/simularium/simularium-viewer (Apache 2.0 viewer)

### Scientific validation requirements
- Define benchmark cases and stable solver versions before presenting numerical claims.
- Compare cell-agent trajectories against deterministic force-law reference cases and published examples.
- Quantify convergence as dt, spatial resolution and stochastic seeds vary.
- Keep stochastic ensemble intervals distinct from parameter uncertainty.
- Identify assumptions, calibrated parameters, relevant scales and units.
- Never claim cell membrane stress from sphere-center trajectories.

### Licensing
License audit is mandatory before redistribution: include runtime dependencies, binaries, scientific models, pretrained weights and imported structures separately.
