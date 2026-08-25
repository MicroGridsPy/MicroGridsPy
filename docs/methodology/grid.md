# Grid Connection and Availability

MicroGridsPy can represent a **weakly grid-connected** mini-grid in addition to the fully
isolated off-grid configuration. When grid connection is enabled, the system can import
electricity from the national grid and, optionally, export surplus back to it. Grid
interaction is constrained by (i) the physical exchange capacity of the interconnection line
and (ii) a **time-dependent grid-availability matrix** capturing outages and upstream
reliability.

Let $E^{imp}_{t,\omega,y}$ and $E^{exp}_{t,\omega,y}$ denote imported and exported
electricity at time $t$, scenario $\omega$, and year $y$. Grid exchange is governed by:

- $A^{grid}_{t,y}\in\{0,1\}$ — grid availability (1 if available, 0 during an outage);
- $\bar{P}^{grid}$ — maximum active power exchange capacity of the interconnection line (kW);
- $\eta^{imp}, \eta^{exp}$ — import/export efficiencies (transformer/conversion losses).

In typical-year mode the year index $y$ is omitted and the availability matrix reduces to a
single representative year $A^{grid}_t$.

## Grid import and export capacity

When on-grid operation is enabled, imports are bounded by the product of availability, line
capacity, and efficiency:

\[
E^{imp}_{t,\omega,y} \le A^{grid}_{t,y}\,\bar{P}^{grid}\,\eta^{imp} \qquad \forall t,\omega,y
\tag{32}
\]

If export is enabled, a symmetric constraint applies:

\[
E^{exp}_{t,\omega,y} \le A^{grid}_{t,y}\,\bar{P}^{grid}\,\eta^{exp} \qquad \forall t,\omega,y
\tag{33}
\]

These enforce that exchange is possible only when the upstream grid is available and within
the rated interconnection capacity. If the system is off-grid, the exchange variables are
fixed to zero.

## Grid-availability simulation

For realistic modelling of weak-grid contexts, MicroGridsPy can generate an exogenous
availability matrix $A^{grid}_{t,y}$ over the whole project horizon. It is stored as a CSV
with one column per project year $y=1,\dots,H$, one row per time period $t\in\mathcal{T}$
(e.g. 8760 rows for hourly resolution), and binary entries $A^{grid}_{t,y}\in\{0,1\}$.

The simulation logic proceeds as follows:

1. **Pre-connection years.** If the grid becomes available only after a connection year, all
   years before the first connection year have zero availability:
   $A^{grid}_{t,y}=0\;\;\forall t,\; y<y_{conn}$.
2. **Ideal-grid special case.** If the average number of outages per year or the average
   outage duration is zero, the grid is fully reliable after connection:
   $A^{grid}_{t,y}=1\;\;\forall t,\; y\ge y_{conn}$.
3. **Outage-event generation.** Otherwise, an outage process alternates *time between
   outages* ($A^{grid}=1$) and *outage durations* ($A^{grid}=0$). Both are sampled from
   **Weibull distributions** to produce realistic variability, then scaled so that, over the
   connected years, the expected total number of outages and total outage hours match the
   user-specified reliability targets (average outages per year and average outage duration).
4. **Matrix assembly.** The final binary sequence is reshaped into a
   $|\mathcal{T}|\times(H-y_{conn}+1)$ matrix for the connected years and concatenated with
   the zero-availability pre-connection block.

This yields a flexible representation of grid reliability — from fully unavailable (off-grid)
to perfectly reliable, to weak grids with stochastic outages — while preserving full
transparency of the underlying availability assumptions.
