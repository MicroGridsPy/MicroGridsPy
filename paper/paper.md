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
    affiliation: '1'
  - name: Nicolò Stevanato
    orcid: 0000-0002-3419-0389
    affiliation: '1'
  - name: Emanuela Colombo
    orcid: 0000-0002-9747-5699
    affiliation: '1'
  - name: Riccardo Mereu
    orcid: 0000-0003-0544-595X
    affiliation: '1'
affiliations:
  - name: Department of Energy, Politecnico di Milano, Milan, Italy
    index: 1
date: 25 September 2026
bibliography: paper.bib
---

# Summary

Many communities in remote regions are not reached by a national electricity grid. Mini-grids - small local electricity systems built around renewable generation, storage, and backup generators - are one of the main ways to supply them, but designing one means deciding what to build, how large, in what order, and at what cost.

`MicroGridsPy` is an open-source Python package that supports these decisions. Given electricity-demand and renewable-resource time series together with technical and economic assumptions, it builds and solves an optimization model that determines which generation and storage assets to install, when to expand them, and how to operate them over time. Systems can combine renewable generation, battery storage, backup generators, and an optional grid connection with import and export. The package supports both representative-year and explicit multi-year planning, and can account for uncertain future conditions by optimizing across several scenarios at once.

The optimization core is implemented with `Linopy` [@Hofmann2023] and can use the open-source `HiGHS` solver [@Huangfu2018highs] or commercial `Gurobi` [@gurobi2026]. `MicroGridsPy` is available as a Python library, a command-line interface, and an optional `Streamlit` graphical interface. Projects use structured CSV, YAML, and JSON inputs and store results in self-contained project folders, supporting reproducible and inspectable analyses. The package is openly developed on [GitHub](https://github.com/MicroGridsPy/MicroGridsPy) and documented at [Read the Docs](https://microgridspy-package-docs.readthedocs.io/en/latest/).

# Statement of need

Planning electricity access in remote areas requires decisions that couple uncertain and evolving demand with variable renewable resources, high capital costs, reliability requirements, and limited technical data. Planners need to compare renewable generation, storage, and dispatchable backup; account for demand growth and staged investment; and evaluate the cost and reliability consequences of uncertainty. The planning problem is therefore not limited to identifying a least-cost technology mix for a single representative year: the timing of investment, the ageing of assets, and the treatment of unserved demand all shape the result.

Energy-access planning is also broader than technical sizing, as the Comprehensive Energy Solution Planning (CESP) framework sets out in connecting engineering analysis with wider social, contextual, and project-planning considerations [@Colombo_2024]. Within that perspective, `MicroGridsPy` addresses the techno-economic optimization layer: it provides a transparent, bottom-up formulation for system design and operation that jointly represents long-term investment decisions, high-resolution operation, economic costs, carbon-related environmental impacts, the social cost of unmet demand, and uncertainty.

The primary users are researchers, energy planners, and practitioners studying rural electrification, mini-grid design, and long-term energy-access strategies who need an open and extensible alternative to proprietary optimization software or to substantial custom model development.

# State of the field

General-purpose energy-system frameworks such as `Calliope` [@calliope], `PyPSA` [@pypsa], and `OSeMOSYS` [@osemosys] are powerful open-source tools for energy-system optimization, but they are aimed primarily at regional and national power systems. Representing the features that dominate mini-grid economics - battery ageing, generator part-load behaviour, staged investment under demand growth, lost-load pricing, and scenario-weighted uncertainty - therefore requires substantial additional model development.

Tools built specifically for off-grid systems are closer to this use case. `HOMER` [@lambert2006homer] is the practitioner standard for hybrid-system sizing but is proprietary, which limits transparency and reproducibility in research. `Offgridplanner` [@offgridplanner] and `CLOVER` [@Sandwell2023] are open source and offer strong capabilities in system design, simulation, and spatial distribution planning. `MicroGridsPy` differs in formulating capacity expansion explicitly as a multi-year optimization problem, with stochastic recourse and mini-grid-specific component representations inside a single economic formulation.

`MicroGridsPy` continues a line of open mini-grid modelling work [@balderrama2019espino], but the present version is a substantial redevelopment rather than an incremental release. It contributes (i) a re-architected, installable Python package with a documented API, a command-line interface, and an optional graphical interface, replacing an earlier script-based workflow; (ii) a migration of the optimization core from Pyomo to `Linopy`; (iii) an annuity-based, dual-rate economic formulation; (iv) explicit power-electronic inverter sizing and a semi-empirical battery degradation model; and (v) typical-year and explicit multi-year formulations sharing a single economic core, with a consistent treatment of stochasticity across both. Together these support studies of technology choice, staged investment under evolving demand, reliability–cost trade-offs, and policy levers such as carbon pricing and renewable-penetration targets.

# Software design

The mathematical model is formulated in `Linopy`, separating model construction from solver execution and allowing the same formulation to be used from scripts, notebooks, the command line, or the graphical interface. `HiGHS` provides the open-source solver option, while `Gurobi` is supported for studies that use a commercial solver.

Two planning formulations share the same economic and technical modelling principles. The typical-year formulation represents the system with a recurring representative year and is intended for compact screening studies. The multi-year formulation represents an explicit planning horizon and introduces time-dependent investment decisions, capacity expansion, and the timing of operating and capital costs. This separation is a deliberate trade-off: users can choose a simpler formulation when temporal investment effects are not central, while retaining a common modelling architecture for long-term studies.

The model annualizes investment through a capital-recovery factor at each technology's weighted average cost of capital while discounting cash flows at a social discount rate, and can represent technology replacement and remaining asset value in multi-year studies. For storage, it incorporates a semi-empirical degradation model with temperature- and depth-resolved cycle ageing, kept linear through a per-state-of-charge-band marginal-cost formulation. Renewable and battery assets can include explicit inverter sizing, and generator operation can account for partial-load efficiency. These choices add modelling detail where it can materially affect mini-grid design while preserving a tractable linear or mixed-integer formulation.

Uncertainty is incorporated within the optimization rather than treated only as a post-processing analysis. In the stochastic formulation, investment decisions are separated from scenario-dependent operational recourse, allowing uncertain resource or demand trajectories and other operating parameters to influence both system design and dispatch. Additional constraints and objective terms can represent land availability, renewable-penetration targets, lost-load limits and penalties, and carbon costs.

The same core formulation is exposed through the Python API, the command-line interface, and an optional `Streamlit` workflow that follows the planning sequence of project definition, input generation and validation, optimization, and result inspection. Project data are stored as CSV, YAML, and JSON files in self-contained folders. This imposes some up-front structure on inputs in exchange for reproducibility, explicit configuration, and a clear separation between the modelling layer and the user interface.

# Research impact statement

The modelling approach underlying `MicroGridsPy` has been applied in peer-reviewed studies of rural electrification, including multi-year sizing under evolving demand [@stevanato2020myce], coupling with spatial electrification planning [@penabalderrama2020onsset], multi-objective and brownfield mini-grid design [@stevanato2023thirdgen], and off-grid planning for a rural community in Nigeria [@agbo2025dugub]; the repository's `pubs_list.md` records the full publication history. Those studies used earlier implementations of the model; the package described here preserves and extends their formulation while making it installable, documented, and testable.

`MicroGridsPy` is also used in teaching at Politecnico di Milano, in the courses *Engineering and Cooperation for Development* and *Innovative Technologies for Energy*, and in international capacity-building programmes: the Climate Compatible Growth *Energy Modelling Platform for Africa*, hosted by the Ghana Institute of Management and Public Administration (Accra, 2024), the UN Economic Commission for Africa (Addis Ababa, 2025) and the University of Cape Town (2026); and the European Union--African Union LEAP-RE *RESchools* (Pretoria, 2022; Kigali, 2023; Milan, 2024) [@leapre_d45].

The repository is maintained for continued community use: an automated test suite runs in continuous integration across Python 3.10–3.12 alongside linting and coverage reporting, the package ships runnable end-to-end examples for both planning formulations, and contribution guidelines, a code of conduct, and full API and methodology documentation are maintained alongside the code.

# AI usage disclosure

Generative AI tools were used during the development of `MicroGridsPy` and in the preparation of this manuscript. Claude (Anthropic, Opus and Sonnet model families) and ChatGPT (OpenAI, GPT-4o and GPT-5 model families) assisted with code generation, refactoring, and test scaffolding during the migration of the codebase from Pyomo to `Linopy` and its packaging; with documentation and repository and continuous-integration configuration; and with drafting and copy-editing parts of this manuscript.

The scientific content of the software was specified by the human authors: the optimization formulation, the economic model, the battery-degradation representation, and the multi-year and stochastic formulations are the authors' own work. The correctness of AI-assisted code was verified by the authors' review of each constraint against the intended mathematical formulation, and by an automated test suite covering the economic, degradation, inverter-sizing, partial-load, and public-API components, which is executed in continuous integration across all supported Python versions. All AI-assisted text was reviewed and edited by the authors, who made every design decision and take full responsibility for the software and for this manuscript.

# Conflict of interest

The authors declare no conflicts of interest.

# Acknowledgements

Part of the development of `MicroGridsPy` was carried out as research within the LEAP-RE project, which has received funding from the European Union's Horizon 2020 research and innovation programme under grant agreement No. 963530. The content of this publication reflects only the authors' view; the European Commission is not responsible for any use that may be made of the information it contains.

`MicroGridsPy` originates from the mini-grid optimization model developed by Sergio Balderrama and Sylvain Quoilin at the Université de Liège [@balderrama2019espino], whose formulation underpins the present redevelopment. We thank them, and all contributors listed in the repository's `AUTHORS` file.

# References
