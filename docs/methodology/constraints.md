# System Constraints

The system-level constraints couple all technologies and ensure feasibility of supply,
reliability, and policy or resource limits. Constraints are enforced at hourly resolution
for each scenario, while additional aggregate constraints may apply at annual level.

## Energy balance constraint

At each time period $t\in\mathcal{T}$ and scenario $\omega\in\Omega$, total net supply must
equal demand. MicroGridsPy adopts the convention that **storage charging and grid export act
as demand-side sinks**, while **storage discharging and grid import act as supply-side
sources**:

\[
\sum_r E^{res}_{t,\omega,r}
+ \sum_g E^{gen}_{t,\omega,g}
+ E^{imp}_{t,\omega} - E^{exp}_{t,\omega}
+ P^{dis}_{t,\omega} - P^{ch}_{t,\omega}
+ \ell_{t,\omega}
= D_{t,\omega}
\qquad \forall t,\omega
\tag{34}
\]

where $\ell_{t,\omega}$ is lost load (unserved energy) and $D_{t,\omega}$ is electrical
demand. If the system is off-grid, then $E^{imp}_{t,\omega}=E^{exp}_{t,\omega}=0$. If grid
connection is enabled but export is disabled, $E^{exp}_{t,\omega}=0$ and only imports are
allowed. In all cases, the balance retains the same structure.

## Minimum renewable penetration

A minimum renewable-penetration constraint can represent policy targets or sustainability
requirements. Define $E_{tot}$ as the total annual electricity supplied to meet demand
(renewables, generators, and grid imports), and $E_{ren}$ as the annual renewable
contribution. The constraint is:

\[
E_{ren} \ge \alpha^{ren}_{min}\, E_{tot}
\tag{35}
\]

where $\alpha^{ren}_{min}\in[0,1]$ is the minimum renewable-penetration fraction. In the
implemented accounting, grid imports contribute to $E_{tot}$ and are treated as
non-renewable unless explicitly modelled otherwise.

## Maximum lost-load share

System reliability can be enforced through an upper bound on the share of demand that may
remain unserved. Let total annual lost load and demand be:

\[
LL_{tot} = \sum_{t,\omega} \ell_{t,\omega}, \qquad
E_{dem} = \sum_{t,\omega} D_{t,\omega}
\tag{36}
\]

The constraint is:

\[
LL_{tot} \le \alpha^{LL}_{max}\, E_{dem}
\tag{37}
\]

where $\alpha^{LL}_{max}\in[0,1]$ is the maximum admissible fraction of unmet demand.

## Land-availability constraint

When spatial limitations are relevant, an upper bound can be enforced on the total land area
required by renewable technologies. Let $a_r$ be the specific land requirement per installed
kW for technology $r$ ($\text{m}^2/\text{kW}$) and $C_r = N_r P_r$ the installed renewable
capacity:

\[
\sum_{r\in R} C_r\, a_r \le A_{max}
\tag{38}
\]

where $A_{max}$ is the maximum available land area ($\text{m}^2$). This constraint applies
only when a positive land limit is specified.

---

Together, these constraints allow technical feasibility, reliability, policy requirements,
and spatial limitations to be represented alongside the economic
[objective](objective-function.md).
