# Multi-Year Inverter Implementation Plan

## 1. Current State Assessment

### 1.1 Typical-Year reference state

Typical-Year now has a coherent inverter treatment across parsing, modeling, reporting, export, and rendering.

Renewable inverter logic:
- Inputs are parsed in [core/data_pipeline/typical_year_parsing.py](../core/data_pipeline/typical_year_parsing.py).
- Renewable investment inputs include:
  - `inverter_specific_investment_cost_per_kw_ac`
  - `inverter_lifetime_years`
  - `inverter_fixed_om_share_per_year`
- Renewable technical inputs include:
  - `dc_ac_ratio`
  - `inverter_efficiency`
- Renewable inverter AC capacity is deterministic:
  - `res_inverter_capacity_ac = installed_dc_capacity / dc_ac_ratio`
- Operational consistency is enforced in [core/typical_year_model/constraints.py](../core/typical_year_model/constraints.py):
  - availability-and-efficiency cap
  - explicit inverter AC cap `res_generation <= installed_dc / dc_ac_ratio`

Battery inverter logic:
- Inputs are parsed in [core/data_pipeline/typical_year_parsing.py](../core/data_pipeline/typical_year_parsing.py).
- Battery investment inputs include:
  - `inverter_specific_investment_cost_per_kw`
  - `inverter_lifetime_years`
  - `inverter_fixed_om_share_per_year`
- Battery technical power-energy coupling now uses only:
  - `max_charge_c_rate`
  - `max_discharge_c_rate`
- The battery inverter is an explicit design variable:
  - `battery_inverter_power`
- Operational consistency is enforced in [core/typical_year_model/constraints.py](../core/typical_year_model/constraints.py) through:
  - `battery_charge <= battery_inverter_power`
  - `battery_discharge <= battery_inverter_power`
  - optional C-rate links from inverter power to installed battery energy

Objective and cost handling:
- Implemented in [core/typical_year_model/objective.py](../core/typical_year_model/objective.py).
- Renewable inverter CAPEX/FOM are annualized separately from renewable DC asset CAPEX/FOM.
- Battery inverter CAPEX/FOM are annualized separately from battery energy CAPEX/FOM.
- Inverter CAPEX uses inverter-specific lifetime, not the host technology lifetime.

Results/export/rendering:
- Canonical solved object is implemented in [core/export/typical_year_results.py](../core/export/typical_year_results.py) as `TypicalYearResults`.
- Reporting tables are built in [core/export/typical_year_reporting.py](../core/export/typical_year_reporting.py).
- Structured inverter outputs include:
  - `renewable_inverter_design`
  - `battery_inverter_design`
  - `inverter_metrics`
- Typical-Year rendering uses the canonical object in [core/visualization/typical_year_results_page.py](../core/visualization/typical_year_results_page.py).

This is the main reference pattern to mirror.

### 1.2 Multi-Year current state

Inputs/templates:
- Dynamic templates in [core/io/templates.py](../core/io/templates.py) already expose several inverter-related fields:
  - renewables:
    - `inverter_specific_investment_cost_per_kw_ac`
    - `inverter_lifetime_years`
    - `inverter_fixed_om_share_per_year`
    - `dc_ac_ratio`
    - `inverter_efficiency`
  - battery:
    - `inverter_specific_investment_cost_per_kw`
    - `inverter_lifetime_years`
    - `inverter_fixed_om_share_per_year`
    - `max_charge_c_rate`
    - `max_discharge_c_rate`
- But the Multi-Year data parser does not yet fully consume them.

Renewables in Multi-Year:
- Parsed in [core/multi_year_model/data.py](../core/multi_year_model/data.py).
- Current renewable parser reads:
  - `nominal_capacity_kw`
  - `lifetime_years`
  - `specific_investment_cost_per_kw`
  - `wacc`
  - `grant_share_of_capex`
  - `embedded_emissions_kgco2e_per_kw`
  - `fixed_om_share_per_year`
  - `production_subsidy_per_kwh`
  - `inverter_efficiency`
  - `specific_area_m2_per_kw`
  - `max_installable_capacity_kw`
  - `capacity_degradation_rate_per_year`
- Current renewable parser does not read:
  - `dc_ac_ratio`
  - `inverter_specific_investment_cost_per_kw_ac`
  - `inverter_lifetime_years`
  - `inverter_fixed_om_share_per_year`
- It also does not persist `conversion_technology_by_resource` metadata like Typical-Year does.

Renewable operations in Multi-Year:
- Implemented in [core/multi_year_model/constraints.py](../core/multi_year_model/constraints.py).
- Active renewable DC capacity by year is already built correctly using:
  - `replacement_active_mask`
  - `repeating_degradation_factor`
  - cohort investments `res_units(inv_step, resource)`
- Renewable dispatch is currently limited by:
  - `availability * active_capacity * inverter_efficiency`
- There is no explicit renewable inverter AC-cap clipping term.
- Therefore modeled dispatch can exceed the inverter size that would be reported if `dc_ac_ratio` were introduced.

Battery in Multi-Year:
- Battery design currently uses only:
  - `battery_units(inv_step)` as energy investment
- There is no explicit battery inverter design variable.
- Battery charge/discharge limits are currently derived from energy using:
  - `battery_charge <= available_energy / max_charge_time_hours`
  - `battery_discharge <= available_energy / max_discharge_time_hours`
- The parser still expects:
  - `max_charge_time_hours`
  - `max_discharge_time_hours`
- Current Multi-Year battery parser does not read:
  - `battery_inverter_specific_investment_cost_per_kw`
  - `battery_inverter_lifetime_years`
  - `battery_inverter_fixed_om_share_per_year`
  - `battery_max_charge_c_rate`
  - `battery_max_discharge_c_rate`

Objective/economics in Multi-Year:
- Implemented in [core/multi_year_model/objective.py](../core/multi_year_model/objective.py).
- Current annuity/FOM logic includes only:
  - renewable DC asset
  - battery energy asset
  - generator asset
- Renewable inverter cost streams are missing.
- Battery inverter cost streams are missing.
- Tail-annuity memo logic also excludes inverter assets.

Results/export/rendering in Multi-Year:
- Reporting/export is in [core/export/multi_year_results.py](../core/export/multi_year_results.py).
- Rendering is in [core/visualization/multi_year_results_page.py](../core/visualization/multi_year_results_page.py).
- Design tables currently report:
  - renewable installed DC capacity by step
  - battery installed kWh by step
  - generator installed kW by step
- There are no structured inverter tables.
- Scenario cost tables and reporting summaries do not break out inverter CAPEX/FOM.
- UI currently shows no inverter-specific sizing or diagnostics in Multi-Year.

Main gaps:
- Renewable inverter semantics are incomplete.
- Battery inverter is not explicit.
- Inverter economics are absent from the objective and reports.
- Multi-Year exports/rendering do not expose inverter results.
- Dynamic parser/templates are ahead of the model in some places and behind in others.

## 2. Target Design for Multi-Year

### 2.1 Renewable inverter logic

Target semantics:
- Keep renewable inverter sizing deterministic, as in Typical-Year.
- Do not create a separate renewable inverter decision variable.
- Derive renewable inverter AC capacity from renewable DC cohort capacity.

Recommended formulation:
- Parse and store:
  - `res_dc_ac_ratio(inv_step, resource)` or `res_dc_ac_ratio(resource)`
  - `res_inverter_specific_investment_cost_per_kw_ac(inv_step, resource)`
  - `res_inverter_lifetime_years(inv_step, resource)`
  - `res_inverter_fixed_om_share_per_year(inv_step, resource)`
- Preferred dimensional treatment:
  - `dc_ac_ratio`: shared by resource across steps
  - inverter CAPEX/lifetime/FOM: step-dependent, like other investment terms
- Derive cohort inverter AC capacity:
  - `res_inv_cap_by_step(inv_step, resource) = res_units * res_nominal_capacity_kw / res_dc_ac_ratio`
- Derive active yearly inverter AC capacity by cohort:
  - `res_inv_cap_available(inv_step, year, resource) = res_inv_cap_by_step * replacement_active_mask * repeating_degradation_factor(...)`
- Aggregate if needed:
  - `res_inv_cap_available_total(year, resource) = sum_inv_step(res_inv_cap_available)`

Operational clipping:
- Add explicit renewable AC-cap consistency constraint:
  - `res_generation(period, year, scenario, resource) <= sum_inv_step(res_inv_cap_available(inv_step, year, resource))`
- Keep the existing availability-and-efficiency cap.
- This mirrors Typical-Year exactly in logic, but uses active cohort capacity by year.

Derived cohort vs aggregated-year choice:
- Best choice: derive inverter capacity cohort-by-cohort, then aggregate for the dispatch limit.
- Why:
  - matches cohort economics naturally
  - matches replacement masks and degradation mechanics already used for renewable DC cohorts
  - makes reporting by step and by year easy
  - avoids introducing a second non-economic aggregation path that could diverge from annuity/FOM accounting

Reporting structure:
- Add structured outputs for:
  - renewable inverter capacity by step/cohort
  - renewable inverter active capacity by year
  - renewable inverter metrics by year/scenario such as:
    - installed AC inverter capacity
    - effective inverter-limited potential
    - inverter clipping potential

### 2.2 Battery inverter logic

Target semantics:
- Make battery inverter sizing explicit, as in Typical-Year.
- In Multi-Year, the battery inverter should be cohort-based because battery investments are cohort-based.

Recommended formulation:
- Add a design variable:
  - `battery_inverter_power(inv_step)`
- Keep battery energy investment:
  - `battery_units(inv_step)`
- Parse and store:
  - `battery_inverter_specific_investment_cost_per_kw(inv_step)`
  - `battery_inverter_lifetime_years(inv_step)`
  - `battery_inverter_fixed_om_share_per_year(inv_step)`
  - `battery_max_charge_c_rate`
  - `battery_max_discharge_c_rate`

Operational interaction:
- Replace current time-based limits with explicit inverter power:
  - `battery_charge(period, year, scenario, inv_step) <= battery_inverter_power(inv_step) * active_mask_or_reference`
  - `battery_discharge(period, year, scenario, inv_step) <= battery_inverter_power(inv_step) * active_mask_or_reference`
- Add optional energy-to-power coupling:
  - `battery_inverter_power(inv_step) <= max_charge_c_rate * nominal_or_effective_energy_reference`
  - `battery_inverter_power(inv_step) <= max_discharge_c_rate * nominal_or_effective_energy_reference`

Most important Multi-Year-specific issue:
- What energy reference should the C-rate link use?

Recommended choice:
- Keep the design coupling against nominal cohort energy investment, not against degraded effective capacity.
- Then let degradation reduce actual charge/discharge by reducing the operational energy state and available usable capacity, but not by shrinking the installed inverter hardware.
- Why:
  - inverter hardware itself does not degrade the same way battery energy does
  - using degraded energy directly inside the design C-rate link would implicitly degrade inverter power capability every year
  - that would be a new physical assumption, not present in Typical-Year

Battery degradation interaction:
- `battery_effective_energy_capacity(year, scenario, inv_step)` should continue to limit SOC and usable energy.
- Battery inverter power should remain non-degrading unless we explicitly choose otherwise.
- If advanced battery-loss mode is active, the explicit inverter variable should become the public AC-side reference, mirroring Typical-Year.

Cohort activation:
- Use `replacement_active_mask` to activate the installed inverter cohort in the years where that cohort is alive.
- For operations, charge/discharge power caps should be zero when the cohort is inactive.

Investment and FOM:
- Add battery inverter annuity and FOM streams step-by-step, using cohort start year and replacement lifecycle logic exactly as battery energy does now.

Reporting:
- Add structured tables for:
  - battery inverter design by step
  - battery inverter active capacity by year
  - battery inverter utilization / peak use by year

### 2.3 Shared economic/reporting logic

Objective:
- Add renewable inverter CAPEX annuities and FOM to the Multi-Year objective.
- Add battery inverter CAPEX annuities and FOM to the Multi-Year objective.
- Extend post-horizon annuity-tail memo to include both inverter asset classes.

Design summary:
- Extend `build_design_by_step_table_multi_year()` so inverter capacity can be reported alongside each cohort.
- Prefer adding separate structured tables rather than overloading the current generic design table.

Yearly KPIs:
- Add renewable inverter clipping metrics to yearly KPIs.
- Add battery inverter peak utilization metrics if low-cost.

Cash flow and reporting:
- Extend discounted cashflow tables to separate:
  - renewable DC annuity
  - renewable inverter annuity
  - battery energy annuity
  - battery inverter annuity
- Extend fixed O&M breakdown similarly.
- Keep objective-consistent totals.

Exports:
- Add dedicated CSV outputs for:
  - `renewable_inverter_design_by_step.csv`
  - `battery_inverter_design_by_step.csv`
  - `renewable_inverter_capacity_by_year.csv`
  - `battery_inverter_capacity_by_year.csv`
  - `inverter_metrics_yearly.csv`
- Keep existing export files, but derive any inverter totals from the same canonical backend logic.

Results page:
- Extend Multi-Year rendering to show:
  - renewable inverter/converter capacity
  - battery inverter/converter power
  - inverter-related cashflow rows
  - inverter metrics by year
- Follow the Typical-Year visual language where it makes sense, but stay year-aware.

## 3. Design Decisions That Need Explicit Confirmation

### Decision 1: Renewable inverter sizing derived per cohort or only at aggregated year level?

Options:
- Aggregate-only:
  - derive yearly renewable DC total first, then compute inverter AC total
- Cohort-first:
  - derive inverter AC for each cohort, then apply active masks and sum

Recommendation:
- Use cohort-first derivation.

Why:
- cost accounting is cohort-based in Multi-Year
- replacement masks are cohort-based
- future reporting by step becomes straightforward
- avoids mismatches between cashflow and operations

### Decision 2: Should renewable inverter CAPEX be attached to renewable cohorts or treated as separate derived reporting only?

Options:
- Reporting-only derived stream
- Real objective cost stream tied to cohorts

Recommendation:
- Treat renewable inverter CAPEX/FOM as real cohort-level objective streams.

Why:
- Typical-Year already treats inverter economics as real
- otherwise operations and reported design would be updated without updating economics
- this is the exact inconsistency we just fixed in Typical-Year

### Decision 3: Should battery inverter replacement follow battery cohorts or a separate inverter lifetime?

Options:
- Tie inverter replacement exactly to battery lifetime
- Use separate inverter lifetime but the same cohort commissioning year

Recommendation:
- Use separate inverter lifetime with the same cohort commissioning year.

Why:
- aligns with Typical-Year inverter lifetime logic
- keeps the model minimal
- respects that inverter lifetime may differ from battery energy lifetime
- avoids creating an entirely separate inverter cohort family with different commissioning dates

Implication:
- replacement-active logic for the battery inverter should use the battery inverter lifetime, not `battery_calendar_lifetime_years`

### Decision 4: Should battery inverter degradation be represented explicitly?

Options:
- degrade inverter power with battery energy state
- do not degrade inverter power; only battery energy degrades

Recommendation:
- Do not degrade inverter power explicitly in the first implementation.

Why:
- simpler
- more defensible for current app semantics
- avoids introducing a hidden new physical assumption
- battery degradation is already complex enough

### Decision 5: What is the cleanest result structure for inverter outputs in Multi-Year?

Options:
- add inverter columns to generic design/cashflow tables only
- create dedicated structured inverter result tables

Recommendation:
- create dedicated structured tables and also expose inverter columns in high-level summaries where useful

Why:
- mirrors the cleaned Typical-Year approach
- easier for Results Page and exports
- prevents repeated reconstruction/parsing logic

## 4. Proposed Implementation Sequence

### Step 1: Audit and align dynamic inputs/templates

Purpose:
- make the dynamic template/schema and parser agree on the inverter fields that will actually be supported

Likely files:
- [core/io/templates.py](../core/io/templates.py)
- [core/multi_year_model/data.py](../core/multi_year_model/data.py)

Work:
- extend Multi-Year renewable parser to consume:
  - `inverter_specific_investment_cost_per_kw_ac`
  - `inverter_lifetime_years`
  - `inverter_fixed_om_share_per_year`
  - `dc_ac_ratio`
- extend Multi-Year battery parser to consume:
  - `inverter_specific_investment_cost_per_kw`
  - `inverter_lifetime_years`
  - `inverter_fixed_om_share_per_year`
  - `max_charge_c_rate`
  - `max_discharge_c_rate`
- remove or de-emphasize `max_*_time_hours` in dynamic templates if we want the same policy as Typical-Year
- persist `conversion_technology_by_resource` into Multi-Year data attrs/settings, as Typical-Year already does

Validate before moving on:
- generated dynamic templates include all required inverter inputs
- parser round-trip works for example projects
- default/fallback behavior is explicit and documented

### Step 2: Extend Multi-Year params and variable definitions

Purpose:
- make inverter-related quantities first-class in the model API

Likely files:
- [core/multi_year_model/params.py](../core/multi_year_model/params.py)
- [core/multi_year_model/variables.py](../core/multi_year_model/constraints.py)

Work:
- add missing renewable inverter params to `Params`
- add missing battery inverter params to `Params`
- add `battery_inverter_power(inv_step)` variable

Validate before moving on:
- model can build with new params present
- no old callsites fail due to missing optional fields

### Step 3: Implement renewable inverter operational consistency

Purpose:
- make renewable dispatch physically consistent with reported inverter AC capacity

Likely files:
- [core/multi_year_model/constraints.py](../core/multi_year_model/constraints.py)

Work:
- compute active renewable inverter AC capacity by cohort/year
- add explicit renewable AC clipping constraint
- keep existing availability-and-efficiency cap
- decide whether renewable capacity degradation applies equally to inverter-limited AC capacity

Recommended implementation:
- use the same active/degradation factor already used for renewable DC cohort availability
- derive AC cap from degraded DC availability divided by `dc_ac_ratio`

Validate before moving on:
- dispatch never exceeds reported active inverter AC capacity
- renewable clipping behaves as expected in a small synthetic case

### Step 4: Implement battery inverter operational consistency

Purpose:
- make battery power explicit and objective-consistent

Likely files:
- [core/multi_year_model/variables.py](../core/multi_year_model/variables.py)
- [core/multi_year_model/constraints.py](../core/multi_year_model/constraints.py)

Work:
- add battery inverter variable by investment step
- replace energy/time-derived power limit with explicit inverter power limit
- add charge/discharge constraints against inverter power
- add C-rate coupling against nominal cohort battery capacity
- update advanced battery-loss mode to use inverter power as the charge/discharge reference

Validate before moving on:
- battery dispatch is bounded by inverter power
- battery inverter can be zero while battery energy exists, and vice versa, unless C-rate binds
- degradation-enabled runs still build and solve

### Step 5: Integrate inverter economics into the objective

Purpose:
- make modeled economics match modeled physics and reported design

Likely files:
- [core/multi_year_model/objective.py](../core/multi_year_model/objective.py)

Work:
- add renewable inverter present-cost, annuity, FOM, and tail-memo terms
- add battery inverter present-cost, annuity, FOM, and tail-memo terms
- keep step-dependent economics and year-dependent active masks

Validate before moving on:
- objective decomposition reconciles numerically
- discounted cashflow still matches the objective

### Step 6: Update Multi-Year export/reporting backend

Purpose:
- centralize inverter reporting before touching the page

Likely files:
- [core/export/multi_year_results.py](../core/export/multi_year_results.py)

Work:
- extend design tables with structured inverter outputs
- add inverter-aware investment summary
- add inverter annuity/FOM rows
- add yearly inverter metrics
- use conversion technology labels instead of raw resource labels where appropriate

Validate before moving on:
- export CSVs contain explicit inverter information
- yearly KPIs and reporting tables reflect inverter costs/metrics consistently

### Step 7: Update Multi-Year Results Page

Purpose:
- expose the new inverter-aware outputs without page-local reconstruction hacks

Likely files:
- [core/visualization/multi_year_results_page.py](../core/visualization/multi_year_results_page.py)
- possibly [pages/4_Results.py](../pages/4_Results.py) if routing/session wiring is needed

Work:
- add inverter capacity summaries
- add inverter-aware cashflow breakdown
- add yearly inverter metrics / clipping information
- avoid recomputing inverter logic inside the page

Validate before moving on:
- page renders from exported backend outputs
- no hidden dependence on live model internals is introduced beyond current Multi-Year architecture

### Step 8: Add focused tests

Purpose:
- lock in the new consistency rules

Likely files:
- add/extend tests under `tests/`

Recommended test coverage:
- renewable dispatch respects active inverter AC capacity by year
- renewable inverter CAPEX/FOM/annuity use inverter-specific inputs
- battery inverter explicit power variable constrains charge/discharge
- battery inverter annuity/FOM use inverter lifetime
- degradation-enabled battery runs remain feasible with explicit inverter power
- export/reporting contains structured inverter tables and consistent totals

Validate before moving on:
- small deterministic synthetic cases pass
- any existing dynamic tests still pass or are updated intentionally

## 5. Risks and Likely Pitfalls

- Cohort/accounting mismatch:
  - if renewable inverter AC capacity is derived only in aggregate while CAPEX is computed by cohort, reporting and cashflow will diverge

- Battery degradation vs inverter power confusion:
  - if inverter power is linked to degraded effective capacity instead of nominal design energy, the model may unintentionally degrade inverter hardware every year

- Template/parser drift:
  - dynamic templates already expose some inverter fields the parser ignores
  - implementing only part of the chain would recreate the exact inconsistency we just fixed in Typical-Year

- UI duplication:
  - if inverter metrics are reconstructed in the page instead of exported by the backend, Multi-Year will become fragile again

- Overly invasive refactor:
  - Multi-Year is richer than Typical-Year, so a full canonical-results rewrite should not be bundled into the first inverter pass unless it becomes necessary

- Replacement-lifetime ambiguity:
  - battery energy and battery inverter may have different lifetimes
  - this must be handled explicitly in active-mask and annuity logic or results will be wrong

- Scenario/year weighting errors:
  - new inverter KPIs and cost rows must preserve the existing expected-value weighting rules

- Degradation-mode regressions:
  - advanced battery-loss and endogenous degradation already make the dynamic model delicate
  - battery inverter integration should be introduced with small isolated tests first

## Recommended First Coding Step

Start with **Step 1: audit and align dynamic inputs/templates**, specifically:
- extend [core/multi_year_model/data.py](../core/multi_year_model/data.py) to actually parse the inverter fields that the dynamic templates already expose
- persist `conversion_technology_by_resource` in Multi-Year dataset attrs/settings

This is the safest first step because it:
- closes the template/parser gap immediately
- gives the rest of the implementation a stable data contract
- can be validated without touching the objective or fragile degradation constraints yet
