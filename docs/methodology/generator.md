# Backup Generators

MicroGridsPy models dispatchable backup generation through a single generator technology
representing the backup unit of the mini-grid, described by a unit-based sizing variable and an
hourly production variable. Fuel consumption is modelled explicitly and linked to electrical
output through either a **nominal-efficiency relationship** or a **partial-load efficiency
curve** represented as a convex piecewise-linear epigraph.

The same structure is used in both modes; in the **multi-year** formulation, generator
investment and operation are **cohort-based**, so production limits and fuel relations are
indexed by year $y$ and step $k$. At hourly resolution $\Delta t = 1\,\text{h}$, generation in
kWh over one step equals average power in kW.

## Installed capacity and production limit

### Typical-year formulation

The generator is sized in discrete units $N^{\text{gen}}$, each with nominal capacity
$P^{\text{gen}}$ (kW), for a total $C^{\text{gen}} = N^{\text{gen}} \cdot P^{\text{gen}}$.
Hourly production is bounded by installed capacity, with an optional maximum-installable bound:

\[
E^{\text{gen}}_{t,\omega} \le N^{\text{gen}} \cdot P^{\text{gen}} \qquad \forall t,\omega,
\qquad\qquad
N^{\text{gen}} \cdot P^{\text{gen}} \le \overline{C}^{\text{gen}}
\]

### Multi-year formulation

Generator investment is cohort-based. Each step $k$ introduces $N^{\text{gen}}_{k}$ units, with
nominal cohort capacity $C^{\text{gen}}_{k} = N^{\text{gen}}_{k} \cdot P^{\text{gen}}$. The
available cohort capacity in year $y$ is

\[
\widetilde{C}^{\text{gen}}_{y,k} = N^{\text{gen}}_{k}\cdot P^{\text{gen}}\cdot \alpha_{y,k}\cdot \delta_{y,k}
\]

where $\alpha_{y,k}$ is the cohort activity/replacement mask and $\delta_{y,k}$ an optional
exogenous degradation factor. Production is bounded cohort by cohort and aggregated:

\[
E^{\text{gen}}_{t,y,\omega,k} \le \widetilde{C}^{\text{gen}}_{y,k} \qquad \forall t,y,\omega,k,
\qquad\qquad
E^{\text{gen,tot}}_{t,y,\omega} = \sum_k E^{\text{gen}}_{t,y,\omega,k}
\]

The maximum-installable bound applies to the cumulative design:
$\sum_k N^{\text{gen}}_{k} \cdot P^{\text{gen}} \le \overline{C}^{\text{gen}}$.

## Fuel–power relationship (nominal efficiency)

When partial-load modelling is disabled, fuel consumption is linked to output through a constant
nominal efficiency $\eta^{\text{nom}}$ and the fuel lower heating value $\text{LHV}$:

\[
E^{\text{gen}}_{t,\omega} = F_{t,\omega}\cdot \text{LHV}\cdot \eta^{\text{nom}}
\qquad\text{(typical-year)}
\]

\[
E^{\text{gen}}_{t,y,\omega,k} = F_{t,y,\omega,k}\cdot \text{LHV}\cdot \eta^{\text{nom}}
\qquad\text{(multi-year)}
\]

where $F$ is fuel consumption in units consistent with the LHV. The implied specific fuel
consumption is constant over the whole operating range.

## Partial-load efficiency and piecewise-linear approximation

When partial-load modelling is enabled, efficiency becomes output-dependent and is represented
through a **convex piecewise-linear epigraph** of fuel consumption. The curve is provided as
relative loading breakpoints $r_b \in [0,1]$ with efficiencies $\eta_b$.

### Typical-year formulation

At each breakpoint $b$, the output and fuel per unit are $p_b = P^{\text{gen}} r_b$ and
$f_b = p_b / (\eta_b\,\text{LHV})$, and the segment slope is $m_b = (f_{b+1}-f_b)/(p_{b+1}-p_b)$.
Fuel consumption lies above all affine secants:

\[
F_{t,\omega} \ge m_b\left( E^{\text{gen}}_{t,\omega} - N^{\text{gen}}\,p_b \right) + N^{\text{gen}}\,f_b
\qquad \forall t,\omega,b
\]

### Multi-year formulation

The same curve is applied cohort by cohort, scaled by the active available capacity:

\[
F_{t,y,\omega,k} \ge \widehat{m}_{b}\, E^{\text{gen}}_{t,y,\omega,k} + \widehat{q}_{b}\, \widetilde{C}^{\text{gen}}_{y,k}
\qquad \forall t,y,\omega,k,b
\]

where $\widehat{m}_{b}, \widehat{q}_{b}$ are the affine coefficients derived from the relative
efficiency curve — algebraically equivalent to scaling the piecewise fuel curve by the active
cohort capacity.

![Generator efficiency: left, a real efficiency curve compared with a constant-efficiency approximation; right, the curve sampled at relative-output breakpoints to build the piecewise-linear approximation](../assets/methodology/partial_load_curve.png)

*Generator efficiency under the constant and partial-load formulations. **Left:** a real
generator efficiency curve versus the constant-efficiency approximation — real efficiency falls
sharply at low load. **Right:** the efficiency curve sampled at relative-output breakpoints, used
to construct the convex piecewise-linear approximation. The approximation guarantees fuel
consumption is **not underestimated** while preserving linearity.*

!!! note "Convexity, and what is not modelled"
    The partial-load formulation is valid when the implied fuel-consumption curve is **convex**
    in electrical output (specific fuel consumption worsens at lower load — realistic for
    backup diesel generators). Convexity of the input curve is **validated during
    preprocessing**. The formulation is deliberately continuous and linear: **no mixed-integer
    unit commitment** (on/off, startup/shutdown costs, minimum up/down times) and **no minimum
    stable output** are modelled, so the generator may run continuously at low output if that is
    optimal within the convex fuel envelope.
