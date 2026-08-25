# Battery Storage

MicroGridsPy models the battery energy-storage system as a **single aggregated battery
bank**, parameterized through an installed energy capacity and operational constraints on
charging, discharging, and state of charge (SOC). The battery is described through three
groups of constraints: **flow constraints**, **SOC dynamics**, and **capacity bounds**. The
mathematical structure is identical in both planning modes; in the multi-year formulation,
parameters (costs, lifetime, availability) can be indexed by year.

Let $t\in\mathcal{T}$ denote the time periods (typically hourly) and $\omega\in\Omega$ the
scenarios. Installed battery energy capacity is:

\[
C^{bat} = N^{bat}\cdot E^{unit}
\tag{17}
\]

where $N^{bat}$ is the number of battery units and $E^{unit}$ the nominal energy capacity
per unit (kWh). Battery operation is described by charging power $P^{ch}_{t,\omega}$,
discharging power $P^{dis}_{t,\omega}$, and stored energy $SOC_{t,\omega}$. At hourly
resolution ($\Delta t = 1$), kW and kWh are used interchangeably.

## Flow constraints

Charging and discharging power are bounded using **time-to-full** parameters, which define
the maximum admissible rate as a fraction of installed energy capacity:

\[
P^{ch}_{t,\omega} \le \frac{C^{bat}}{t^{ch}} \qquad \forall t,\omega
\tag{18}
\]

\[
P^{dis}_{t,\omega} \le \frac{C^{bat}}{t^{dis}} \qquad \forall t,\omega
\tag{19}
\]

where $t^{ch}$ and $t^{dis}$ are the times (hours) required to fully charge or discharge the
battery at maximum rate.

## State of charge

SOC dynamics follow a standard energy balance including charge/discharge efficiencies. For
an hourly time step ($\Delta t = 1\,\text{h}$):

\[
SOC_{0,\omega} = SOC_0\cdot C^{bat} + \eta_c P^{ch}_{0,\omega} - \frac{P^{dis}_{0,\omega}}{\eta_d}
\qquad \forall\omega
\tag{20}
\]

\[
SOC_{t,\omega} = SOC_{t-1,\omega} + \eta_c P^{ch}_{t,\omega} - \frac{P^{dis}_{t,\omega}}{\eta_d}
\qquad \forall t = 1,\dots,|\mathcal{T}|-1,\;\forall\omega
\tag{21}
\]

where $\eta_c$ and $\eta_d$ are the charging and discharging efficiencies and
$SOC_0\in[0,1]$ is the initial SOC fraction.

A **cyclic boundary condition** avoids end-of-horizon artefacts and ensures consistent
operation across repeated years:

\[
SOC_{|\mathcal{T}|-1,\omega} = SOC_0\cdot C^{bat} \qquad \forall\omega
\tag{22}
\]

## Capacity constraints

The SOC is bounded between a minimum and maximum admissible stored energy, based on usable
capacity and the depth-of-discharge limit:

\[
SOC_{t,\omega} \le C^{bat} \qquad \forall t,\omega
\tag{23}
\]

\[
SOC_{t,\omega} \ge (1-\text{DoD})\,C^{bat} \qquad \forall t,\omega
\tag{24}
\]

where $\text{DoD}\in[0,1]$ is the maximum depth of discharge.

!!! note "Degradation is treated implicitly"
    In the current planning formulation, battery degradation is treated implicitly through a
    **calendar-lifetime assumption**: the battery technical lifetime (in years) drives the
    annualized investment cost (via CRF) and the replacement logic in the multi-year
    formulation. Degradation does **not** directly constrain operation, and the usable
    capacity is assumed constant during the battery's lifetime.

    A natural, still-linear extension is **exogenous capacity fade** via a time-dependent
    multiplier $\alpha_y\in(0,1]$, so the effective capacity becomes $C^{bat}_y = \alpha_y
    C^{bat}$. In the multi-year formulation this enables constraints such as
    $SOC_{t,\omega,y} \le \alpha_y C^{bat}$ and $SOC_{t,\omega,y} \ge (1-\text{DoD})\alpha_y
    C^{bat}$, with the charge/discharge limits (18)–(19) scaled analogously. The trajectory
    $\alpha_y$ can come from empirical calendar-aging models, manufacturer data, or scenario
    assumptions. Temperature-driven derating can be incorporated the same way by defining
    $\alpha_y$ (or a higher-resolution $\alpha_{t,y}$) as a deterministic function of
    ambient/battery temperature — preserving linearity as long as the factors are exogenous.
