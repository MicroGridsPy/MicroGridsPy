# The Kalobeyei Case Study

All the examples in this section use the case of **Kalobeyei**, a remote settlement in
northern Kenya that is currently **not connected to the national grid**. Like many rural
communities in Sub-Saharan Africa, households and businesses still rely largely on
traditional energy sources such as kerosene, diesel, and biomass.

This makes Kalobeyei a realistic testbed for MicroGridsPy: it combines a genuine electricity
demand, good solar potential, and the kind of planning uncertainty — growing demand, possible
future grid arrival — that off-grid planners face in practice.

## The community

The demand is built bottom-up from the settlement's users:

- around **700 households**, classified into three groups by their actual and expected
  appliance ownership;
- **2 primary schools** (roughly 30 lights each, plus some external lighting);
- **1 dispensary** with three rooms and seven beds;
- **productive activities**: tailoring workshops, bars, and garages.

## Demand assessment

Before running any optimization, MicroGridsPy characterizes the local demand through an
hourly time series for the representative year. The daily average profile is typical of a
small rural settlement: low overnight consumption, a daytime rise driven by productive uses,
and a pronounced **evening peak** when lighting and social activity coincide.

![Average daily electricity demand profile for Kalobeyei](../assets/examples/demand_profile.png)

*Average daily load. The evening peak reaches roughly 80 kW, with an average daily demand of
about 1100 kWh.* In some scenarios (from [Planning for Growth](planning-for-growth.md)
onward) this demand is scaled up year by year to represent settlement growth.

## Resource assessment

The other primary input is the availability of the renewable resource, again provided as an
hourly time series. Kalobeyei has **strong and stable solar potential**, which makes solar PV
the natural backbone of the system.

![Average daily solar capacity factor for Kalobeyei](../assets/examples/resource_solar_cf.png)

*Average daily solar capacity factor.* Wind was also assessed for the site but is more
variable and generally lower, so it contributes little to the least-cost design; the examples
therefore model **solar PV** as the single renewable technology. The resource time series
were generated for the site's coordinates using open resource databases.

These two inputs — demand and resource availability — define the operating conditions under
which every scenario is optimized.

## Shared assumptions

Unless a scenario explicitly changes them, all six examples use the same techno-economic and
project settings. This is what makes their results directly comparable.

| Setting | Value |
|---|---|
| Planning horizon | 10 years (2026–2035) |
| Social discount rate | 7.4 % |
| Formulation | multi-year (dynamic) |
| Lost-load constraint | not enforced (0 % unmet demand allowed to be free) |
| Minimum renewable penetration | not enforced |
| Integer (discrete) capacity units | disabled |
| Land constraint | not enforced |
| Generator efficiency model | constant efficiency (no part-load curve) |
| Battery loss model | constant efficiency |
| Battery degradation | exogenous capacity fade only |
| Diesel fuel cost | 1.3 USD/litre (constant across years) |

### Techno-economic inputs

| Parameter | Solar PV | Diesel generator | Li-ion battery | Lead-acid battery |
|---|--:|--:|--:|--:|
| Capital cost | 1200 USD/kW | 400 USD/kW | 300 USD/kWh | 200 USD/kWh |
| WACC | 5 % | 5 % | 5 % | 5 % |
| Lifetime | 25 y | 20 y | 10 y | 8 y |
| Fixed O&M (of CAPEX/yr) | 1.8 % | 4.5 % | 2 % | 2 % |
| Efficiency | inverter 0.98 | full-load 0.34 | charge/discharge 0.93 | charge/discharge 0.86 |
| Operating limits | DC/AC ratio 1.2 | — | DoD 0.8; C-rate 0.25 | DoD 0.5; C-rate 0.167 |
| Exogenous degradation | 0 %/y | 0 %/y | 0.5 %/y | 0.3 %/y |

<small>Diesel LHV = 10.14 kWh per unit of fuel. Battery inverter cost = 160 USD/kW; PV
inverter cost = 180 USD/kW<sub>ac</sub>; inverter lifetime = 15 y. Emissions are left at zero
except for grid imports in the [carbon-cost scenario](uncertainty.md#scenario-6-carbon-cost). Full
inputs are in each project's `inputs/` folder — see the
[reproducibility mapping](index.md#reproducibility).</small>

With the site characterized, we can start comparing planning strategies, beginning with
[Technology Choice](technology-choice.md).
