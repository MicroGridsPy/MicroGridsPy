# Planning Modes

MicroGridsPy supports two complementary modelling modes, addressing different levels of
temporal complexity and data availability:

- **Multi-year planning mode** (dynamic);
- **Typical-year planning mode** (steady-state).

Both are **investment-oriented** and rely on an **annuity-based cost formulation**, making
them suitable for long-term, multi-scenario techno-economic planning. In both cases the model
minimizes the **expected total system cost** — annuitized investment costs (with capital
recovery), operating costs, and optional externalities.

The optimization runs at **hourly resolution** and can account for multiple **scenarios**
representing alternative realizations of demand, renewable availability, or grid conditions,
each with a probability. The resulting problem is a **two-stage stochastic optimization with
recourse**, solved in deterministic-equivalent form: sizing and investment are here-and-now
decisions shared across scenarios, while operational decisions are scenario-dependent recourse
actions. Both modes can represent a fully off-grid or a weakly grid-connected system through a
**grid-availability matrix**.

## What the total system cost includes

- **Investment costs** — annualized using a technology-specific WACC to reflect the
  opportunity cost of capital, financing conditions, and risk premia. Here the WACC is used
  solely within the annuity formulation and does not model private bankability.
- **Operating costs** — fuel, maintenance, and replacement expenditures.
- **Externalities** *(optional)* — social or environmental damages such as CO₂ emissions,
  internalized through cost adders.

In the **multi-year** formulation, a **social discount rate** discounts future costs to
present value. This rate is conceptually distinct from the WACC: the WACC captures the cost of
financing capital equipment, while the social discount rate reflects society's valuation of
future expenditures and long-term benefits.

This structure captures the key long-term trade-offs in mini-grid planning: **CAPEX vs OPEX**
substitution (e.g. PV + battery vs diesel), **renewable integration** and **emissions
reduction** under externality pricing, **grid interaction** under variable pricing and
availability, and **reliability vs cost**.

!!! note "Public planning, not private appraisal"
    The model does not incorporate tariffs, revenues, profitability metrics, or affordability
    constraints. Outputs are intended to support **policy-making, planning, and techno-economic
    analysis**, not private investment appraisal. Private bankability and financial feasibility
    are instead evaluated in post-processing if required. This preserves a clean separation
    between **economic least-cost planning** (public view) and **financial viability analysis**
    (private view), which generally require different discounting and risk assumptions.

## Multi-Year Planning

The multi-year mode is the most comprehensive formulation. It is defined over a horizon
$y = 1,\dots,H$, where both system decisions and exogenous parameters may evolve over time.
Time-dependent inputs — demand, renewable availability, prices, grid conditions — are indexed
by **year** and **scenario**.

It is formulated as a **two-stage stochastic capacity-expansion problem with recourse** and
captures three key effects:

- **Monotone capacity expansion.** Investments are phased across predefined planning steps,
  letting the system grow over time while enforcing non-decreasing installed capacity and
  modelling technology roll-out through cohort-specific capacity additions.
- **Intertemporal economic valuation.** All system costs are evaluated in present-value terms
  using a **dual-rate logic**: capital recovery uses technology-specific financial discount
  rates ($\text{WACC}_j$), while system-level discounting uses a **social discount rate**
  $r_s$.
- **Cohort-based annuity persistence.** Once an investment cohort is activated, its annualized
  cost stream remains active over the remaining modelled horizon through an implicit
  like-for-like replacement logic. Replacement expenditures are therefore represented through
  the persistence of the annuity stream rather than separate overnight reinvestment terms.

The objective is the **discounted expected system cost within the modelled horizon** — see
[Objective Function → Multi-Year](objective-function.md#multi-year-planning).

### Investment cohorts

Capacity expansion is not restricted to the initial year but can occur at discrete
**investment steps** $\tau$ (equivalently, cohorts $k$), each commissioned at a specific year.
Each cohort is characterized by its installation time, technical lifetime, and financial
parameters, and contributes annualized costs from its commissioning year onward.

## Typical-Year Planning

The typical-year mode is a tractable **steady-state** approximation of long-term economics.
The system is described by a single representative operating year assumed to repeat
identically over time, so the objective reduces to minimizing the **expected annual (welfare)
cost**.

It is well suited to systems assumed to have reached long-term equilibrium, where key
time-varying parameters (most notably demand) are not expected to evolve significantly. It can
be interpreted as a **collapsed** version of the multi-year model under **single-year
operation**: load, resource availability, performance, and operating conditions are identical
every year; inter-annual variability, demand growth, technology learning, and degradation are
neglected.

Under this assumption, the annuity-based investment cost becomes mathematically equivalent to
an **infinite discounted sequence of identical replacements** — the system is implicitly
assumed to operate indefinitely in steady state, each asset replaced by an identical one at
end of life. The objective is the **expected equivalent annual cost (EAC)** — see
[Objective Function → Typical-Year](objective-function.md#typical-year-planning).

## Choosing a mode

| | Typical-year | Multi-year |
|---|---|---|
| Formulation | steady-state | dynamic |
| Time representation | one representative year | explicit horizon $y=1,\dots,H$ |
| Objective | expected annual cost (EAC) | discounted expected cost (NPWC) |
| Capacity expansion | — | phased investment steps, non-decreasing |
| Cohorts | single block | cohort-based (year- and step-indexed) |
| Discounting affects sizing? | no | yes (social discount rate) |
| Typical use | screening, steady-state, tractability | long-term planning, phased investment |

Both modes rely on the same bottom-up [cost structure](cost-accounting.md), so the typical-year
model is the steady-state limit of the dynamic one under time-invariant conditions.
