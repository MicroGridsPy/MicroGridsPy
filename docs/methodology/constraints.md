# System Constraints

The system-level constraints couple all technologies and ensure feasibility of supply,
reliability, and policy or resource limits. Constraints are enforced at hourly resolution for
each scenario; aggregate constraints may additionally apply annually.

## Energy balance constraint

At each time step, total net supply equals demand. MicroGridsPy adopts the convention that
storage charging and grid export act as demand-side sinks, while storage discharging and grid
import act as supply-side sources. Grid flows enter **after** multiplication by the grid
efficiency $\eta^{\text{grid}}$ (see the [PCC convention](grid.md#grid-efficiency-in-the-energy-balance)).

### Typical-year formulation

For each $t\in\mathcal{T}$ and $\omega\in\Omega$:

\[
\sum_{r} E^{\text{res}}_{t,\omega,r}
+ E^{\text{gen}}_{t,\omega}
+ \eta^{\text{grid}} E^{\text{imp}}_{t,\omega}
- \eta^{\text{grid}} E^{\text{exp}}_{t,\omega}
+ E^{\text{dis}}_{t,\omega}
- E^{\text{ch}}_{t,\omega}
+ E^{\text{LL}}_{t,\omega}
= D_{t,\omega}
\]

where $\sum_r E^{\text{res}}$ is total renewable generation, $E^{\text{gen}}$ generator
production, $E^{\text{imp}}/E^{\text{exp}}$ the raw grid flows at the PCC, $E^{\text{dis}}/
E^{\text{ch}}$ battery discharge/charge on the AC-side balance, $E^{\text{LL}}$ lost load (a
slack supply term ensuring feasibility), and $D$ demand.

### Multi-year formulation

Generator and battery operations are cohort-indexed and summed across investment steps:

\[
\sum_{r} E^{\text{res}}_{t,y,\omega,r}
+ \sum_k E^{\text{gen}}_{t,y,\omega,k}
+ \eta^{\text{grid}} E^{\text{imp}}_{t,y,\omega}
- \eta^{\text{grid}} E^{\text{exp}}_{t,y,\omega}
+ \sum_k E^{\text{dis}}_{t,y,\omega,k}
- \sum_k E^{\text{ch}}_{t,y,\omega,k}
+ E^{\text{LL}}_{t,y,\omega}
= D_{t,y,\omega}
\]

## Minimum renewable penetration

A minimum renewable-penetration constraint can represent policy or sustainability targets. It is
defined on **served supply components**, not total load: renewable generation contributes to both
the numerator and the denominator; generator output contributes only to the denominator; only
the renewable share $\rho^{\text{grid}}\in[0,1]$ of **delivered** grid imports contributes to the
numerator; lost load and exports do not enter the ratio.

### Typical-year formulation

For each scenario $\omega$:

\[
E^{\text{tot}}_{\omega} = \sum_t \left( \sum_r E^{\text{res}}_{t,\omega,r} + E^{\text{gen}}_{t,\omega} + \eta^{\text{grid}} E^{\text{imp}}_{t,\omega} \right),
\]
\[
E^{\text{ren}}_{\omega} = \sum_t \left( \sum_r E^{\text{res}}_{t,\omega,r} + \rho^{\text{grid}}\,\eta^{\text{grid}} E^{\text{imp}}_{t,\omega} \right)
\]

The constraint is imposed either **scenario-wise** or in **expectation**:

\[
E^{\text{ren}}_{\omega} \ge \alpha^{\text{ren}}_{\min,\omega}\, E^{\text{tot}}_{\omega} \quad \forall\omega,
\qquad\text{or}\qquad
\sum_{\omega} p_{\omega} E^{\text{ren}}_{\omega} \ge \alpha^{\text{ren}}_{\min} \sum_{\omega} p_{\omega} E^{\text{tot}}_{\omega}
\]

### Multi-year formulation

The same logic applies **year by year**, with $E^{\text{tot}}_{y,\omega}$ and
$E^{\text{ren}}_{y,\omega}$ defined analogously (summing generator output over cohorts):

\[
E^{\text{ren}}_{y,\omega} \ge \alpha^{\text{ren}}_{\min,y,\omega}\, E^{\text{tot}}_{y,\omega} \quad \forall y,\omega,
\qquad\text{or}\qquad
\sum_{\omega} p_{\omega} E^{\text{ren}}_{y,\omega} \ge \alpha^{\text{ren}}_{\min,y} \sum_{\omega} p_{\omega} E^{\text{tot}}_{y,\omega} \quad \forall y
\]

## Maximum lost-load share

Reliability can be enforced through an upper bound on the fraction of demand that may remain
unserved. **Typical-year**, with $E^{\text{LL}}_{\omega} = \sum_t E^{\text{LL}}_{t,\omega}$ and
$E^{\text{dem}}_{\omega} = \sum_t D_{t,\omega}$:

\[
E^{\text{LL}}_{\omega} \le \alpha^{\text{LL}}_{\max,\omega}\, E^{\text{dem}}_{\omega} \quad \forall\omega,
\qquad\text{or}\qquad
\sum_{\omega} p_{\omega} E^{\text{LL}}_{\omega} \le \alpha^{\text{LL}}_{\max} \sum_{\omega} p_{\omega} E^{\text{dem}}_{\omega}
\]

**Multi-year**, enforced year by year:

\[
E^{\text{LL}}_{y,\omega} \le \alpha^{\text{LL}}_{\max,y,\omega}\, E^{\text{dem}}_{y,\omega} \quad \forall y,\omega,
\qquad\text{or}\qquad
\sum_{\omega} p_{\omega} E^{\text{LL}}_{y,\omega} \le \alpha^{\text{LL}}_{\max,y} \sum_{\omega} p_{\omega} E^{\text{dem}}_{y,\omega} \quad \forall y
\]

!!! note "Constraint enforcement mode"
    For both minimum renewable penetration and maximum lost-load share, MicroGridsPy supports two
    enforcement philosophies: **scenario-wise**, where the constraint holds separately for each
    scenario, and **expected**, where it holds only in probability-weighted expectation across
    scenarios. In the typical-year formulation the aggregates are computed over the representative
    year; in the multi-year formulation, separately for each modelled year.

---

Spatial limits on renewable deployment are handled by the
[land-availability constraint](renewable.md#land-availability-constraint-optional). Together with
the economic [objective](objective-function.md), these constraints let technical feasibility,
reliability, and policy requirements be represented explicitly.
