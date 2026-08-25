# Planning Modes

MicroGridsPy supports two complementary modelling modes. Both are investment-oriented,
rely on an annuity-based cost formulation, and minimize an **expected total system cost**
that includes annuitized investment costs (with capital recovery), operating costs, and
optional externalities.

## Typical-Year Planning

The **typical-year planning mode** is a tractable **steady-state** approximation of
long-term system economics. The system is described by a single representative operating
year assumed to repeat identically over time, so the objective reduces to minimizing the
**expected annual (welfare) cost**.

It can be interpreted as a *collapsed* version of the multi-year model under the assumption
of **single-year operation**: load demand, resource availability, technology performance,
and operating conditions are assumed identical in every year. Inter-annual variability,
demand growth, technology learning, and degradation are neglected.

Under this assumption, the annuity-based investment cost becomes mathematically equivalent
to an **infinite discounted sequence of identical replacements** — each asset is implicitly
replaced by an identical one at the end of its technical lifetime, and the system operates
indefinitely in a steady-state regime.

This mode is particularly suited to:

- steady-state or mature systems;
- early-stage feasibility studies;
- comparative technology assessments;
- stochastic analyses with multiple scenarios, where computational tractability is a priority.

!!! note "Discounting does not affect sizing in typical-year mode"
    Because all costs are evaluated on an annual basis and the system is assumed to operate
    indefinitely under stationary conditions, **intertemporal discounting does not affect
    system sizing**. Annuity-based capital recovery already embeds discounting at the asset
    level through the WACC. System sizing is therefore driven exclusively by the trade-off
    between annualized investment costs and expected annual operating costs.

The objective is the **expected equivalent annual cost (EAC)** — see
[Objective Function](objective-function.md#typical-year-planning).

## Multi-Year Planning

The **multi-year planning mode** is the most comprehensive formulation. It is defined over
a multi-year planning horizon $y = 1,\dots,H$, where both system decisions and exogenous
parameters may evolve over time. Time-dependent inputs — demand, renewable availability,
prices, grid conditions — are explicitly indexed by **year** and **scenario**.

It is formulated as a **single-stage stochastic capacity-expansion problem** and captures
three key effects:

- **Monotone capacity expansion.** Investments are phased across predefined planning
  steps, allowing the system to grow over time while enforcing non-decreasing installed
  capacity and explicitly modelling technology roll-out and replacement cycles.
- **Intertemporal economic valuation.** All system costs are evaluated in present-value
  terms using a **dual-rate logic**: capital recovery uses technology-specific financial
  discount rates ($\text{WACC}_j$), while system-level discounting uses a **social discount
  rate** $r_s$.
- **Residual value of long-lived assets.** An economically consistent **salvage value** is
  credited for assets whose technical lifetime exceeds the horizon, avoiding short-horizon
  bias and ensuring neutrality between early and late investments.

The objective is the **expected Net Present Welfare Cost (NPWC)** — see
[Objective Function](objective-function.md#multi-year-planning).

### Investment cohorts

In the multi-year formulation, capacity expansion is not restricted to the initial year but
can occur at discrete **investment steps** $\tau$, each corresponding to a commissioning
year within the horizon. Each step defines a distinct **investment cohort**, characterized
by its installation time, technical lifetime, and financial parameters. Rather than charging
the full capital expenditure at installation, each cohort is converted into an equivalent
stream of constant annual payments (an *annuity*) over its technical lifetime; those
payments contribute to system cost only for the years in which the asset is operational.

## Choosing a mode

| | Typical-year | Multi-year |
|---|---|---|
| Formulation | steady-state | dynamic |
| Time representation | one representative year | explicit horizon $y=1,\dots,H$ |
| Objective | expected annual cost (EAC) | expected Net Present Welfare Cost (NPWC) |
| Capacity expansion | — | phased investment steps, non-decreasing |
| Discounting affects sizing? | no | yes (social discount rate) |
| Salvage value | not applicable | credited for long-lived assets |
| Typical use | screening, steady-state, tractability | long-term planning, phased investment |

Both modes rely on the **same bottom-up cost structure**, so the typical-year model can be
interpreted as the steady-state limit of the dynamic formulation under time-invariant
conditions.
