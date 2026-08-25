# Cost Accounting

MicroGridsPy follows a **bottom-up** cost-accounting approach: every cost component is
explicitly parameterized and mapped to decision variables. The same conceptual structure is
used in both planning modes, but the **temporal treatment** of costs differs between the
typical-year and multi-year formulations.

Total system cost is decomposed into four categories:

1. **Annualized investment costs**,
2. **Fixed operation and maintenance costs**,
3. **Variable operational costs and revenues**,
4. **Externalities and penalty terms**.

Investment-related costs depend on capacity-sizing decisions and are therefore
**scenario-independent**. Most operational costs, revenues, and reliability penalties depend
on scenario-specific dispatch variables. The two modes differ mainly in how time is
represented:

- In the **typical-year** formulation, all costs are interpreted as (steady-state) annual
  equivalents.
- In the **multi-year** formulation, costs are tracked explicitly by year and discounted to
  present value. If capacity expansion is enabled, investments are introduced at discrete steps
  and tracked as **capacity cohorts**, with annualized costs active from the commissioning year
  to the end of the horizon.

## Investment cost

Installed capacity of technology $j$ is unit-based:

\[
C_j = N_j \cdot P_j
\]

where $N_j$ is the number of installed units and $P_j$ the nominal capacity per unit. The
annualized investment cost is

\[
\text{Annuity}_j = C_j \cdot \text{CAPEX}^{\text{eff}}_j \cdot \text{CRF}_j
\]

where $\text{CAPEX}^{\text{eff}}_j = (1-g_j)\,\text{CAPEX}_j$ accounts for investment grants
$g_j$, and $\text{CRF}_j$ is the [capital recovery factor](objective-function.md#annuities-and-the-capital-recovery-factor)
computed from $\text{WACC}_j$ and the lifetime $LT_j$.

## Fixed operation and maintenance cost

Fixed O&M costs are capacity-dependent, hence **scenario-independent**. For technology $j$:

\[
\text{FixedO\&M}_j = C_j \cdot \text{CAPEX}_j \cdot f^{\text{FOM}}_j
\]

where $f^{\text{FOM}}_j$ is the fixed-O&M fraction. In the **typical-year** formulation, total
annual fixed O&M is computed once from installed capacities and added **outside** the scenario
expectation:

\[
\text{FixedO\&M} = \sum_j \text{FixedO\&M}_j
\]

In the **multi-year** formulation, it is computed per active cohort and included in yearly
system costs:

\[
\text{FOM}_y = \sum_{j,k} \alpha_{j,k,y}\cdot \text{FOM}_{j,k}
\]

where $\alpha_{j,k,y}$ is the cohort activation mask.

## Operational costs and revenues

Operational costs depend on dispatch variables at hourly resolution. For each scenario
$\omega$:

**Fuel costs**

\[
\text{FuelCost}_{\omega} = \sum_{t,g} f_{t,\omega,g}\cdot c^{\text{fuel}}_g
\]

**Grid interaction (net cost)**

\[
\text{GridNetCost}_{\omega} = \sum_t \left( e^{\text{imp}}_{t,\omega}\,c^{\text{imp}}_{t,\omega} - e^{\text{exp}}_{t,\omega}\,c^{\text{exp}}_{t,\omega} \right)
\]

**Renewable production subsidies**

\[
\text{Subsidy}_{\omega} = \sum_{t,r} p^{\text{ren}}_{t,\omega,r}\cdot s_r
\]

**Lost-load penalties**

\[
\text{LLCost}_{\omega} = \sum_t \ell_{t,\omega}\cdot c^{\text{LL}}
\]

The expected annual operational cost is the probability-weighted sum across scenarios. Grid
costs and revenues are computed on the **raw** interchange variables at the point of common
coupling — see [Grid Cost and Emissions](grid.md#grid-cost-and-emissions-accounting).

## Externalities

Externalities include direct operational emissions, optional grid-related (scope-2) emissions,
and embodied emissions. In the **typical-year** formulation, embodied emissions are annualized
consistently with the steady-state interpretation:

\[
\text{Externalities}_{\omega} = c^{\text{CO}_2}
\left(
\sum_{t,g} f_{t,\omega,g}\,\epsilon^{\text{fuel}}_g
+ \sum_j \frac{C_j\,\epsilon^{\text{emb}}_j}{LT_j}
+ \sum_t e^{\text{imp}}_{t,\omega}\,\epsilon^{\text{grid}}_t
\right)
\]

where the three terms are direct fuel emissions, annualized embodied emissions, and grid-related
indirect emissions. In the **multi-year** formulation, embodied emissions are tracked explicitly
by year and cohort rather than annualized:

\[
\text{Externalities}_{y,\omega} = c^{\text{CO}_2}
\left(
\sum_{t,g} f_{t,y,\omega,g}\,\epsilon^{\text{fuel}}_g
+ \sum_{j,k} \beta_{j,k,y}\,\epsilon^{\text{emb}}_j
+ \sum_t e^{\text{imp}}_{t,y,\omega}\,\epsilon^{\text{grid}}_t
\right)
\]

where $\beta_{j,k,y}$ activates embodied emissions at commissioning. Direct fuel-emission costs
and optional grid-emission costs are evaluated within each modelled year and scenario, then
discounted together with the other annual system costs.

!!! note "Same economics, different time representation"
    Both modes rely on the same bottom-up cost structure. In the typical-year formulation costs
    are annualized into horizon-independent equivalents; in the multi-year formulation they are
    resolved year by year and discounted to present value. The typical-year model is the
    steady-state limit of the dynamic one.
