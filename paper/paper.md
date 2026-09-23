---
title: 'MicroGridsPy: A bottom-up, open-source optimization model for multi-year planning of mini-grids in energy-access contexts'
tags:
  - Python
  - energy access
  - mini-grids
  - rural electrification
  - energy system optimization
  - linear programming
  - capacity expansion
authors:
  # TODO: confirm the final author list, order, ORCIDs, and corresponding author with all contributors.
  - name: Alessandro Onori
    orcid: 0009-0009-1195-2078
    corresponding: true
    affiliation: 1
  - name: Nicolò Stevanato
    orcid: 0000-0002-3419-0389
    affiliation: 1
  - name: Riccardo Mereu
    orcid: 0000-0003-0544-595X
    affiliation: 1
  - name: Emanuela Colombo
    orcid: 0000-0002-9747-5699
    affiliation: 1
affiliations:
  - name: Department of Energy, Politecnico di Milano, Milan, Italy
    index: 1
date: XXXXX
bibliography: paper.bib
---

# Summary

`MicroGridsPy` is an open-source Python package for the techno-economic planning of
mini-grid energy systems in remote and underserved areas. Given hourly demand and
renewable-resource time series together with techno-economic parameters, it builds and
solves a least-cost capacity-expansion and dispatch optimization problem that decides how
much renewable generation, battery storage, and dispatchable backup to install and how to
operate them across a planning horizon. The reference energy system can combine renewable
generation, battery storage, backup generators, and an optional (possibly weak) grid
connection with import and export. Beyond deterministic planning, `MicroGridsPy` supports
a two-stage stochastic formulation with scenario-dependent recourse, in which uncertainty
can be represented through arbitrary user-defined operating parameters and time-series inputs
while investment decisions are separated from scenario-specific operational responses.

The model is formulated with the `Linopy` [@linopy] optimization framework and hands the problem 
to open-source (`HiGHS`) or commercial (`Gurobi`) solvers. `MicroGridsPy` can be used either as a 
library - a small, stable Python API takes a project from input templates to solved, analysis-ready 
tables - or through an optional guided `Streamlit` graphical interface that scaffolds inputs,
audits data, solves, and visualizes results. The project is
developed openly on [GitHub](https://github.com/MicroGridsPy/MicroGridsPy) with full
[documentation](https://microgridspy-package-docs.readthedocs.io/en/latest/), and each
project is a self-contained folder of CSV, YAML, and JSON files, so studies remain
reproducible and inspectable.


# Statement of need

Planning electricity access in remote areas is a distinctive optimization problem:
demand is uncertain and evolving, capital is expensive and lumpy, resources are highly
variable, and the least-cost system typically mixes renewables, storage, and fuel-based
backup under reliability and policy constraints. General-purpose energy-system frameworks
such as `Calliope` [@calliope], `PyPSA` [@pypsa], and `OSeMOSYS` [@osemosys] are powerful
but are aimed primarily at regional and national power systems; capturing the features
that dominate mini-grid economics — battery ageing, generator part-load behaviour,
staged investment under demand growth, lost-load pricing, and scenario-weighted
uncertainty — requires substantial custom modelling. Widely used practitioner tools for
off-grid sizing, such as `HOMER Pro` [@homerpro], are often commercial, which limits transparency 
and reproducibility in research, while open-source tools such as `Offgridplanner` [@offgridplanner] 
and `CLOVER` [@clover] can provide valuable simulation, system-design, and sizing capabilities for
off-grid applications, including spatial distribution-grid planning, but the key distinction
lies in MicroGridsPy **core planning logic**; capacity expansion is formulated explicitly as a
multi-year planning problem, with a consistent economic formulation linking long-term
investment decisions to high-resolution technical operation and a stochastic
formulation for uncertain operating parameters. This allows technical realism, long-term planning 
and uncertainty treatment to be handled within the same optimization framework rather than as separate analyses.
`MicroGridsPy` targets this gap: a transparent, modular, bottom-up model built
specifically for energy-access planning, packaged so that it is straightforward to install,
script, and extend.

`MicroGridsPy` continues a line of open mini-grid modelling work [@balderrama2019espino]
but represents a substantial redevelopment rather than an incremental release. The present
version contributes: (i) a re-architected, installable Python package with a documented,
stable API and an optional GUI, replacing an earlier script-based workflow; (ii) an
**annuity-based, dual-rate economic formulation** that annualizes investment through a
capital-recovery factor at each technology's weighted average cost of capital while
discounting system cash flows at a social discount rate; (iii) **explicit power-electronic
inverter sizing** for both renewable and battery assets; (iv) a **semi-empirical battery
degradation** model with temperature- and depth-resolved cycle ageing (a depth-resolved
per-state-of-charge-band marginal-cost formulation for Li-ion, kept linear); and (v) a
**consistent treatment of stochasticity and of multi-year capacity expansion**, including
representative typical-year and explicit multi-year formulations that share the same
economic logic. Together these let researchers and practitioners study technology choice,
staged investment under evolving demand, reliability–cost trade-offs, and policy levers
such as carbon pricing and renewable-penetration targets, reproducibly and with an
inspectable model. `MicroGridsPy` is developed openly and has supported teaching and
research in energy-access planning.

# Key features

- Typical-year and multi-year (explicit horizon) planning formulations sharing one
  economic core.
- Off-grid and on-grid (weak-grid) configurations, with optional grid export.
- Continuous or integer (discrete) capacity sizing.
- Single-scenario and scenario-weighted stochastic studies with configurable constraint
  enforcement.
- Renewable, battery, and generator investment with explicit inverter sizing.
- Generator part-load efficiency and a power-dependent battery loss model.
- Semi-empirical, temperature-aware battery calendar and cycle degradation.
- Optional carbon-cost internalization, land-use limits, minimum renewable penetration,
  and lost-load constraints and penalties.
- A small stable Python API, a command-line interface, and an optional Streamlit GUI.

# Acknowledgements

<!-- TODO: add funding sources, grant numbers, and any acknowledged contributors. -->
`MicroGridsPy` builds on earlier open mini-grid modelling work by the original authors of
the model. We thank the contributors listed in the repository's `AUTHORS` file.

# References
