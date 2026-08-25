# Renewable Technologies

Renewable technologies are modelled with a **generic, technology-agnostic** formulation
based on installed capacity, resource availability, and conversion efficiency. This common
structure — driven by time-series inputs and a small set of techno-economic parameters — can
represent photovoltaic systems, wind turbines, hydropower, or any renewable source
describable through a production profile.

## Renewable production constraint

Renewable electricity production is limited by installed capacity and by the availability of
the primary energy resource. For each time period $t$, scenario $\omega$, and renewable
technology $r$:

\[
E_{t,\omega,r} \le A_{t,\omega,r}\cdot \eta_r\cdot P_r\cdot N_r
\tag{15}
\]

where:

- $E_{t,\omega,r}$ is the renewable electricity production;
- $A_{t,\omega,r}$ is the **normalized resource-availability** time series (e.g. solar
  irradiation, wind capacity factor);
- $\eta_r$ is the inverter/conversion efficiency;
- $P_r\cdot N_r$ is the installed nominal capacity ($N_r$ units of nominal capacity $P_r$).

This enforces that generation cannot exceed the maximum power output allowed by both
installed capacity and resource availability at each time step. Because production is bounded
*from above* (not fixed), the model can implicitly **curtail** surplus renewable energy.

## Maximum installable capacity

An optional upper bound can reflect physical, spatial, or regulatory limits on each
renewable technology. When enabled:

\[
N_r\cdot P_r \le \mathcal{C}_r
\tag{16}
\]

where $\mathcal{C}_r$ is the maximum allowable installed capacity for technology $r$.

The same conceptual structure is used across planning modes, with appropriate year and
scenario indexing in the multi-year formulation. A system-level
[land-availability constraint](constraints.md#land-availability-constraint) can additionally
bound total renewable area.
