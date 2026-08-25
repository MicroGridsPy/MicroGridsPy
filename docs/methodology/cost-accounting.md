# Cost Accounting

MicroGridsPy follows a **bottom-up** cost-accounting approach: all cost components are
explicitly parameterized and mapped to decision variables. The same conceptual structure is
used in both planning modes, but the *dimensionality* of costs differs between the
typical-year (steady-state) and multi-year (dynamic) formulations.

For each technology $j$, total system cost is decomposed into three components:

1. **Annualized investment costs**, including fixed operation and maintenance;
2. **Variable operational costs and revenues**, dependent on dispatch decisions;
3. **Externalities**, such as emissions and unserved-energy penalties.

Investment-related costs depend only on capacity-sizing decisions and are therefore
**scenario-independent**, while operational costs and externalities depend on
scenario-specific dispatch variables.

## Investment cost

Installed capacity is unit-based (kW or kWh). For technology $j$:

\[
C_j = N_j \cdot P_j
\tag{8}
\]

where $N_j$ is the number of installed units and $P_j$ the nominal capacity per unit. The
annualized investment cost is:

\[
\text{INV}^{ann}_j = C_j \cdot
\Big[ CRF_j\cdot \text{CAPEX}^{eff}_j + \text{CAPEX}_j\cdot \text{FOM}_j \Big]
\tag{9}
\]

where:

- $\text{CAPEX}^{eff}_j = (1-g_j)\,\text{CAPEX}_j$ accounts for possible investment grants $g_j$;
- $\text{FOM}_j$ is the fixed O&M cost as a fraction of CAPEX;
- $CRF_j$ is the [capital recovery factor](objective-function.md#annuities-and-the-capital-recovery-factor)
  from $\text{WACC}_j$ and the technical lifetime.

In the **typical-year** formulation, investment costs are computed once and interpreted as
steady-state annual costs. In the **multi-year** formulation, they are defined per
investment step and translated into year-dependent annuities, enabling phased expansion and
replacements.

## Operational costs

Operational costs depend on dispatch variables, computed at hourly resolution and aggregated
annually. For each scenario $\omega$:

**Fuel costs**

\[
\text{FuelCost}_\omega = \sum_{t,g} f_{t,\omega,g}\cdot c^{fuel}_g
\tag{10}
\]

**Grid interaction costs and revenues** (if enabled)

\[
\text{GridCost}_\omega = \sum_{t}
\left( e^{imp}_{t,\omega}\cdot c^{imp}_{t,\omega} - e^{exp}_{t,\omega}\cdot c^{exp}_{t,\omega} \right)
\tag{11}
\]

**Renewable production subsidies**

\[
\text{Subsidy}_\omega = \sum_{t,r} p^{ren}_{t,\omega,r}\cdot s_r
\tag{12}
\]

**Lost-load penalties**

\[
\text{LLCost}_\omega = \sum_{t} \ell_{t,\omega}\cdot c^{LL}
\tag{13}
\]

The expected annual operational cost is the probability-weighted sum across scenarios.

## Externalities

Externalities include both operational and embodied emissions. For each scenario $\omega$:

\[
\text{EXT}_\omega = c^{CO_2}
\left(
\sum_{t,g} f_{t,\omega,g}\cdot \epsilon^{fuel}_g
+ \sum_j \frac{C_j\cdot \epsilon^{emb}_j}{LT_j}
\right)
\tag{14}
\]

where the first term is direct operational emissions and the second is annualized embodied
emissions from installed capacity.

!!! note "Same economics, different time representation"
    The two modes differ in how time is represented, not in the underlying economic logic.
    In the **typical-year** formulation, investment costs are annualized over the technical
    lifetime, yielding steady-state annual equivalents independent of the chosen horizon. In
    the **multi-year** formulation, time is modelled explicitly: investment, operational, and
    externality costs are resolved year by year and discounted to present value. Both rely on
    the same bottom-up cost structure, so the typical-year model is the steady-state limit of
    the dynamic one.
