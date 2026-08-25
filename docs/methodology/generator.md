# Backup Generators

Dispatchable backup generation is modelled through one or more generator technologies
$g\in\mathcal{G}$. Each generator has a unit-based sizing variable and an hourly production
variable. Fuel consumption is modelled explicitly and linked to electrical production
through either a **nominal-efficiency** relationship or a **partial-load efficiency curve**.

## Installed capacity and production limit

Generators are sized in discrete units $N_g$, each with nominal electrical capacity $P_g$
(kW). Total installed generator capacity is:

\[
C_g = N_g\cdot P_g
\tag{25}
\]

Hourly production is bounded by installed capacity:

\[
E^{gen}_{t,\omega,g} \le N_g\cdot P_g \qquad \forall t,\omega,g
\tag{26}
\]

## Fuel–power relationship (nominal efficiency)

Fuel consumption is expressed in volumetric units (e.g. litres) and linked to electrical
production through the fuel lower heating value (LHV) and an efficiency factor. For
generators **without** partial-load modelling, the relationship is an equality using a
nominal conversion efficiency $\eta^{nom}_g$:

\[
E^{gen}_{t,\omega,g} = F_{t,\omega,g}\cdot \text{LHV}_g\cdot \eta^{nom}_g
\qquad \forall t,\omega,\; g\in\mathcal{G}_{noPL}
\tag{27}
\]

where $F_{t,\omega,g}$ is fuel consumption and $\text{LHV}_g$ is the energy content per unit
of fuel.

## Partial-load efficiency and piecewise-linear approximation

When partial-load modelling is enabled, generator efficiency becomes output-dependent.
MicroGridsPy implements a **convex piecewise-linear lower bound** on fuel consumption as a
function of electrical production. This keeps the formulation linear while capturing the
increase in specific fuel consumption at low load.

Let $r\in[0,1]$ be the generator loading fraction and let breakpoints $\{r_p\}_{p=0}^{P}$ be
given with corresponding efficiencies $\eta_{g,p}$. The electrical power at each breakpoint
is:

\[
p_{g,p} = P_g\cdot r_p
\tag{28}
\]

and the corresponding fuel consumption per unit:

\[
f_{g,p} = \frac{p_{g,p}}{\eta_{g,p}\,\text{LHV}_g}
\tag{29}
\]

For each segment $k$ connecting consecutive breakpoints $(p_{g,k}, f_{g,k})$ and
$(p_{g,k+1}, f_{g,k+1})$, the slope is:

\[
m_{g,k} = \frac{f_{g,k+1} - f_{g,k}}{p_{g,k+1} - p_{g,k}}
\tag{30}
\]

Fuel consumption is then constrained to lie above all segment lines (epigraph form), scaled
by the number of installed units:

\[
F_{t,\omega,g} \ge m_{g,k}\left( E^{gen}_{t,\omega,g} - N_g\, p_{g,k} \right) + N_g\, f_{g,k}
\qquad \forall t,\omega,\; g\in\mathcal{G}_{PL},\;\forall k
\tag{31}
\]

This yields a convex piecewise-linear approximation of the true nonlinear fuel curve and
guarantees fuel consumption is **not underestimated**, enabling realistic part-load
performance while preserving linearity and tractability.

!!! note "Convexity assumption and possible extensions"
    The part-load formulation is valid under the assumption that the fuel-consumption curve
    is **convex** with respect to electrical output — consistent with most internal
    combustion engines and small diesel generators. The current formulation is deliberately
    minimal for tractability. Consistent extensions include:

    - **Mixed-integer unit commitment** — binary on/off variables for minimum load, start-up
      costs, and non-convex efficiency regions (at higher computational cost).
    - **Piecewise efficiency with minimum load** — a lower bound $E^{gen}\ge \alpha P_g N_g$
      to reflect technical operating limits, without altering the convex structure.
    - **Technology-specific degradation** — time-dependent $\eta_{g,p}$ to reflect aging or
      maintenance, compatible with the piecewise-linear structure.

    These preserve the separation between **capacity planning** and **operational realism**.
