from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Optional, List

import pandas as pd
import yaml

from core.io.jsonio import ensure_parent_dir
from core.io.paths import ProjectPaths


# =============================================================================
# Template settings (extended)
# =============================================================================
@dataclass(frozen=True)
class TemplateSettings:
    formulation: str                 # "steady_state" | "dynamic"
    system_type: str                 # "off_grid" | "on_grid"
    allow_export: bool

    multi_scenario: bool
    n_scenarios: int
    scenario_labels: Sequence[str]
    scenario_weights: Sequence[float]

    # dynamic-only context used to generate year headers
    start_year_label: str            # e.g. "2026" or "typical_year"
    horizon_years: Optional[int]     # e.g. 20 (None for steady_state)
    # capacity expansion context
    capacity_expansion: bool
    investment_steps_years: Optional[Sequence[int]]  # e.g. [5,5,5,5] or None


    # renewable resource context
    n_res_sources: int              # e.g. 2
    resource_labels: Sequence[str]   # e.g. ["solar", "wind"]
    conversion_labels: Sequence[str]  # e.g. ["pv", "wt"]
    # single-tech component labels
    battery_label: str
    generator_label: str
    fuel_label: str


def write_templates(paths: ProjectPaths, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Write user-editable templates into the project inputs folder.
    """

    # Time series templates
    _write_load_demand_csv(paths.inputs_dir / "load_demand.csv", settings, overwrite=overwrite)
    _write_resource_availability_csv(paths.inputs_dir / "resource_availability.csv", settings, overwrite=overwrite)
    # Write README file with metadata
    _write_inputs_readme(paths.inputs_dir / "README_inputs.md", settings, overwrite=overwrite)
    # Write renewables.yaml configuration
    _write_renewables_yaml(paths.inputs_dir / "renewables.yaml", settings, overwrite=overwrite)
    # Write battery.yaml configuration
    _write_battery_yaml(paths.inputs_dir / "battery.yaml", settings, overwrite=overwrite)
    # Write generator.yaml configuration
    _write_generator_yaml(paths.inputs_dir / "generator.yaml", settings, overwrite=overwrite)
    _write_generator_efficiency_curve_csv(paths.inputs_dir / "generator_efficiency_curve.csv", overwrite=overwrite)
    # Grid inputs (ONLY if on-grid)
    _write_grid_inputs(paths, settings, overwrite=overwrite)


# =============================================================================
# Helpers
# =============================================================================
def _safe_scenario_labels(settings: TemplateSettings) -> List[str]:
    """
    Ensure scenario_labels matches n_scenarios (stable ordering).
    """
    labels = list(settings.scenario_labels) if settings.scenario_labels is not None else []
    if len(labels) < settings.n_scenarios:
        labels += [f"scenario_{i+1}" for i in range(len(labels), settings.n_scenarios)]
    if len(labels) > settings.n_scenarios:
        labels = labels[: settings.n_scenarios]
    return [str(x).strip() or f"scenario_{i+1}" for i, x in enumerate(labels)]


def _safe_year_labels(settings: TemplateSettings) -> List[str]:
    """
    Return year labels for the second header level.
    - steady_state -> ["typical_year"]
    - dynamic -> ["<start_year>", "<start_year+1>", ...] for horizon_years
      If start_year_label is not parseable as int, fall back to "year_1..year_N".
    """
    if settings.formulation != "dynamic":
        return ["typical_year"]

    horizon = int(settings.horizon_years or 0)
    horizon = max(horizon, 1)

    try:
        y0 = int(str(settings.start_year_label).strip())
        return [str(y0 + i) for i in range(horizon)]
    except Exception:
        return [f"year_{i+1}" for i in range(horizon)]
    
def _safe_resource_labels(settings: TemplateSettings) -> List[str]:
    """
    Ensure resource_labels matches n_res_sources (stable ordering).
    """
    labels = list(settings.resource_labels) if settings.resource_labels is not None else []
    n = int(settings.n_res_sources or 0)
    n = max(n, 1)

    if len(labels) < n:
        labels += [f"RESOURCE_{i+1}" for i in range(len(labels), n)]
    if len(labels) > n:
        labels = labels[:n]

    return [str(x).strip() or f"RESOURCE_{i+1}" for i, x in enumerate(labels)]

def _safe_conversion_labels(settings: TemplateSettings) -> List[str]:
    labels = list(settings.conversion_labels) if settings.conversion_labels is not None else []
    n = int(settings.n_res_sources or 0)
    n = max(n, 1)

    if len(labels) < n:
        labels += [f"TECH_{i+1}" for i in range(len(labels), n)]
    if len(labels) > n:
        labels = labels[:n]

    return [str(x).strip() or f"TECH_{i+1}" for i, x in enumerate(labels)]


def _safe_step_keys(settings: TemplateSettings) -> List[str]:
    """
    Step keys used in YAML:
    - if dynamic AND capacity_expansion -> ["step_1", ..., "step_N"]
    - else -> ["base"]
    """
    is_dynamic = (settings.formulation == "dynamic")
    capexp = bool(getattr(settings, "capacity_expansion", False))

    if not (is_dynamic and capexp):
        return ["base"]

    years = list(settings.investment_steps_years or [])
    if len(years) == 0:
        # fallback: at least one step
        return ["step_1"]

    return [f"step_{i+1}" for i in range(len(years))]

def _safe_battery_label(settings: TemplateSettings) -> str:
    v = str(getattr(settings, "battery_label", "") or "").strip()
    return v or "Battery"


def _safe_generator_label(settings: TemplateSettings) -> str:
    v = str(getattr(settings, "generator_label", "") or "").strip()
    return v or "Generator"


def _safe_fuel_label(settings: TemplateSettings) -> str:
    v = str(getattr(settings, "fuel_label", "") or "").strip()
    return v or "Fuel"


def _template_scenarios(settings: TemplateSettings) -> List[str]:
    return _safe_scenario_labels(settings) if settings.multi_scenario else ["scenario_1"]


def _template_years(settings: TemplateSettings) -> List[str]:
    return _safe_year_labels(settings)


def _ensure_parent_dir(path: Path) -> None:
    ensure_parent_dir(path)


def _write_yaml_file(path: Path, payload: dict) -> None:
    _ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=True)


def _hourly_index(n_hours: int = 8760) -> pd.RangeIndex:
    return pd.RangeIndex(start=0, stop=n_hours, step=1)


def _write_hourly_csv_template(
    path: Path,
    *,
    columns: pd.MultiIndex,
    hour_column: tuple,
    value_columns: list[tuple],
    overwrite: bool,
    default_value: float = 0.0,
) -> None:
    if path.exists() and not overwrite:
        return

    hour_index = _hourly_index()
    df = pd.DataFrame(index=hour_index, columns=columns, dtype="float64")
    df[hour_column] = hour_index.to_numpy()
    for column in value_columns:
        df[column] = default_value

    _ensure_parent_dir(path)
    df.to_csv(path, index=False)


# =============================================================================
# Writers
# =============================================================================
def _write_load_demand_csv(path: Path, settings: TemplateSettings, overwrite: bool) -> None:
    """
    Create inputs/load_demand.csv with a 2-row header:
      - level 0: scenario label
      - level 1: year label

    Data:
      - 8760 hourly rows
      - values are hourly demand in kWh
      - includes meta/hour column as ("","hour") with values 0..8759
      - default cells are 0.0 (user to fill in)
    """
    scenarios = _template_scenarios(settings)
    years = _template_years(settings)

    # MultiIndex columns: ("scenario", "year")
    cols = [("meta", "hour")]
    for s in scenarios:
        for y in years:
            cols.append((str(s), str(y)))

    columns = pd.MultiIndex.from_tuples(cols, names=["scenario", "year"])
    value_columns = [(str(s), str(y)) for s in scenarios for y in years]
    _write_hourly_csv_template(
        path,
        columns=columns,
        hour_column=("meta", "hour"),
        value_columns=value_columns,
        overwrite=overwrite,
    )

def _write_resource_availability_csv(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/resource_availability.csv with a 3-row header:
      - level 0: scenario label
      - level 1: year label
      - level 2: resource label (one column per renewable resource)

    Data:
      - 8760 hourly rows
      - values are capacity factors (dimensionless, typically 0..1)
      - includes meta/hour column as ("","hour","") with values 0..8759
      - default cells are 0.0 (user to fill in)
    """
    scenarios = _template_scenarios(settings)
    years = _template_years(settings)
    resource_labels = _safe_resource_labels(settings)

    cols = [("meta", "hour", "")]
    for s in scenarios:
        for y in years:
            for r in resource_labels:
                cols.append((str(s), str(y), str(r)))

    columns = pd.MultiIndex.from_tuples(cols, names=["scenario", "year", "resource"])
    value_columns = [(str(s), str(y), str(r)) for s in scenarios for y in years for r in resource_labels]
    _write_hourly_csv_template(
        path,
        columns=columns,
        hour_column=("meta", "hour", ""),
        value_columns=value_columns,
        overwrite=overwrite,
    )


def _write_inputs_readme(path: Path, settings: TemplateSettings, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        return

    scenarios = _template_scenarios(settings)
    years = _template_years(settings)

    text = (
        "# Inputs folder\n\n"
        "This folder contains user-editable input templates.\n\n"
        "## load_demand.csv\n"
        "- Hourly **load demand** template (8760 rows).\n"
        "- Units: **kWh per hour** (energy during each hour).\n"
        "- **Two-row header**:\n"
        "  - Row 1: scenario labels\n"
        "  - Row 2: year labels\n"
        "- A meta column `meta/hour` provides the hour index (0..8759).\n\n"
        f"Scenarios: {', '.join(scenarios)}\n\n"
        f"Years: {', '.join(years)}\n\n"
        "## resource_availability.csv\n"
        "- Hourly **resource availability** template (8760 rows).\n"
        "- Units: **capacity factor** (per unit of nominal capacity, typically 0..1).\n"
        "- **Three-row header**:\n"
        "  - Row 1: scenario labels\n"
        "  - Row 2: year labels\n"
        "  - Row 3: resource labels\n"
        "- A meta column `meta/hour` provides the hour index (0..8759).\n\n"
        f"Scenarios: {', '.join(scenarios)}\n\n"
        f"Years: {', '.join(years)}\n\n"
        f"Resources: {', '.join(_safe_resource_labels(settings))}\n"
        "\n## renewables.yaml\n"
        "- Renewable techno-economic parameters.\n"
        "- Parameters can vary by resources, scenario and (if enabled) by investment step.\n\n"
        f"Renewables Technologies: {', '.join(_safe_conversion_labels(settings))}\n\n"
        "\n## battery.yaml\n"
        "- Battery techno-economic parameters.\n"
        "- Parameters can vary by scenario and (if enabled) by investment step.\n" 
    )

    # Grid section (only for on-grid)
    if settings.system_type == "on_grid":
        text += (
            "## grid.yaml\n"
            "- Grid connection parameters (scenario-dependent):\n"
            "  - line capacity (kW)\n"
            "  - transmission efficiency (-)\n"
            "  - (multi-year only) first year of grid connection\n"
            "  - outage statistics for backend-generated availability matrix\n\n"
            "## grid_import_price.csv\n"
            "- Hourly grid import cost (8760 rows).\n"
            "- Units: currency per kWh.\n"
            "- Two-row header: scenario labels / year labels.\n"
            "- Meta column `meta/hour` provides hour index (0..8759).\n\n"
        )

        if bool(getattr(settings, "allow_export", False)):
            text += (
                "## grid_export_price.csv\n"
                "- Hourly grid export price (8760 rows).\n"
                "- Units: currency per kWh.\n"
                "- Two-row header: scenario labels / year labels.\n"
                "- Meta column `meta/hour` provides hour index (0..8759).\n\n"
            )

        text += (
            "Note: the grid availability matrix is generated by the backend from outage inputs (no user template).\n\n"
        )

    _ensure_parent_dir(path)
    path.write_text(text, encoding="utf-8")

def _write_renewables_yaml(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/renewables.yaml

    Cohort logic (recommended default):
      - ONLY investment-side params may vary by investment step (inv_step).
      - Technical params are invariant across steps (no cohort-specific physics).
      - Operational params may vary by scenario, but are NOT step-dependent.

    YAML structure:

      renewables:
        - id, conversion_technology, resource
          investment:
            by_step:
              "<inv_step_label>":   # e.g. "1", "2" ... or "base" if single step
                {investment-side parameters}
          technical:
            {step-invariant technical parameters}
          operation:
            by_scenario:
              "<scenario>":
                {scenario-dependent operational parameters}

    Notes:
      - If multi_scenario is False, only scenario_1 is used.
      - If capacity_expansion is disabled (or not dynamic), only one step key is used (typically "base" or "1",
        depending on your _safe_step_keys implementation).
      - In steady_state, degradation keys are omitted (not applicable).
    """
    if path.exists() and not overwrite:
        return

    scenarios = _safe_scenario_labels(settings) if settings.multi_scenario else ["scenario_1"]

    resource_labels = _safe_resource_labels(settings)
    conversion_labels = _safe_conversion_labels(settings)

    # IMPORTANT: step keys MUST match sets.inv_step labels.
    # For dynamic capexp with N steps, this should be ["1","2",...,"N"].
    # For no capexp, this can be ["base"] OR ["1"] depending on your convention.
    step_keys = list(map(str, _safe_step_keys(settings)))

    is_dynamic = (settings.formulation == "dynamic")
    capexp = bool(getattr(settings, "capacity_expansion", False))

    # Optional step metadata (purely informational; not required by loaders)
    steps_years = list(getattr(settings, "investment_steps_years", None) or [])
    steps_meta = None
    if is_dynamic and capexp and steps_years:
        # Map metadata to inv_step labels "1","2",...
        steps_meta = [{"step": str(i + 1), "duration_years": int(steps_years[i])} for i in range(len(steps_years))]

    # -------------------------------------------------------------------------
    # Default parameter blocks
    # -------------------------------------------------------------------------
    def _default_investment_params() -> dict:
        return {
            # sizing (design-side)
            "nominal_capacity_kw": 1.0,                         # kW per unit (or per continuous "unit")

            # economics (investment-side)
            "specific_investment_cost_per_kw": 0.0,             # currency/kW
            "wacc": 0.0,                                        # -
            "grant_share_of_capex": 0.0,                        # share (0..1)

            # lifetime / replacement modelling (still investment-side)
            "lifetime_years": 25,                               # years

            # sustainability (investment-side; embodied per installed capacity)
            "embedded_emissions_kgco2e_per_kw": 0.0,            # kgCO2e/kW
        }

    def _default_technical_params() -> dict:
        # Keep ONLY step-invariant physical/technical parameters here.
        # If later you add cohort dispatch, you can move some keys to investment.by_step or a new technical.by_step.
        return {
            "inverter_efficiency": 1.0,                         # -
            "specific_area_m2_per_kw": None,                    # optional (m2/kW) -> allow null 
            "max_installable_capacity_kw": None,                # optional (kW) -> allow null
        }

    def _default_operation_params() -> dict:
        p = {
            "fixed_om_share_per_year": 0.0,                     # share of CAPEX per year
            "production_subsidy_per_kwh": 0.0,                  # currency/kWh
        }
        # Degradation affects operation, but we keep it scenario-dependent and step-invariant
        if is_dynamic:
            p["capacity_degradation_rate_per_year"] = 0.0       # -/year (effective capacity)
        return p

    renewables_list = []
    n_res = int(getattr(settings, "n_res_sources", 1) or 1)

    for i in range(n_res):
        conv = str(conversion_labels[i])
        res = str(resource_labels[i])

        investment_by_step = {sk: _default_investment_params() for sk in step_keys}
        operation_by_scenario = {str(s): _default_operation_params() for s in scenarios}

        renewables_list.append(
            {
                "id": f"res_{i+1}",
                "conversion_technology": conv,
                "resource": res,
                "investment": {"by_step": investment_by_step},
                "technical": _default_technical_params(),
                "operation": {"by_scenario": operation_by_scenario},
            }
        )

    # -----------------------------
    # META: units + descriptions
    # -----------------------------
    units = {
        "res_nominal_capacity_kw": "kW",
        "res_specific_investment_cost_per_kw": "currency_per_kW",
        "res_wacc": "-",
        "res_grant_share_of_capex": "share",
        "res_lifetime_years": "years",
        "res_embedded_emissions_kgco2e_per_kw": "kgCO2e_per_kW",
        "res_inverter_efficiency": "-",
        "res_specific_area_m2_per_kw": "m2_per_kW",
        "res_max_installable_capacity_kw": "kW",
        "res_fixed_om_share_per_year": "share_per_year",
        "res_production_subsidy_per_kwh": "currency_per_kWh",
    }
    if is_dynamic:
        units["res_capacity_degradation_rate_per_year"] = "per_year"

    description = {
        "summary": (
            "Renewable inputs define cohort-dependent investment parameters, shared technical assumptions, "
            "and scenario-dependent operating parameters."
        ),
        "parameters": {
            "res_nominal_capacity_kw": "Nominal capacity represented by one renewable unit.",
            "res_specific_investment_cost_per_kw": "Specific investment cost of installed renewable capacity.",
            "res_wacc": "Weighted average cost of capital used for annualizing renewable CAPEX.",
            "res_grant_share_of_capex": "Fraction of renewable CAPEX covered by grants or subsidies.",
            "res_lifetime_years": "Technical/economic lifetime used for replacement and annuity calculations.",
            "res_embedded_emissions_kgco2e_per_kw": "Embodied emissions associated with installing renewable capacity.",
            "res_inverter_efficiency": "Conversion efficiency applied to renewable output.",
            "res_specific_area_m2_per_kw": "Land requirement per unit of renewable installed capacity.",
            "res_max_installable_capacity_kw": "Upper bound on renewable installed capacity for the resource.",
            "res_fixed_om_share_per_year": "Fixed annual O&M cost expressed as a share of renewable CAPEX.",
            "res_production_subsidy_per_kwh": "Operating subsidy earned per unit of renewable generation.",
        },
    }
    if is_dynamic:
        description["parameters"]["res_capacity_degradation_rate_per_year"] = (
            "Annual reduction in effective renewable capacity used in the dynamic formulation."
        )

    payload = {
        "meta": {
            "units": units,
            "context": {
                "formulation": settings.formulation,
                "multi_scenario": bool(settings.multi_scenario),
                "scenarios": list(map(str, scenarios)),
                "capacity_expansion": capexp,
                "investment_steps": steps_meta,
                "inv_step_keys": step_keys,  # helpful for debugging template vs sets
            },
            "description": description,
        },
        "renewables": renewables_list,
    }

    _write_yaml_file(path, payload)


def _write_battery_yaml(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/battery.yaml (NEW SCHEMA: cohorts only for investment-side params)

    Structure:
      battery:
        label: <battery_label>

        investment:
          by_step:
            "<inv_step>":
              {investment-side params that may differ by cohort}

        technical:
          {step-invariant technical params}

        operation:
          by_scenario:
            "<scenario>":
              {scenario-dependent operation params (NOT step-dependent)}

    Notes:
    - If multi_scenario is False, only scenario_1 is used.
    - If capacity_expansion is disabled (or not dynamic), inv_step typically has one label (e.g. "1" or "base"
      depending on your sets convention). We still write by_step for whatever _safe_step_keys returns.
    - In steady_state (typical-year), degradation parameters are omitted (not applicable).
    """
    if path.exists() and not overwrite:
        return

    scenarios = _template_scenarios(settings)
    step_keys = _safe_step_keys(settings)  # IMPORTANT: should match sets.inv_step labels, e.g. ["1","2",...]

    is_dynamic = (settings.formulation == "dynamic")
    capexp = bool(getattr(settings, "capacity_expansion", False))

    # Optional step metadata (human readability only)
    steps_years = list(getattr(settings, "investment_steps_years", None) or [])
    steps_meta = None
    if is_dynamic and capexp:
        steps_meta = [
            {"step": f"step_{i+1}", "duration_years": int(steps_years[i])}
            for i in range(len(steps_years))
        ]

    # -------------------------------------------------------------------------
    # Default parameter blocks (NEW)
    # -------------------------------------------------------------------------
    # Step-dependent cohort params (investment-side)
    def _default_investment_params() -> dict:
        return {
            # sizing (per unit)
            "nominal_capacity_kwh": 1.0,                      # kWh per unit (or continuous unit)

            # economics (investment-related)
            "specific_investment_cost_per_kwh": 0.0,          # currency/kWh
            "wacc": 0.0,                                      # -

            # lifetime / limits (can differ by cohort/product)
            "calendar_lifetime_years": 10,                    # years

            # sustainability (manufacturing / embodied, cohort-side)
            "embedded_emissions_kgco2e_per_kwh": 0.0,         # kgCO2e/kWh of capacity
        }

    # Step-invariant technical parameters (shared across cohorts)
    def _default_technical_params() -> dict:
        return {
            "charge_efficiency": 1.0,                         # -
            "discharge_efficiency": 1.0,                      # -
            "initial_soc": 0.5,                               # fraction of usable capacity (0..1)
            "depth_of_discharge": 0.8,                        # fraction (0..1), usable fraction of nominal capacity
            "max_discharge_time_hours": 5.0,                  # hours (C-rate proxy)
            "max_charge_time_hours": 5.0,                     # hours (C-rate proxy)
            "max_installable_capacity_kwh": None,             # optional (kWh)
        }

    # Scenario-dependent operation parameters (NOT step-dependent)
    def _default_operation_params() -> dict:
        p = {
            "fixed_om_share_per_year": 0.0,                   # share of CAPEX per year
        }
        # Degradation only meaningful in dynamic formulation
        if is_dynamic:
            p["capacity_degradation_rate_per_year"] = 0.0     # /year (effective capacity fade)
        return p

    # -------------------------------------------------------------------------
    # Build YAML sections
    # -------------------------------------------------------------------------
    investment_by_step = {sk: _default_investment_params() for sk in step_keys}

    operation_by_scenario = {str(s): _default_operation_params() for s in scenarios}

    payload = {
        "meta": {
            "units": {
                "battery_nominal_capacity_kwh": "kWh",
                "battery_specific_investment_cost_per_kwh": "currency_per_kWh",
                "battery_wacc": "-",
                "battery_calendar_lifetime_years": "years",
                "battery_embedded_emissions_kgco2e_per_kwh": "kgCO2e_per_kWh",
                "battery_charge_efficiency": "-",
                "battery_discharge_efficiency": "-",
                "battery_initial_soc": "share",
                "battery_depth_of_discharge": "share",
                "battery_max_discharge_time_hours": "hours",
                "battery_max_charge_time_hours": "hours",
                "battery_max_installable_capacity_kwh": "kWh",
                "battery_fixed_om_share_per_year": "share_per_year",
                **(
                    {
                        "battery_capacity_degradation_rate_per_year": "per_year",
                    }
                    if is_dynamic
                    else {}
                ),
            },
            "context": {
                "formulation": settings.formulation,
                "multi_scenario": bool(settings.multi_scenario),
                "scenarios": list(map(str, scenarios)),
                "capacity_expansion": capexp,
                "investment_steps": steps_meta,
            },
            "description": {
                "summary": (
                    "Battery inputs define cohort-dependent investment data, shared technical behavior, "
                    "and scenario-dependent operating assumptions."
                ),
                "parameters": {
                    "battery_nominal_capacity_kwh": "Nominal energy capacity represented by one battery unit.",
                    "battery_specific_investment_cost_per_kwh": "Specific investment cost of battery capacity.",
                    "battery_wacc": "Weighted average cost of capital used for battery annuities.",
                    "battery_calendar_lifetime_years": "Calendar lifetime used for battery replacement economics.",
                    "battery_embedded_emissions_kgco2e_per_kwh": "Embodied emissions associated with battery capacity.",
                    "battery_charge_efficiency": "Battery charging efficiency.",
                    "battery_discharge_efficiency": "Battery discharging efficiency.",
                    "battery_initial_soc": "Initial state of charge as a share of usable capacity.",
                    "battery_depth_of_discharge": "Usable fraction of nominal battery capacity.",
                    "battery_max_discharge_time_hours": "Minimum time needed to fully discharge at nominal power.",
                    "battery_max_charge_time_hours": "Minimum time needed to fully charge at nominal power.",
                    "battery_max_installable_capacity_kwh": "Upper bound on total installed battery capacity.",
                    "battery_fixed_om_share_per_year": "Fixed annual O&M cost expressed as a share of battery CAPEX.",
                    **(
                        {
                            "battery_capacity_degradation_rate_per_year": (
                                "Annual reduction in effective battery capacity in the dynamic formulation."
                            )
                        }
                        if is_dynamic
                        else {}
                    ),
                },
            },
        },
        "battery": {
            "label": _safe_battery_label(settings),
            "investment": {"by_step": investment_by_step},
            "technical": _default_technical_params(),
            "operation": {"by_scenario": operation_by_scenario},
        },
    }

    _write_yaml_file(path, payload)


def _write_generator_yaml(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/generator.yaml

    NEW generator logic (fuel unchanged):
    - generator.investment.by_step: step-dependent investment-side params only
    - generator.technical: step-INVARIANT technical params
    - generator.operation.by_scenario: scenario-dependent operation params (NOT step-dependent)

    Fuel block remains:
      fuel:
        label: ...
        by_scenario:
          <scenario>:
            {LHV, emissions factor, fuel cost specification}

    Notes:
    - If efficiency_curve_csv is null/empty, constant nominal efficiency is assumed.
    - If efficiency_curve_csv is provided, it should point to a CSV file with:
        'Relative Power Output [-]', 'Efficiency [-]'.
    """
    if path.exists() and not overwrite:
        return

    is_dynamic = (settings.formulation == "dynamic")
    capexp = bool(getattr(settings, "capacity_expansion", False))

    scenarios = _template_scenarios(settings)
    step_keys = _safe_step_keys(settings)
    years = _template_years(settings)  # used for fuel cost only when dynamic

    # Optional step metadata (for human readability; not required by loader)
    steps_years = list(getattr(settings, "investment_steps_years", None) or [])
    steps_meta = None
    if is_dynamic and capexp:
        steps_meta = [
            {"step": f"step_{i+1}", "duration_years": int(steps_years[i])}
            for i in range(len(steps_years))
        ]

    # -------------------------------------------------------------------------
    # Default parameter blocks (GENERATOR)
    # -------------------------------------------------------------------------
    # Step-dependent investment-side params (cohort differences allowed)
    def _default_generator_investment_params() -> dict:
        return {
            # sizing (per unit)
            "nominal_capacity_kw": 1.0,                        # kW per unit

            # lifetime / finance (investment-side)
            "lifetime_years": 10,                              # years
            "specific_investment_cost_per_kw": 0.0,            # currency/kW
            "wacc": 0.0,                                       # -
            "embedded_emissions_kgco2e_per_kw": 0.0,           # kgCO2e/kW (investment-side attribute)
        }

    # Step-INVARIANT technical params
    def _default_generator_technical_params() -> dict:
        return {
            # core performance assumption at 100% output
            "nominal_efficiency_full_load": 0.30,              # - at 100% power
            "max_installable_capacity_kw": None,               # optional (kW)
        }

    # Scenario-dependent operation params (NOT step-dependent)
    def _default_generator_operation_params() -> dict:
        p = {
            # economics (operation-related)
            "fixed_om_share_per_year": 0.0,                    # share of CAPEX per year

            # optional partial-load efficiency curve CSV (scenario-level switch)
            # If None/empty -> constant efficiency = nominal_efficiency_full_load
            "efficiency_curve_csv": None,                      # e.g. "generator_efficiency_curve.csv"
        }

        # Degradation only meaningful in dynamic formulation (scenario-dependent)
        if is_dynamic:
            p["capacity_degradation_rate_per_year"] = 0.0  # -/year (effective power capacity)

        return p

    # -------------------------------------------------------------------------
    # Fuel block (UNCHANGED)
    # -------------------------------------------------------------------------
    def _default_fuel_block() -> dict:
        """
        Fuel block per scenario.

        steady_state:
          - fuel_cost_per_unit_fuel: scalar

        dynamic:
          - by_year_cost_per_unit_fuel: list aligned with meta.context.year_labels_for_fuel_cost
            (If you want constant cost, repeat the same value for all years.)
        """
        base = {
            "lhv_kwh_per_unit_fuel": 0.0,                        # kWh per unit fuel (e.g., kWh/L or kWh/kg)
            "direct_emissions_kgco2e_per_unit_fuel": 0.0,        # kgCO2e per unit fuel
        }

        if not is_dynamic:
            base["fuel_cost_per_unit_fuel"] = 0.0               # currency per unit fuel (constant typical-year)
            base["description"] = (
                "Typical-year fuel inputs use a single constant fuel cost per unit fuel."
            )
            return base

        # dynamic
        base["by_year_cost_per_unit_fuel"] = [0.0 for _ in years]  # list aligned with year_labels_for_fuel_cost
        base["description"] = (
            "Multi-year fuel inputs use one fuel cost value per model year label; repeat values for flat trajectories."
        )
        return base

    # -------------------------------------------------------------------------
    # Build GENERATOR blocks (NEW SCHEMA)
    # -------------------------------------------------------------------------
    # investment.by_step
    gen_investment_by_step = {sk: _default_generator_investment_params() for sk in step_keys}

    # technical (step-invariant)
    gen_technical = _default_generator_technical_params()

    # operation.by_scenario (no by_step anymore)
    gen_operation_by_scenario = {str(s): _default_generator_operation_params() for s in scenarios}

    # -------------------------------------------------------------------------
    # Build fuel by_scenario (UNCHANGED)
    # -------------------------------------------------------------------------
    fuel_by_scenario = {str(s): _default_fuel_block() for s in scenarios}

    # -------------------------------------------------------------------------
    # META: units + descriptions (update wording to match new schema)
    # -------------------------------------------------------------------------
    units = {
        "generator_nominal_capacity_kw": "kW",
        "generator_lifetime_years": "years",
        "generator_specific_investment_cost_per_kw": "currency_per_kW",
        "generator_wacc": "-",
        "generator_embedded_emissions_kgco2e_per_kw": "kgCO2e_per_kW",
        "generator_nominal_efficiency_full_load": "-",
        "generator_max_installable_capacity_kw": "kW",
        "generator_fixed_om_share_per_year": "share_per_year",
        "fuel_lhv_kwh_per_unit_fuel": "kWh_per_unit_fuel",
        "fuel_direct_emissions_kgco2e_per_unit_fuel": "kgCO2e_per_unit_fuel",
    }
    if is_dynamic:
        units.update(
            {
                "generator_capacity_degradation_rate_per_year": "per_year",
                "fuel_cost_by_year": "currency_per_unit_fuel_by_year",
            }
        )
    else:
        units.update({"fuel_fuel_cost_per_unit_fuel": "currency_per_unit_fuel"})

    description = {
        "summary": (
            "Generator inputs define cohort-dependent investment data, shared technical behavior, "
            "scenario-dependent operating assumptions, and scenario fuel properties."
        ),
        "parameters": {
            "generator_nominal_capacity_kw": "Nominal power represented by one generator unit.",
            "generator_lifetime_years": "Generator lifetime used for replacement and annuity calculations.",
            "generator_specific_investment_cost_per_kw": "Specific generator investment cost.",
            "generator_wacc": "Weighted average cost of capital used for generator annuities.",
            "generator_embedded_emissions_kgco2e_per_kw": "Embodied emissions associated with generator capacity.",
            "generator_nominal_efficiency_full_load": "Generator efficiency at full load when no partial-load curve is used.",
            "generator_max_installable_capacity_kw": "Upper bound on installed generator capacity.",
            "generator_fixed_om_share_per_year": "Fixed annual O&M cost expressed as a share of generator CAPEX.",
            "fuel_lhv_kwh_per_unit_fuel": "Lower heating value of the fuel.",
            "fuel_direct_emissions_kgco2e_per_unit_fuel": "Direct combustion emissions per unit of fuel.",
            "fuel_fuel_cost_per_unit_fuel": "Fuel price in the steady-state formulation.",
        },
    }
    if is_dynamic:
        description["parameters"]["generator_capacity_degradation_rate_per_year"] = (
            "Annual reduction in effective generator capacity in the dynamic formulation."
        )
        description["parameters"]["fuel_cost_by_year"] = (
            "Fuel price trajectory aligned with the dynamic model year labels."
        )

    payload = {
        "meta": {
            "units": units,
            "context": {
                "formulation": settings.formulation,
                "multi_scenario": bool(settings.multi_scenario),
                "scenarios": list(map(str, scenarios)),
                "capacity_expansion": capexp,
                "investment_steps": steps_meta,
                "year_labels_for_fuel_cost": list(map(str, years)),
                "efficiency_curve_path_base": "inputs/",
            },
            "description": description,
        },
        "generator": {
            "label": _safe_generator_label(settings),
            # NEW keys
            "investment": {"by_step": gen_investment_by_step},
            "technical": gen_technical,
            "operation": {"by_scenario": gen_operation_by_scenario},
        },
        "fuel": {
            "label": _safe_fuel_label(settings),
            "by_scenario": fuel_by_scenario,
        },
    }

    _write_yaml_file(path, payload)


def _write_generator_efficiency_curve_csv(path: Path, overwrite: bool = False) -> None:
    """
    Create inputs/generator_efficiency_curve.csv (optional helper template).

    Columns:
      - Relative Power Output [-]
      - Efficiency [-]

    This is NOT mandatory; if not provided, the model should assume constant efficiency.
    """
    if path.exists() and not overwrite:
        return

    df = pd.DataFrame(
        {
            "Relative Power Output [-]": [0, 0.25, 0.50, 0.75, 1.0],
            "Efficiency [-]": [0.0, 0.20, 0.26, 0.29, 0.30],
        }
    )

    _ensure_parent_dir(path)
    df.to_csv(path, index=False)

def _write_grid_inputs(paths: ProjectPaths, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Write grid-related templates ONLY if on-grid system is enabled.
    Files:
      - inputs/grid.yaml
      - inputs/grid_import_price.csv
      - inputs/grid_export_price.csv (only if allow_export=True)
    """
    if settings.system_type != "on_grid":
        return

    _write_grid_yaml(paths.inputs_dir / "grid.yaml", settings, overwrite=overwrite)
    _write_grid_import_price_csv(paths.inputs_dir / "grid_import_price.csv", settings, overwrite=overwrite)

    if bool(getattr(settings, "allow_export", False)):
        _write_grid_export_price_csv(paths.inputs_dir / "grid_export_price.csv", settings, overwrite=overwrite)


def _write_grid_yaml(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/grid.yaml (used by backend only if system_type == 'on_grid').

    Includes:
      - Grid line capacity (kW) (import/export limit)
      - Grid line transmission efficiency (-), scenario dependent
      - Future grid connection (dynamic only): first_year_connection (scenario dependent)
      - Outage simulation inputs (scenario dependent):
          - average_outages_per_year
          - average_outage_duration_minutes
          - outage_scale_od_hours   (Weibull scale for outage duration; default 36/60)
          - outage_shape_od         (Weibull shape for outage duration; default 0.56)

    Separate CSV inputs (hourly):
      - grid_import_price.csv (required in on-grid mode)
      - grid_export_price.csv (only if allow_export=True)

    Notes:
      - Price CSV templates are generated as multi-header files consistent with load_demand:
          - header level 0: scenario
          - header level 1: year label(s)
        and contain 8760 hourly rows plus a meta/hour column.
      - Grid availability matrix is generated by the backend from outage parameters.
    """
    if path.exists() and not overwrite:
        return

    scenarios = _template_scenarios(settings)
    years = _template_years(settings)  # used for context + dynamic first_year_connection default
    is_dynamic = (settings.formulation == "dynamic")
    allow_export = bool(getattr(settings, "allow_export", False))

    def _default_grid_params() -> dict:
        base = {
            "line": {
                "capacity_kw": 0.0,                 # kW (grid import/export limit)
                "transmission_efficiency": 1.0,     # - (0..1), scenario dependent
                "renewable_share": 0.0,             # share (0..1) of imported electricity counted as renewable
                "emissions_factor_kgco2e_per_kwh": 0.0,  # kgCO2e per delivered kWh imported from grid
            },
            "outages": {
                "average_outages_per_year": 0.0,         # events/year
                "average_outage_duration_minutes": 0.0,  # minutes/event

                # Weibull parameters for outage duration (OD), in HOURS
                # Default matches your previous constants: scale_od = 36/60, shape_od = 0.56
                "outage_scale_od_hours": 36 / 60,        # hours
                "outage_shape_od": 0.56,                 # -
                "outage_seed": 0,                        # deterministic seed for generated availability
            },
        }

        # Only include future-connection parameter in dynamic formulation
        if is_dynamic:
            # best-effort default: first year label if parseable, otherwise None
            fy = None
            if years:
                try:
                    fy = int(str(years[0]).strip())
                except Exception:
                    fy = None
            base["first_year_connection"] = fy

        return base

    by_scenario = {str(s): _default_grid_params() for s in scenarios}

    payload = {
        "meta": {
            "context": {
                "formulation": settings.formulation,
                "system_type": settings.system_type,
                "multi_scenario": bool(settings.multi_scenario),
                "scenarios": list(map(str, scenarios)),
                "year_headers_used_in_timeseries": list(map(str, years)),
                "allow_export": allow_export,
                "csv_files": {
                    "grid_import_price": "grid_import_price.csv",
                    "grid_export_price": "grid_export_price.csv" if allow_export else None,
                    "csv_base_folder": "inputs/",
                },
            },
            "units": {
                "grid_line_capacity_kw": "kW",
                "grid_transmission_efficiency": "-",
                "grid_renewable_share": "share",
                "grid_emissions_factor_kgco2e_per_kwh": "kgCO2e_per_kWh",
                "grid_avg_outages_per_year": "events_per_year",
                "grid_avg_outage_duration_minutes": "minutes",
                "grid_outage_scale_od_hours": "hours",
                "grid_outage_shape_od": "-",
                "grid_outage_seed": "integer_seed",
                "grid_first_year_connection": "year_label" if is_dynamic else None,
            },
            "description": {
                "summary": (
                    "Grid inputs define line limits, outage statistics, and connection timing for on-grid configurations."
                ),
                "parameters": {
                    "grid_line_capacity_kw": "Maximum import/export capacity of the grid interconnection.",
                    "grid_transmission_efficiency": "Efficiency applied to power exchanged with the grid.",
                    "grid_renewable_share": "Share of delivered imported electricity counted as renewable in policy metrics.",
                    "grid_emissions_factor_kgco2e_per_kwh": "Scope 2 emissions factor applied to delivered imported electricity.",
                    "grid_avg_outages_per_year": "Average number of grid outages per year.",
                    "grid_avg_outage_duration_minutes": "Average outage duration used by the outage simulator.",
                    "grid_outage_scale_od_hours": "Weibull scale parameter for outage duration sampling.",
                    "grid_outage_shape_od": "Weibull shape parameter for outage duration sampling.",
                    "grid_outage_seed": "Deterministic seed used when generating the derived grid availability matrix.",
                    **(
                        {
                            "grid_first_year_connection": (
                                "First model year in which the grid connection becomes available."
                            )
                        }
                        if is_dynamic
                        else {}
                    ),
                },
            },
        },
        "grid": {
            "by_scenario": by_scenario,
        },
    }

    _write_yaml_file(path, payload)



def _write_grid_import_price_csv(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/grid_import_price.csv with a 2-row header:
      - level 0: scenario label
      - level 1: year label

    Data:
      - 8760 hourly rows
      - values are grid import costs (currency per kWh)
      - includes meta/hour column as ("meta","hour") with values 0..8759

    Notes:
      - If steady_state: year label is 'typical_year'
      - If dynamic: year labels expand across horizon_years
      - Scenario × year layout mirrors load_demand.csv
    """
    scenarios = _template_scenarios(settings)
    years = _template_years(settings)

    cols = [("meta", "hour")]
    for s in scenarios:
        for y in years:
            cols.append((str(s), str(y)))

    columns = pd.MultiIndex.from_tuples(cols, names=["scenario", "year"])
    value_columns = [(str(s), str(y)) for s in scenarios for y in years]
    _write_hourly_csv_template(
        path,
        columns=columns,
        hour_column=("meta", "hour"),
        value_columns=value_columns,
        overwrite=overwrite,
    )


def _write_grid_export_price_csv(path: Path, settings: TemplateSettings, overwrite: bool = False) -> None:
    """
    Create inputs/grid_export_price.csv with a 2-row header:
      - level 0: scenario label
      - level 1: year label

    Data:
      - 8760 hourly rows
      - values are grid export prices (currency per kWh)
      - includes meta/hour column as ("meta","hour") with values 0..8759
    """
    scenarios = _template_scenarios(settings)
    years = _template_years(settings)

    cols = [("meta", "hour")]
    for s in scenarios:
        for y in years:
            cols.append((str(s), str(y)))

    columns = pd.MultiIndex.from_tuples(cols, names=["scenario", "year"])
    value_columns = [(str(s), str(y)) for s in scenarios for y in years]
    _write_hourly_csv_template(
        path,
        columns=columns,
        hour_column=("meta", "hour"),
        value_columns=value_columns,
        overwrite=overwrite,
    )
