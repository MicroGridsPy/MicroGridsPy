# Inverter Sizing

Power-electronic conversion is modelled explicitly for the two DC-coupled assets — renewable
generation and battery storage — so that converter capacity is sized and costed alongside the
energy assets rather than folded into them. The two follow different but consistent philosophies.

## Renewable inverters (deterministic)

Each renewable technology is sized on the **DC side** (installed panel/turbine capacity), and its
inverter/converter **AC capacity** is derived deterministically from a fixed **DC/AC ratio**:

\[
P^{\text{inv,ac}}_{j} = \frac{C^{\text{dc}}_{j}}{\text{dc\_ac\_ratio}_{j}}
\]

The ratio (`renewables.yaml → technical.dc_ac_ratio`, default 1.0) encodes the design choice of
deliberately oversizing the array relative to the inverter. The derived AC capacity carries its
own investment cost (`inverter_specific_investment_cost_per_kw_ac`), lifetime
(`inverter_lifetime_years`), and fixed O&M (`inverter_fixed_om_share_per_year`), and a conversion
efficiency (`inverter_efficiency`) is applied to renewable output. Because the AC capacity is a
fixed function of the DC sizing decision, no extra optimisation variable is introduced — the
inverter is a **deterministic sidecar** to the renewable sizing.

## Battery inverter (explicit, component-based)

The battery converter is treated as a **first-class sizing decision**, on the same
component-based footing as the other assets:

\[
P^{\text{inv}} = u^{\text{inv}}\; P^{\text{inv,nom}}
\]

where $u^{\text{inv}}$ is the number of battery-inverter units and $P^{\text{inv,nom}}$ is the
nominal power per unit (`battery.yaml → technical.inverter_nominal_power_kw`). Discrete unit
sizing therefore applies naturally to the battery inverter as an integer unit count. The installed
inverter power **bounds the battery charge and discharge power** in every period (see
[Battery storage](battery.md)), and may optionally be coupled to the installed energy through a
maximum charge/discharge **C-rate**:

\[
P^{\text{ch}}_{t} \le P^{\text{inv}}, \qquad P^{\text{dis}}_{t} \le P^{\text{inv}}, \qquad
P^{\text{inv}} \le c^{\text{rate}}\, C^{\text{bat}}
\]

The battery inverter has its own CAPEX (`inverter_specific_investment_cost_per_kw`), lifetime
(`inverter_lifetime_years`), and fixed O&M, all amortised on the **calendar** convention like the
other assets (it is not subject to the battery's cycle-fade replacement).

## Across the planning modes

Both formulations size the inverters with the same logic. In the **typical-year** model the
inverter powers are single design variables; in the **multi-year** model they are resolved **per
investment step** — renewable inverter/converter capacity per renewable technology and explicit
battery-inverter sizing by step — and the inverter costs enter the discounted objective and the
structured exports on the same cohort/step basis as the energy assets.
