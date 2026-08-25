# Renewable Technologies

Renewable technologies are modelled with a **generic, technology-agnostic** formulation based
on installed capacity, resource availability, and conversion efficiency. This common structure
— driven by time-series inputs and a small set of techno-economic parameters — represents
photovoltaics, wind turbines, hydropower, or any renewable source describable through a
production profile.

Renewable production is always treated as an **upper-bounded** quantity: **curtailment is
implicitly allowed** whenever available renewable energy exceeds demand or network capability.
The mathematical structure differs slightly between the typical-year and multi-year
formulations because the latter treats capacity evolution explicitly.

## Renewable production constraint

### Typical-year formulation

For each time period $t$, scenario $\omega$, and renewable technology $r$, production is bounded
by installed capacity and resource availability:

\[
E_{t,\omega,r} \;\le\; A_{t,\omega,r}\cdot \eta_r\cdot P_r\cdot N_r
\]

where $E_{t,\omega,r}$ is renewable production, $A_{t,\omega,r}$ is the normalized resource-
availability profile (e.g. capacity factor), $\eta_r$ is the inverter/conversion efficiency,
and $P_r\cdot N_r$ is the installed nominal capacity.

### Multi-year formulation

Renewable capacity is built incrementally through investment cohorts and evolves over time due
to aging and replacement. Let $k$ denote the investment step (cohort) and $y$ the year. The
available capacity in year $y$ is

\[
C^{\text{avail}}_{y,r} = \sum_k N_{k,r}\cdot P_r\cdot \alpha_{k,y}\cdot \delta_{k,y,r}
\]

where $N_{k,r}$ is the number of units installed at step $k$, $\alpha_{k,y}$ is the cohort
activation mask (accounting for lifetime and replacement), and $\delta_{k,y,r}$ is the
degradation factor applied to capacity. Renewable production is then bounded by the available
capacity:

\[
E_{t,y,\omega,r} \;\le\; A_{t,y,\omega,r}\cdot \eta_r\cdot C^{\text{avail}}_{y,r}
\]

## Maximum installable capacity (optional)

Physical, spatial, or regulatory limits can bound the installed capacity of each renewable
technology.

**Typical-year** — applies to the total installed capacity:

\[
N_r\cdot P_r \;\le\; \overline{C}_r
\]

**Multi-year** — applies to the cumulative capacity across all cohorts:

\[
\sum_k N_{k,r}\cdot P_r \;\le\; \overline{C}_r
\]

where $\overline{C}_r$ is the maximum allowable installed capacity.

## Land availability constraint (optional)

When spatial limitations are relevant, MicroGridsPy can bound the total land area used by
renewables. Let $a_r$ be the specific land requirement of technology $r$ ($\text{m}^2/\text{kW}$)
and $A^{\max}$ the total available area.

**Typical-year** — with $C_r = N_r P_r$:

\[
\sum_{r} C_r\, a_r \;\le\; A^{\max}
\]

**Multi-year** — land use is computed on the cumulative renewable design across all steps:

\[
\sum_k \sum_r N_{k,r}\, P_r\, a_r \;\le\; A^{\max}
\]

so renewable land occupation is a cumulative design-side constraint over all installed cohorts.
