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

### Unmet scientific needs (review 2026-10-27)

Grounding: Munn & Jain, "Challenges and opportunities for the next generation of
computational tumor models", PLOS Biol 23(7): e3003269 (2025).

What scientists cannot do well today:
1. Build models without multidisciplinary teams. Mechanistic tumor models "require
   multidisciplinary expertise and abundant biological data to develop"; TME models
   need mathematicians + oncologists + biologists + immunologists + engineers, and
   collaboration/funding barriers block most groups.
2. Calibrate parameters. High-quality longitudinal datasets for calibration and
   benchmarking are scarce; calibration is a multi-metric optimization problem over
   stochastic, expensive ABMs with poor identifiability and local minima.
3. Predict individual responses. Uniform tumor parameters across populations fail to
   predict individual outcomes; spatial clinical data is still not integrated into models.
4. Capture system-level drug resistance. Multicellular resistance is a property of the
   3D tumor as a system (gradients, hypoxia, geometry) and evaporates in monolayer
   assays — exactly what spheroid ABMs can probe.
5. Trust and adopt models. Clinician skepticism (complexity, interpretability,
   insufficient validation), regulatory uncertainty, and models going stale as biology
   advances.

What AI + mechanistic engines can credibly achieve (per the same review):
- ML estimating unknown parameters, initializing models from data, surrogate modeling
  for real-time prediction and rapid sensitivity analysis.
- Data assimilation and calibration when parameters are experimentally inaccessible;
  inference from time-series/observational data.
- Hypothesis testing and virtual experimentation: tumor growth, invasion, response to
  therapy, hybrid quantitative-systems-pharmacology models, virtual clinical trials,
  biomarker discovery.
- Patient-specific digital twins (stated as direction, NOT as a BioSim AI claim).

BioSim AI consequence: the highest-contribution slice is the calibration + virtual
experimentation loop (fit model to observed growth → predict treatment dose-response
in silico), not single forward runs. Explicitly out of scope: clinical predictions,
patient data, membrane mechanics (SOFA), molecular detail (OpenMM).

Sources:
- https://pmc.ncbi.nlm.nih.gov/articles/PMC12286354/ (Munn & Jain 2025)
- https://pmc.ncbi.nlm.nih.gov/articles/PMC5046954/ (automated multi-objective ABM calibration)
- https://classic.genetics.org/bib/article/23/1/bbab387/6383562 (calibration: identifiability, local minima)
- https://www.frontiersin.org/journals/immunology/articles/10.3389/fimmu.2026.1927857/full (uniform params fail per-patient)
- https://www.nature.com/articles/s41540-025-00642-7 (spatial data not yet integrated; PhysiCell-based)
