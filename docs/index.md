# MicroGridsPy

**MicroGridsPy** is an open-source Python package for the techno-economic planning of
mini-grid energy systems in remote and underserved areas. The planning model is
implemented in **[Linopy](https://linopy.readthedocs.io/)** and couples investment
decisions with hourly operational optimization for renewable generation, battery
storage, dispatchable backup generation, and optional weak-grid interaction.

MicroGridsPy is designed as a transparent, modular tool for energy-access modelling,
with a focus on bottom-up system planning and reproducible optimization workflows.

## What MicroGridsPy does

At a high level, the workflow is:

```text
Project definition
      ↓
Demand and resource characterization
      ↓
Technology and economic inputs
      ↓
Optimization model (Linopy)
      ↓
Capacity sizing + hourly dispatch
      ↓
Costs, KPIs and time-series results
```

The mathematical formulation is based on a bottom-up representation of renewable
technologies, a battery energy-storage system, dispatchable backup generation and,
when enabled, a weak-grid connection. The full derivation is documented in the
[Methodology](methodology/overview.md) section.

## Getting started

### Installation

MicroGridsPy is a pip-installable package with optional solver extras. For example, with
the open-source HiGHS solver:

```bash
pip install "microgridspy[highs]"
```

See [Installation](getting-started/installation.md) for the complete installation
workflow and available solver options.

### Quickstart

A minimal end-to-end workflow:

```python
import microgridspy as mgp

# 1. Create a project folder and its input templates
mgp.create_project(
    "my_site",
    formulation="steady_state",
    resources=["solar", "wind"],
)

# 2. Fill the generated input files with the case-study data, then validate them
mgp.validate_project("my_site")

# 3. Build and solve the optimization; retrieve analysis-ready results
results = mgp.solve("my_site", solver="highs").results()

print(results.kpis)          # pandas DataFrame of headline indicators
mgp.export_results(results)  # write CSV/Excel into the project's results/ folder
```

The exact API should always be checked against the [API Reference](api/index.md), which is
generated from the package source. See [Quickstart](getting-started/quickstart.md) and the
[Tutorials](tutorials/typical-year.md) for complete, reproducible workflows.

## Conceptual model

MicroGridsPy supports two complementary planning formulations:

- **[Typical-year planning](methodology/planning-modes.md#typical-year-planning)** — a
  representative operating year under steady-state assumptions, minimizing an equivalent
  annual system cost.
- **[Multi-year planning](methodology/planning-modes.md#multi-year-planning)** — an explicit
  planning horizon with time-dependent inputs, investment steps, capacity expansion and
  intertemporal economic valuation.

Both formulations can include multiple **scenarios**. Investment (sizing) decisions are
here-and-now decisions shared across scenarios, while operational decisions are
scenario-specific recourse actions, resulting in a **two-stage stochastic** planning problem
with recourse.

## Technology representation

The reference energy system contains four technology groups:

| Component | Represented through | Methodology |
|---|---|---|
| **Renewable generation** | installed capacity, resource-availability time series, conversion efficiency, techno-economic parameters | [Renewable Technologies](methodology/renewable.md) |
| **Battery storage** | one aggregated bank: energy capacity, charge/discharge flows and efficiencies, SOC, depth-of-discharge, cyclic boundary | [Battery](methodology/battery.md) |
| **Backup generation** | one or more dispatchable generators; nominal efficiency or a Willans part-load fuel line with clustered unit commitment | [Generators](methodology/generator.md) |
| **Weak-grid connection** | line capacity, time-dependent availability matrix, import/export efficiencies and prices | [Grid Connection](methodology/grid.md) |

## Optimization structure

At each time step the model enforces an energy balance between supply and demand:

\[
\sum_r E^{res}_{t,\omega,r}
+ E^{gen}_{t,\omega}
+ \eta^{grid} E^{imp}_{t,\omega} - \eta^{grid} E^{exp}_{t,\omega}
+ E^{dis}_{t,\omega} - E^{ch}_{t,\omega}
+ E^{LL}_{t,\omega}
= D_{t,\omega}
\]

where the terms represent renewable production, dispatchable generation, grid exchange,
battery operation, lost load and demand. The objective depends on the selected planning
formulation, but the economic structure combines annualized investment costs with expected
operating costs and, where enabled, externalities. See the
[Objective Function](methodology/objective-function.md).

## Documentation map

- **[Getting Started](getting-started/installation.md)** — install the package and run your first model.
- **[User Guide](user-guide/input-data.md)** — input data, planning modes, model execution and results.
- **[Tutorials](tutorials/typical-year.md)** — complete workflows for representative cases.
- **[Methodology](methodology/overview.md)** — the mathematical and economic formulation.
- **[Data Reference](data-reference/overview.md)** — user-facing inputs and the internal data contract.
- **[API Reference](api/index.md)** — generated automatically from the Python package.
- **[Developers](developers/architecture.md)** — package architecture and contribution workflow.

## From energy-access planning to an integrated modelling ecosystem

MicroGridsPy Planning is intended to operate as part of a broader, interoperable
energy-access modelling workflow built on the **Comprehensive Energy System Planning
(CESP)** methodology. The broader concept connects:

```text
GIS / distribution-grid topology
        ↓
Demand assessment (RAMP)
        ↓
Resource assessment (PVGIS)
        ↓
MicroGridsPy optimization
        ↓
Dispatch / operational analysis
        ↓
Power-flow / network analysis
```

Each stage remains modular while sharing well-defined data interfaces. This separation is
the reason MicroGridsPy keeps an explicit [internal data contract](data-reference/data-contract.md)
between its data-loading and formulation layers.

## Citation and references

If you use MicroGridsPy in your work, please cite the relevant publications from the SESAM
research group at Politecnico di Milano, on whose methodology the tool is based:

- Sergio Balderrama, Francesco Lombardi, Fabio Riva, Walter Canedo, Emanuela Colombo, Sylvain
  Quoilin, *"A two-stage linear programming optimization framework for isolated hybrid
  microgrids in a rural context: The case study of the 'El Espino' community"*, **Energy**,
  2019, 188, 116073.
- Nicolò Stevanato, Francesco Lombardi, Emanuela Colombo, Sergio Balderrama, Sylvain Quoilin,
  *"Two-Stage Stochastic Sizing of a Rural Micro-Grid Based on Stochastic Load Generation"*,
  **2019 IEEE Milan PowerTech**, pp. 1–6.
- Nicolò Stevanato, Francesco Lombardi, Giulia Guidicini, Lorenzo Rinaldi, Sergio L.
  Balderrama, Matija Pavičević, Sylvain Quoilin, Emanuela Colombo, *"Long-term sizing of rural
  microgrids: Accounting for load evolution through multi-step investment plan and stochastic
  optimization"*, **Energy for Sustainable Development**, 2020, 58, pp. 16–29.
- Nicolò Stevanato, Gianluca Pellecchia, Ivan Sangiorgio, Diana Shendrikova, Castro Antonio
  Soares, Riccardo Mereu, Emanuela Colombo, *"Planning third generation minigrids:
  Multi-objective optimization and brownfield investment approaches in modelling village-scale
  on-grid and off-grid energy systems"*, **Renewable and Sustainable Energy Transition**, 2023,
  3, 100053.
- Giacomo Crevani, Castro Soares, Emanuela Colombo, *"Modelling Financing Schemes for Energy
  System Planning: A Mini-Grid Case Study"*, **ECOS 2023**, pp. 1958–1969.
- N. Stevanato, I. Sangiorgio, R. Mereu, E. Colombo, *"Archetypes of Rural Users in Sub-Saharan
  Africa for Load Demand Estimation"*, **2023 IEEE PES/IAS PowerAfrica**, Marrakech, Morocco,
  2023, pp. 1–5, doi: [10.1109/PowerAfrica57932.2023.10363287](https://doi.org/10.1109/PowerAfrica57932.2023.10363287).

## Online course

A free, self-paced online course introduces MicroGridsPy and the broader Comprehensive Energy
System Planning (CESP) methodology for energy-access planning:

- **[Comprehensive Energy System Planning for Energy Access](https://www.open.edu/openlearncreate/course/view.php?id=17733)**
  (OpenLearn Create) — walks through the modelling workflow, from demand and resource
  assessment to mini-grid optimization with MicroGridsPy, with hands-on material and case
  studies.
