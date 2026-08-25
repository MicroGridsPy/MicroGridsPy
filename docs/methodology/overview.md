# Methodology Overview

**MicroGridsPy Planning** is a bottom-up, open-source optimization model for the long-term
planning of energy systems in remote and underserved areas. The formulation is implemented
in **Linopy** and is designed to make system sizing, dispatch and economic assumptions
explicit and transparent.

The model explicitly addresses the challenges of energy-system scaling, technology
selection, and operational planning in contexts characterized by **limited data
availability, high uncertainty, and strong economic constraints**.

!!! abstract "Source"
    This section reproduces and explains the *MicroGridsPy — Mathematical Formulation*
    document (A. Onori, December 2025). Where the implemented code and the document differ,
    the code is authoritative; discrepancies should be reported as issues.

## Reference energy system

The reference energy system integrates renewable generation, an energy-storage system, and
backup generation:

- **Renewable generation** — a *generic* renewable technology characterized by general
  parameters, able to represent PV, wind (including power-curve modelling), hydro, or any
  source describable through a production time series and basic cost parameters.
- **Battery storage** — a single aggregated battery bank, parameterized through state of
  charge (SOC), depth of discharge (DoD), and charge/discharge efficiencies.
- **Backup generation** — one or more flexible, dispatchable sources (diesel, biomass, or
  any generator able to meet load when renewables and storage are insufficient).
- **Weak-grid connection** *(optional)* — electricity import/export subject to a
  time-dependent grid-availability matrix.

This modular representation captures the technical and economic interactions between
generation, storage, and dispatch decisions in off-grid and weak-grid contexts.

![Conceptual technology interaction scheme of MicroGridsPy: renewable generators, battery storage, backup generator and optional grid connected to a common AC bus feeding the aggregated load](../assets/methodology/energy_system.png)

*Conceptual technology interaction scheme used in MicroGridsPy. All technologies exchange
power through a common **AC system bus**, with conversion efficiencies applied between each
technology and the bus. The diagram represents the modelled connections rather than a
physical electrical layout; **dashed** elements (grid connection) are optional and activated
through parameter settings.*

## Planning workflow

The conceptual sequence is:

```text
Demand + resource inputs
          ↓
Technology characterization
          ↓
Investment decisions   (capacity sizing — shared across scenarios)
          ↓
Hourly operational decisions   (dispatch — scenario-specific)
          ↓
Economic accounting
          ↓
Least-cost system configuration
```

## Stochastic structure

The optimization is performed at **hourly time resolution** and can simultaneously account
for multiple **scenarios** $\omega \in \Omega$ representing alternative realizations of
time-dependent parameters such as electricity demand, renewable-resource availability, or
grid conditions. Each scenario is assigned a probability $p_\omega$, resulting in a
**single-stage stochastic optimization problem**.

- **Sizing decisions are shared across all scenarios**, ensuring a robust design that
  performs well under diverse future conditions.
- **Operational decisions are optimized separately for each scenario** to minimize expected
  cost.

## Planning modes

Two complementary formulations are available, addressing different levels of temporal
complexity and data availability:

- **[Typical-Year Planning](planning-modes.md#typical-year-planning)** — a *steady-state*
  approximation described by a single representative operating year assumed to repeat
  identically over time.
- **[Multi-Year Planning](planning-modes.md#multi-year-planning)** — a *dynamic*
  formulation over a planning horizon $y = 1,\dots,H$, where both system decisions and
  exogenous parameters may evolve over time.

Both modes are **investment-oriented** and rely on an **annuity-based cost formulation**,
making them suitable for long-term, multi-scenario techno-economic planning. Both can
represent either a fully off-grid (isolated) system or a weakly grid-connected one.

## How the methodology is organized

| Page | Content |
|---|---|
| [Planning Modes](planning-modes.md) | typical-year vs. multi-year formulations and their economic interpretation |
| [Objective Function](objective-function.md) | the NPWC and EAC objectives, CRF, WACC, salvage value |
| [Cost Accounting](cost-accounting.md) | bottom-up investment, operational, and externality costs |
| [Renewable Technologies](renewable.md) | generic renewable production and capacity constraints |
| [Battery](battery.md) | flow, SOC dynamics, and capacity constraints |
| [Generators](generator.md) | installed capacity, fuel–power relationship, part-load curve |
| [Grid Connection](grid.md) | import/export limits and grid-availability simulation |
| [System Constraints](constraints.md) | energy balance, renewable penetration, lost load, land use |
