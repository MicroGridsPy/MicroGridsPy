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
date: 23 September 2026
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

The model is formulated with the `Linopy` [@Hofmann2023] optimization framework and hands the problem 
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
backup under reliability and policy constraints. General-purpose energy-system
frameworks such as `Calliope` [@calliope], `PyPSA` [@pypsa], and `OSeMOSYS`
[@osemosys] are aimed primarily at regional and national power systems, so the features
that dominate mini-grid economics - battery ageing, generator part-load behaviour,
staged investment under demand growth, lost-load pricing, and scenario-weighted
uncertainty - require substantial custom modelling.

Tools built specifically for off-grid sizing are closer to the problem. `HOMER`
[@lambert2006homer] is the practitioner standard, but it is commercial, which limits
transparency and reproducibility in research. `Offgridplanner` [@offgridplanner] and
`CLOVER` [@Sandwell2023] are open source and offer valuable simulation, system-design
and sizing capabilities, including spatial distribution-grid planning.

`MicroGridsPy` differs in its core planning logic. Capacity expansion is formulated
explicitly as a multi-year problem; a single economic formulation links long-term
investment decisions to high-resolution technical operation; and uncertain operating
parameters are treated stochastically within the same optimization problem rather than
through separate analyses. The result is a transparent, modular, bottom-up model built
for energy-access planning and packaged so that it is straightforward to install,
script, and extend.

`MicroGridsPy` continues a line of open mini-grid modelling work [@balderrama2019espino]
but is a substantial redevelopment rather than an incremental release. It contributes
(i) a re-architected, installable Python package with a documented API and an optional
GUI, replacing an earlier script-based workflow; (ii) an **annuity-based, dual-rate
economic formulation**, annualizing investment through a capital-recovery factor at each
technology's weighted average cost of capital while discounting cash flows at a social
discount rate; (iii) **explicit power-electronic inverter sizing** for renewable and
battery assets; (iv) a **semi-empirical battery degradation** model with temperature-
and depth-resolved cycle ageing, kept linear through a per-state-of-charge-band
marginal-cost formulation; and (v) **consistent treatment of stochasticity and
multi-year capacity expansion**, with typical-year and explicit multi-year formulations
sharing one economic core. Together these support studies of technology choice, staged
investment under evolving demand, reliability–cost trade-offs, and policy levers such as
carbon pricing and renewable-penetration targets. 

`MicroGridsPy` has been applied in peer-reviewed studies of rural electrification,
including multi-year sizing under evolving demand [@stevanato2020myce], coupling with
spatial electrification planning [@penabalderrama2020onsset], multi-objective and
brownfield mini-grid design [@stevanato2023thirdgen], and off-grid planning for a rural
community in Nigeria [@agbo2025dugub]; the repository's `pubs_list.md` records the full
publication history. It is also used in teaching at Politecnico di Milano, in the courses
*Engineering and Cooperation for Development* and *Innovative Technologies for Energy*,
and in international capacity-building programmes: the Climate Compatible Growth *Energy
Modelling Platform for Africa*, hosted by the Ghana Institute of Management and Public
Administration (Accra, 2024), the UN Economic Commission for Africa (Addis Ababa, 2025)
and the University of Cape Town (2026); and the European Union--African Union LEAP-RE
*RESchools* (Pretoria, 2022; Kigali, 2023; Milan, 2024) [@leapre_d45].

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

Part of the development of `MicroGridsPy` was carried out as research within the LEAP-RE
project, which has received funding from the European Union's Horizon 2020 research and
innovation programme under grant agreement No 963530. The content of this publication
reflects only the authors' view; the European Commission is not responsible for any use
that may be made of the information it contains.

`MicroGridsPy` originates from the mini-grid optimization model developed by Sergio
Balderrama and Sylvain Quoilin at the Université de Liège [@balderrama2019espino], whose
formulation underpins the present redevelopment. We thank them, and all contributors
listed in the repository's `AUTHORS` file.

# AI usage disclosure

Generative AI tools were used during the development of `MicroGridsPy` and in the
preparation of this paper. Claude (Anthropic, Opus and Sonnet model families) and ChatGPT 
(OpenAI, GPT-4o and GPT-5 families) were used for: code generation, refactoring
and test scaffolding during the migration of the codebase from Pyomo to `Linopy` and
its packaging; drafting and copy-editing of the documentation; repository and
continuous-integration configuration; and drafting and copy-editing of parts of this
manuscript.

The scientific content of the software was specified by the human authors: the
optimization formulation, the economic model, the battery-degradation representation,
the multi-year and stochastic formulations, and the validation of model results are
the authors' own work. All AI-assisted outputs - code, tests, documentation and text -
were reviewed, edited and validated by the human authors, who made all core design
decisions and take full responsibility for the content of the software and of this
paper.

# References
